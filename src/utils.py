from typing import Dict, Optional
import logging
import os
import sys
import torch
import xgboost as xgb
from datetime import datetime

def setup_logger(name: str, log_dir: str = "outputs/logs", log_filename: Optional[str] = None) -> logging.Logger:
    """
    Sets up a logger that writes to console and a file.
    
    Args:
        name: Logger name
        log_dir: Directory to save the log file (if log_filename is None)
        log_filename: Specific path to the log file (overrides log_dir default naming)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid adding handlers multiple times
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Console Handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File Handler
    if log_filename:
        # Ensure parent dir exists
        os.makedirs(os.path.dirname(log_filename), exist_ok=True)
        log_path = log_filename
    else:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"Unified_DDoS_System_{timestamp}.log")

    from logging.handlers import RotatingFileHandler
    
    # Rotating File Handler (10MB per file, max 5 backups)
    fh = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

def get_device() -> Dict[str, str]:
    """
    Detects available hardware (CPU/GPU) for PyTorch and XGBoost.
    """
    device_info = {}
    
    # PyTorch (Kitsune)
    if torch.cuda.is_available():
        device_info['pytorch'] = 'cuda'
        device_info['torch_name'] = torch.cuda.get_device_name(0)
    else:
        device_info['pytorch'] = 'cpu'
        device_info['torch_name'] = 'CPU'

    # XGBoost
    # XGBoost automatically handles GPU if tree_method='gpu_hist' is set and drivers are available.
    # We will return a helpful string to log.
    try:
        import subprocess
        # Safer: explicit arguments, no shell
        subprocess.run(['nvidia-smi'], capture_output=True, check=True)
        device_info['xgboost'] = 'gpu_hist'
    except (subprocess.CalledProcessError, FileNotFoundError):
        device_info['xgboost'] = 'hist' # fallback to optimized CPU hist

    return device_info

logger = setup_logger("Unified_DDoS_System")
