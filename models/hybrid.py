import numpy as np
from src.utils import logger

from typing import Dict, Any, List, Tuple
import pandas as pd
from .xgboost_model import XGBoostDetector
from .kitsune import KitNET

class HybridDetector:
    def __init__(self, xgb_model: XGBoostDetector, kitsune_model: KitNET, config: Dict[str, Any]):
        self.xgb = xgb_model
        self.kitsune = kitsune_model
        self.config = config
        self.logger = logger

    def detect(self, X, input_df=None):
        """
        Runs both models and combines the results.
        
        Args:
            X: Input features (numpy array or DataFrame)
            input_df: Raw DataFrame containing IPs/Ports for heuristic checks (optional)
            
        Returns:
            dict: Results containing verdict, scores, and details.
        """
        # 1. XGBoost Prediction
        xgb_preds, xgb_probs = self.xgb.predict(X)
        
        # 2. Kitsune Anomaly Score
        # Kitsune needs consistent feature set. Assuming X matches training.
        kitsune_scores = self.kitsune.predict(X)
        
        # 3. Hybrid Logic
        # If XGBoost says DoS (1), we trust it.
        # If XGBoost says Benign (0), we check Kitsune.
        # If Kitsune score > Threshold, we flag as "Anomaly" (Potential Zero-Day or subtle DoS).
        
        final_preds = []
        reasons = []
        
        for i in range(len(X)):
            xgb_label = xgb_preds[i]
            k_score = kitsune_scores[i]
            k_thresh = self.kitsune.threshold
            
            # Initial Verdict
            verdict = "Benign"
            reason = "Clean"
            
            if xgb_label == 1:
                verdict = "DoS/DDoS"
                reason = f"XGBoost Confidence: {xgb_probs[i]:.2f}"
            elif k_score > k_thresh:
                verdict = "Anomaly"
                reason = f"Kitsune RMSE: {k_score:.2f} > {k_thresh:.2f}"
                
            # --- Override Logic: Safe Broadcasts ---
            if verdict != "Benign" and input_df is not None:
                if self._is_safe_broadcast(input_df.iloc[i]):
                    verdict = "Benign"
                    reason = "Clean (Safe Broadcast)"
            
            final_preds.append(verdict)
            reasons.append(reason)
                
        return {
            "xgb_preds": xgb_preds,
            "xgb_probs": xgb_probs,
            "kitsune_scores": kitsune_scores,
            "final_preds": final_preds,
            "reasons": reasons
        }

    def _is_safe_broadcast(self, row):
        """
        Checks if a flow is a safe/low-volume broadcast or multicast.
        """
        try:
            # 1. Volume Check (Must be low volume)
            # User threshold: 10
            if row.get('total fwd packets', 999) > 10:
                return False
                
            dst_ip = str(row.get('dst_ip', ''))
            dst_port = int(row.get('dst_port', 0))

            # 2. IP Check
            # Broadcast (.255) or Multicast (RFC 5771: 224.0.0.0 - 239.255.255.255)
            is_broadcast_ip = dst_ip.endswith('.255') or dst_ip == '255.255.255.255'
            try:
                first_octet = int(dst_ip.split('.')[0])
                is_multicast_ip = 224 <= first_octet <= 239
            except (ValueError, IndexError):
                is_multicast_ip = False

            # 3. Port Check (NetBIOS, SSDP, mDNS, DHCP)
            # 137, 138: NetBIOS
            # 1900: SSDP
            # 5353: mDNS
            # 67/68: DHCP
            safe_ports = {137, 138, 1900, 5353, 67, 68}
            is_safe_port = dst_port in safe_ports

            # Allow only if ALL 3 conditions are met (volume + IP + port)
            if (is_broadcast_ip or is_multicast_ip) and is_safe_port:
                return True
                
            return False
            
        except Exception:
            return False
