import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pickle
import os
from src.utils import logger, get_device
from typing import List, Dict, Any, Optional, Union

# ============================================================================
# Feature Group Definitions
# Maps the paper's 4 feature categories to their feature names
# (matching Table I of the Chimera research paper)
# ============================================================================
FEATURE_GROUPS = {
    'volume': [
        'flow duration', 'total fwd packets', 'total backward packets',
        'total length of fwd packets', 'total length of bwd packets',
        'flow bytes/s', 'flow packets/s'
    ],
    'packet_size': [
        'fwd packet length max', 'fwd packet length min',
        'fwd packet length mean', 'fwd packet length std',
        'bwd packet length max', 'bwd packet length min',
        'bwd packet length mean', 'bwd packet length std'
    ],
    'iat': [
        'flow iat mean', 'flow iat std', 'flow iat max', 'flow iat min',
        'fwd iat total', 'fwd iat mean', 'fwd iat std', 'fwd iat max', 'fwd iat min',
        'bwd iat total', 'bwd iat mean', 'bwd iat std', 'bwd iat max', 'bwd iat min'
    ],
    'tcp_flags': [
        'fwd psh flags', 'bwd psh flags', 'fwd urg flags', 'bwd urg flags'
    ]
}


# ============================================================================
# Legacy AutoEncoder (kept for backward-compatible model loading)
# ============================================================================
class _LegacyAutoEncoder(nn.Module):
    """Old single autoencoder architecture, kept only for loading old .pkl files."""
    def __init__(self, input_dim, hidden_dim=0.75):
        super(_LegacyAutoEncoder, self).__init__()
        h_dim = int(input_dim * hidden_dim)
        if h_dim < 1: h_dim = 1
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, h_dim),
            nn.ReLU(),
            nn.Linear(h_dim, h_dim // 2 if h_dim // 2 > 0 else 1),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(h_dim // 2 if h_dim // 2 > 0 else 1, h_dim),
            nn.ReLU(),
            nn.Linear(h_dim, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


# ============================================================================
# Sub-AutoEncoder: One per feature group (Denoising + BatchNorm + Dropout)
# ============================================================================
class SubAutoEncoder(nn.Module):
    """A denoising autoencoder for a single feature group."""
    
    def __init__(self, input_dim, noise_factor=0.1, dropout=0.2):
        super(SubAutoEncoder, self).__init__()
        self.noise_factor = noise_factor
        self.input_dim = input_dim
        
        # Calculate layer sizes — wider than input for better representation
        h1 = max(input_dim * 2, 8)
        h2 = max(input_dim, 4)
        bottleneck = max(input_dim // 2, 2)
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, h1),
            nn.BatchNorm1d(h1),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(h1, h2),
            nn.BatchNorm1d(h2),
            nn.ReLU(),
            nn.Linear(h2, bottleneck),
            nn.ReLU()
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck, h2),
            nn.BatchNorm1d(h2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(h2, h1),
            nn.BatchNorm1d(h1),
            nn.ReLU(),
            nn.Linear(h1, input_dim)
        )
    
    def forward(self, x):
        # Apply denoising during training
        if self.training and self.noise_factor > 0:
            noise = torch.randn_like(x) * self.noise_factor
            x_input = x + noise
        else:
            x_input = x
        encoded = self.encoder(x_input)
        decoded = self.decoder(encoded)
        return decoded


# ============================================================================
# Output AutoEncoder: Combines RMSE scores from all sub-AEs
# ============================================================================
class OutputAutoEncoder(nn.Module):
    """Output autoencoder that learns to reconstruct the combined anomaly scores."""
    
    def __init__(self, input_dim):
        super(OutputAutoEncoder, self).__init__()
        h1 = max(input_dim * 2, 8)
        bottleneck = max(input_dim // 2, 2)
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, h1),
            nn.ReLU(),
            nn.Linear(h1, bottleneck),
            nn.ReLU()
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck, h1),
            nn.ReLU(),
            nn.Linear(h1, input_dim)
        )
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


