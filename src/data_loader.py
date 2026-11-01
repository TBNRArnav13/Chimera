import pandas as pd
import yaml
import os
from typing import List, Optional, Any, Dict
from src.utils import logger

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def load_csv(filepath: str, selected_features: Optional[List[str]] = None, label_override: Optional[str] = None, skip_rows: int = 0) -> Optional[pd.DataFrame]:
    """
    Loads a CSV file and returns a cleaning DataFrame with selected features.
    
    Args:
        filepath (str): Path to the CSV file.
        selected_features (list): List of column names to keep. If None, uses config.
        label_override (str): If provided, overrides the 'label' column with this value.
        skip_rows (int): Number of rows to skip (while keeping the header).
        
    Returns:
        pd.DataFrame: Processed DataFrame.
    """
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return None

    try:
        # Check file size (e.g. limit to 2GB to prevent memory exhaustion)
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        max_size_mb = CONFIG.get('data_loading', {}).get('max_file_size_mb', 2048) # Default 2GB
        if file_size_mb > max_size_mb:
            logger.error(f"File too large: {filepath} ({file_size_mb:.2f} MB > {max_size_mb} MB)")
            return None

        # Check for max_rows limit
        max_rows = CONFIG.get('data_loading', {}).get('max_rows_per_file', None)
        
        if skip_rows > 0:
            df = pd.read_csv(filepath, nrows=max_rows, skiprows=range(1, skip_rows + 1))
        else:
            df = pd.read_csv(filepath, nrows=max_rows)
            
        logger.info(f"Loaded {filepath} with shape {df.shape}")

        
        # Standardize column names (strip whitespace, lowercase)
        df.columns = df.columns.str.strip().str.lower()
        
        if selected_features is None:
            selected_features = CONFIG.get('selected_features', [])
            # standardized config features
            selected_features = [f.strip().lower() for f in selected_features]

        # Ensure 'label' is always included if it exists, or handled
        if 'label' in df.columns:
            if 'label' not in selected_features:
                selected_features.append('label')
        
        # Filter columns
        # We need to intersection because Benign/DoS might have different extras
        existing_cols = [c for c in selected_features if c in df.columns]
        missing_cols = [c for c in selected_features if c not in df.columns]
        
        if missing_cols:
            logger.warning(f"Missing columns in {filepath}: {missing_cols}")
        
        df = df[existing_cols]
        
        # Handle Inf/NaN
        # Replace Inf with NaN, then drop NaN or fill
        df.replace([float('inf'), float('-inf')], float('nan'), inplace=True)
        df.dropna(inplace=True)
        
        if label_override:
            df['label'] = label_override

        return df

    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None

def combine_datasets(benign_path: str, dos_dir: str) -> Optional[pd.DataFrame]:
    """
    Loads and combines Benign and DoS datasets into a single training DataFrame.
    """
    dfs = []
    
    # Load Benign
    logger.info("Loading Benign Dataset...")
    benign_df = load_csv(benign_path)
    if benign_df is not None:
        dfs.append(benign_df)
    
    # Load DoS
    if os.path.exists(dos_dir):
        logger.info("Loading DoS Datasets...")
        for filename in os.listdir(dos_dir):
            if filename.endswith(".csv"):
                full_path = os.path.join(dos_dir, filename)
                dos_df = load_csv(full_path)
                if dos_df is not None:
                    dfs.append(dos_df)
    
    if not dfs:
        return None
        
    combined_df = pd.concat(dfs, axis=0, ignore_index=True)
    logger.info(f"Combined Dataset Shape: {combined_df.shape}")
    
    return combined_df
