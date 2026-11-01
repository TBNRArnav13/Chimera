import xgboost as xgb
import numpy as np
import os
from src.utils import logger, get_device
from typing import Dict, Any, Tuple, Optional, Union

class XGBoostDetector:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model: Optional[xgb.Booster] = None
        self.device_info = get_device()
        self.logger = logger
        
    def train(self, X, y, validation_data=None):
        """
        Trains the XGBoost classifier.
        """
        self.logger.info("Initializing XGBoost Training...")
        
        # Prepare parameters
        params = {
            'objective': self.config.get('objective', 'binary:logistic'),
            'max_depth': self.config.get('max_depth', 6),
            'learning_rate': self.config.get('learning_rate', 0.1),
            'eval_metric': ['logloss', 'error'],
        }
        
        # Check for GPU support
        if self.device_info.get('xgboost') == 'gpu_hist':
            params['device'] = 'cuda'
            params['tree_method'] = 'hist' # Modern XGBoost uses 'hist' with device='cuda'
            self.logger.info("XGBoost using GPU (device='cuda').")
        else:
            params['device'] = 'cpu'
            params['tree_method'] = 'hist'
            self.logger.info("XGBoost using CPU (Hist).")
            
        dtrain = xgb.DMatrix(X, label=y)
        evals = [(dtrain, 'train')]
        
        if validation_data:
            dval = xgb.DMatrix(validation_data[0], label=validation_data[1])
            evals.append((dval, 'validation'))
            
        self.logger.info("Starting XGBoost training cycle...")
        self.model = xgb.train(
            params, 
            dtrain, 
            num_boost_round=self.config.get('n_estimators', 100),
            evals=evals,
            early_stopping_rounds=10,
            verbose_eval=True
        )
        self.logger.info("XGBoost Training Complete.")

    def predict(self, X):
        """
        Returns predictions (class) and probabilities.
        """
        if not self.model:
            self.logger.error("Model not trained or loaded.")
            return None, None
            
        dtest = xgb.DMatrix(X)
        probs = self.model.predict(dtest)
        preds = (probs > 0.5).astype(int)
        
        return preds, probs

    def save(self, path):
        if self.model:
            self.model.save_model(path)
            self.logger.info(f"XGBoost model saved to {path}")
        else:
            self.logger.error("No model to save.")

    def load(self, path):
        if not os.path.exists(path):
            self.logger.error(f"Model file not found: {path}")
            return
            
        self.model = xgb.Booster()
        self.model.load_model(path)
        self.logger.info(f"XGBoost model loaded from {path}")