# ============================================================================
# KitNET: Ensemble Orchestrator
# ============================================================================
class KitNET:
    """
    Kitsune-inspired ensemble of autoencoders for anomaly detection.
    
    Architecture:
      - One SubAutoEncoder per feature group (Volume, Packet Size, IAT, TCP Flags)
      - Each trained independently on benign data with denoising
      - An OutputAutoEncoder combines per-group RMSE scores + cross-group stats
      - Final anomaly score = RMSE of the output AE reconstruction
    
    API is backward-compatible with the old single-AE KitNET class.
    """
    
    def __init__(self, input_dim: int, config: Dict[str, Any], feature_names: Optional[List[str]] = None):
        self.config = config
        self.input_dim = input_dim
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.threshold: Optional[float] = None
        self.logger = logger
        
        # Ensemble components
        self.group_indices: Dict[str, List[int]] = {}
        self.sub_autoencoders: Dict[str, SubAutoEncoder] = {}
        self.output_ae: Optional[OutputAutoEncoder] = None
        self._group_names_ordered: List[str] = []
        self._is_legacy: bool = False
        
        # Feature normalization (StandardScaler)
        # Fitted during training, applied during prediction
        self._scaler_mean: Optional[np.ndarray] = None
        self._scaler_std: Optional[np.ndarray] = None
        
        if feature_names is not None:
            self._build_ensemble(feature_names)
    
    def _build_ensemble(self, feature_names: List[str]):
        """Build the ensemble of sub-autoencoders based on feature group definitions."""
        feature_names_lower = [f.strip().lower() for f in feature_names]
        
        noise_factor = self.config.get('noise_factor', 0.1)
        dropout = self.config.get('dropout', 0.2)
        
        self.logger.info(f"Building Kitsune Ensemble ({len(feature_names_lower)} input features):")
        
        # Map feature names to column indices for each group
        for group_name, group_features in FEATURE_GROUPS.items():
            indices = []
            for feat in group_features:
                feat_lower = feat.strip().lower()
                if feat_lower in feature_names_lower:
                    indices.append(feature_names_lower.index(feat_lower))
            
            if indices:
                self.group_indices[group_name] = indices
                sub_ae = SubAutoEncoder(
                    len(indices), noise_factor=noise_factor, dropout=dropout
                ).to(self.device)
                self.sub_autoencoders[group_name] = sub_ae
                self.logger.info(f"  Sub-AE '{group_name}': {len(indices)} features")
        
        # Check for features that didn't map to any predefined group
        mapped = set()
        for indices in self.group_indices.values():
            mapped.update(indices)
        unmapped = [i for i in range(len(feature_names_lower)) if i not in mapped]
        if unmapped:
            self.group_indices['misc'] = unmapped
            sub_ae = SubAutoEncoder(
                len(unmapped), noise_factor=noise_factor, dropout=dropout
            ).to(self.device)
            self.sub_autoencoders['misc'] = sub_ae
            self.logger.info(f"  Sub-AE 'misc': {len(unmapped)} unmapped features")
        
        # Output AE: takes per-group RMSEs + 3 cross-group statistics
        n_groups = len(self.sub_autoencoders)
        output_input_dim = n_groups + 3  # per-group RMSEs + max, mean, std
        self.output_ae = OutputAutoEncoder(output_input_dim).to(self.device)
        self._group_names_ordered = list(self.sub_autoencoders.keys())
        
        self.logger.info(f"  Output AE: {output_input_dim} inputs ({n_groups} group RMSEs + 3 stats)")
        self.logger.info(f"Ensemble built: {n_groups} sub-AEs + 1 output AE on {self.device}")

    def train(self, X_train, epochs=None, batch_size=None):
        """
        Trains the full ensemble on benign data (X_train).
        
        Phase 1: Train each sub-autoencoder on its feature group.
        Phase 2: Compute per-group RMSEs on training data.
        Phase 3: Train the output autoencoder on aggregated RMSE scores.
        Phase 4: Calibrate the anomaly detection threshold.
        """
        if epochs is None:
            epochs = self.config.get('epochs', 50)
        if batch_size is None:
            batch_size = self.config.get('batch_size', 32)
        
        self.logger.info(f"Starting Kitsune Ensemble training on {self.device}")
        self.logger.info(f"  Training data: {X_train.shape[0]} samples, {X_train.shape[1]} features")
        self.logger.info(f"  Epochs: {epochs}, Batch size: {batch_size}")
        
        # Fit StandardScaler on training data
        self._scaler_mean = np.mean(X_train, axis=0).astype(np.float32)
        self._scaler_std = np.std(X_train, axis=0).astype(np.float32)
        # Prevent division by zero for constant features (e.g., flags often all-zero)
        self._scaler_std[self._scaler_std < 1e-8] = 1.0
        
        X_normalized = (X_train - self._scaler_mean) / self._scaler_std
        self.logger.info(f"  Feature normalization fitted (mean range: [{self._scaler_mean.min():.2f}, {self._scaler_mean.max():.2f}])")
        
        X_tensor = torch.FloatTensor(X_normalized).to(self.device)
        
        # ==== Phase 1: Train each sub-autoencoder ====
        self.logger.info("=" * 50)
        self.logger.info("Phase 1: Training Sub-Autoencoders")
        self.logger.info("=" * 50)
        
        sub_ae_rmses = {}
        
        for group_name, sub_ae in self.sub_autoencoders.items():
            indices = self.group_indices[group_name]
            X_group = X_tensor[:, indices]
            
            self.logger.info(f"\nTraining sub-AE '{group_name}' ({len(indices)} features, "
                           f"{X_group.shape[0]} samples)...")
            
            optimizer = optim.Adam(
                sub_ae.parameters(), lr=self.config.get('learning_rate', 0.001)
            )
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, patience=5, factor=0.5, min_lr=1e-6
            )
            criterion = nn.MSELoss()
            
            dataset = torch.utils.data.TensorDataset(X_group)
            loader = torch.utils.data.DataLoader(
                dataset, batch_size=batch_size, shuffle=True, drop_last=True
            )
            
            sub_ae.train()
            for epoch in range(epochs):
                total_loss = 0
                num_batches = 0
                for batch in loader:
                    inputs = batch[0]
                    optimizer.zero_grad()
                    outputs = sub_ae(inputs)
                    loss = criterion(outputs, inputs)  # Reconstruct clean input
                    loss.backward()
                    optimizer.step()
                    total_loss += loss.item()
                    num_batches += 1
                
                avg_loss = total_loss / max(num_batches, 1)
                scheduler.step(avg_loss)
                
                if (epoch + 1) % 10 == 0:
                    current_lr = optimizer.param_groups[0]['lr']
                    self.logger.info(
                        f"  [{group_name}] Epoch [{epoch+1}/{epochs}], "
                        f"Loss: {avg_loss:.6f}, LR: {current_lr:.6f}"
                    )
            
            # Compute per-sample RMSE for this sub-AE (eval mode — no noise)
            sub_ae.eval()
            with torch.no_grad():
                recons = sub_ae(X_group)
                rmse = torch.sqrt(torch.mean((X_group - recons) ** 2, dim=1))
                sub_ae_rmses[group_name] = rmse
            
            self.logger.info(
                f"  [{group_name}] Final RMSE — mean: {rmse.mean():.6f}, "
                f"std: {rmse.std():.6f}, max: {rmse.max():.6f}"
            )
        
        # ==== Phase 2: Prepare output AE input ====
        self.logger.info("\n" + "=" * 50)
        self.logger.info("Phase 2: Training Output Autoencoder")
        self.logger.info("=" * 50)
        
        # Stack per-group RMSEs: shape (N, n_groups)
        rmse_stack = torch.stack(
            [sub_ae_rmses[g] for g in self._group_names_ordered], dim=1
        )
        
        # Cross-group statistics (helps the output AE detect multi-group anomalies)
        rmse_max = rmse_stack.max(dim=1, keepdim=True).values
        rmse_mean = rmse_stack.mean(dim=1, keepdim=True)
        rmse_std = rmse_stack.std(dim=1, keepdim=True)
        # Handle NaN from std on single-group (shouldn't happen with 4 groups)
        rmse_std = torch.nan_to_num(rmse_std, nan=0.0)
        
        # Concatenate: [rmse_group1, rmse_group2, ..., max, mean, std]
        output_input = torch.cat([rmse_stack, rmse_max, rmse_mean, rmse_std], dim=1)
        
        self.logger.info(f"Output AE input shape: {output_input.shape}")
        
        # Train output AE
        optimizer = optim.Adam(
            self.output_ae.parameters(), lr=self.config.get('learning_rate', 0.001)
        )
        criterion = nn.MSELoss()
        
        dataset = torch.utils.data.TensorDataset(output_input)
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=batch_size, shuffle=True, drop_last=True
        )
        
        self.output_ae.train()
        for epoch in range(epochs):
            total_loss = 0
            num_batches = 0
            for batch in loader:
                inputs = batch[0]
                optimizer.zero_grad()
                outputs = self.output_ae(inputs)
                loss = criterion(outputs, inputs)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                num_batches += 1
            
            avg_loss = total_loss / max(num_batches, 1)
            if (epoch + 1) % 10 == 0:
                self.logger.info(
                    f"  [Output AE] Epoch [{epoch+1}/{epochs}], Loss: {avg_loss:.6f}"
                )
        
        # ==== Phase 3: Calibrate threshold ====
        self.logger.info("\n" + "=" * 50)
        self.logger.info("Phase 3: Calibrating Threshold")
        self.logger.info("=" * 50)
        
        self.output_ae.eval()
        with torch.no_grad():
            recons = self.output_ae(output_input)
            final_rmse = torch.sqrt(torch.mean((output_input - recons) ** 2, dim=1))
            final_rmse_np = final_rmse.cpu().numpy()
        
        mean_loss = float(np.mean(final_rmse_np))
        std_loss = float(np.std(final_rmse_np))
        std_factor = self.config.get('threshold_std_factor', 3.0)
        self.threshold = mean_loss + (std_factor * std_loss)
        
        self.logger.info(f"Threshold set to: {self.threshold:.6f}")
        self.logger.info(f"  Mean RMSE: {mean_loss:.6f}")
        self.logger.info(f"  Std RMSE:  {std_loss:.6f}")
        self.logger.info(f"  Factor:    {std_factor}")
        self.logger.info(f"Training Complete!")

    def predict(self, X):
        """
        Returns anomaly scores (RMSE from output AE) for input X.
        
        Args:
            X: Input features as numpy array, shape (N, 33).
            
        Returns:
            numpy array of anomaly scores, shape (N,).
        """
        # Handle legacy single-AE models
        if self._is_legacy:
            return self._predict_legacy(X)
        
        # Apply the same normalization as during training
        if self._scaler_mean is not None and self._scaler_std is not None:
            X_normalized = (X - self._scaler_mean) / self._scaler_std
        else:
            X_normalized = X
        
        X_tensor = torch.FloatTensor(X_normalized).to(self.device)
        
        # Set all models to eval mode
        for sub_ae in self.sub_autoencoders.values():
            sub_ae.eval()
        self.output_ae.eval()
        
        with torch.no_grad():
            # Step 1: Compute per-group RMSEs
            group_rmses = []
            for group_name in self._group_names_ordered:
                sub_ae = self.sub_autoencoders[group_name]
                indices = self.group_indices[group_name]
                X_group = X_tensor[:, indices]
                recons = sub_ae(X_group)
                rmse = torch.sqrt(torch.mean((X_group - recons) ** 2, dim=1))
                group_rmses.append(rmse)
            
            # Step 2: Stack and compute cross-group statistics
            rmse_stack = torch.stack(group_rmses, dim=1)
            rmse_max = rmse_stack.max(dim=1, keepdim=True).values
            rmse_mean = rmse_stack.mean(dim=1, keepdim=True)
            rmse_std = rmse_stack.std(dim=1, keepdim=True)
            rmse_std = torch.nan_to_num(rmse_std, nan=0.0)
            
            output_input = torch.cat([rmse_stack, rmse_max, rmse_mean, rmse_std], dim=1)
            
            # Step 3: Output AE reconstruction error = final anomaly score
            recons = self.output_ae(output_input)
            final_scores = torch.sqrt(torch.mean((output_input - recons) ** 2, dim=1))
        
        return final_scores.cpu().numpy()

    def _predict_legacy(self, X):
        """Legacy predict path using old single autoencoder."""
        self._legacy_model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)
        with torch.no_grad():
            recons = self._legacy_model(X_tensor)
            scores = torch.sqrt(torch.mean((X_tensor - recons) ** 2, dim=1))
        return scores.cpu().numpy()

    def save(self, path):
        """Save the ensemble model to disk."""
        import hashlib
        
        if self._is_legacy:
            self.logger.warning("Cannot save legacy model in ensemble format. Please retrain first.")
            return
        
        checkpoint = {
            'version': 'ensemble_v1',
            'input_dim': self.input_dim,
            'config': self.config,
            'threshold': self.threshold,
            'group_indices': self.group_indices,
            'group_names_ordered': self._group_names_ordered,
            'sub_ae_states': {
                name: ae.state_dict() for name, ae in self.sub_autoencoders.items()
            },
            'sub_ae_dims': {
                name: len(self.group_indices[name]) for name in self.sub_autoencoders
            },
            'output_ae_state': self.output_ae.state_dict(),
            'output_ae_dim': len(self.sub_autoencoders) + 3,
            'scaler_mean': self._scaler_mean,
            'scaler_std': self._scaler_std,
        }
        
        with open(path, 'wb') as f:
            pickle.dump(checkpoint, f)
        
        # Generate checksum
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        checksum_path = path + ".sha256"
        with open(checksum_path, "w") as f:
            f.write(sha256_hash.hexdigest())
        
        self.logger.info(f"Kitsune ensemble model saved to {path} with checksum")

    @classmethod
    def load(cls, path):
        """Load a Kitsune model from disk (supports both ensemble and legacy formats)."""
        import hashlib
        
        if not os.path.exists(path):
            return None
        
        # Verify checksum
        checksum_path = path + ".sha256"
        if os.path.exists(checksum_path):
            with open(checksum_path, "r") as f:
                expected_hash = f.read().strip()
            
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            if sha256_hash.hexdigest() != expected_hash:
                logger.error(f"Model integrity check failed for {path}!")
                raise ValueError("Model file is corrupted or tampered with (Checksum Mismatch).")
            else:
                logger.info(f"Model integrity verified for {path}.")
        else:
            logger.warning(f"No checksum found for {path}. Skipping integrity check.")
        
        with open(path, 'rb') as f:
            checkpoint = pickle.load(f)
        
        # Detect model format
        if checkpoint.get('version') != 'ensemble_v1':
            return cls._load_legacy(checkpoint)
        
        # Load ensemble model
        instance = cls(checkpoint['input_dim'], checkpoint['config'])
        instance.threshold = checkpoint['threshold']
        instance.group_indices = checkpoint['group_indices']
        instance._group_names_ordered = checkpoint['group_names_ordered']
        instance._scaler_mean = checkpoint.get('scaler_mean')
        instance._scaler_std = checkpoint.get('scaler_std')
        
        noise_factor = checkpoint['config'].get('noise_factor', 0.1)
        dropout = checkpoint['config'].get('dropout', 0.2)
        
        # Rebuild sub-autoencoders
        for name, state_dict in checkpoint['sub_ae_states'].items():
            dim = checkpoint['sub_ae_dims'][name]
            sub_ae = SubAutoEncoder(dim, noise_factor=noise_factor, dropout=dropout)
            sub_ae.load_state_dict(state_dict)
            sub_ae.to(instance.device)
            sub_ae.eval()
            instance.sub_autoencoders[name] = sub_ae
        
        # Rebuild output autoencoder
        output_dim = checkpoint['output_ae_dim']
        instance.output_ae = OutputAutoEncoder(output_dim)
        instance.output_ae.load_state_dict(checkpoint['output_ae_state'])
        instance.output_ae.to(instance.device)
        instance.output_ae.eval()
        
        logger.info(
            f"Kitsune ensemble loaded from {path} "
            f"({len(instance.sub_autoencoders)} sub-AEs, threshold={instance.threshold:.6f})"
        )
        return instance

    @classmethod
    def _load_legacy(cls, checkpoint):
        """Backward compatibility: load old single-AE model format."""
        logger.warning("=" * 60)
        logger.warning("LEGACY MODEL FORMAT DETECTED")
        logger.warning("The old single-autoencoder model is loaded.")
        logger.warning("For improved performance, retrain with:")
        logger.warning("  python run.py train_kitsune")
        logger.warning("=" * 60)
        
        instance = cls(checkpoint['input_dim'], checkpoint['config'])
        instance.threshold = checkpoint['threshold']
        instance._is_legacy = True
        
        # Reconstruct the old AutoEncoder architecture
        legacy_ae = _LegacyAutoEncoder(
            checkpoint['input_dim'],
            checkpoint['config'].get('hidden_ratio', 0.75)
        )
        legacy_ae.load_state_dict(checkpoint['model_state'])
        legacy_ae.to(instance.device)
        legacy_ae.eval()
        instance._legacy_model = legacy_ae
        
        return instance
