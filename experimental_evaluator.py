import os
import sys
import yaml
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime

# Adjust path to import Chimera src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.utils import setup_logger
from src.data_loader import load_csv, load_config
from models.kitsune import KitNET
from models.xgboost_model import XGBoostDetector
from models.hybrid import HybridDetector

logger = setup_logger("Evaluator", log_filename="experimental_data/eval_log.txt")

def evaluate_models():
    os.makedirs("experimental_data", exist_ok=True)
    
    config = load_config()
    benign_path = config['datasets']['benign']
    dos_dir = config['datasets']['dos']
    
    # Check if models exist
    k_path = os.path.join(config['directories']['models'], "kitsune_model.pkl")
    x_path = os.path.join(config['directories']['models'], "xgboost_model.json")
    
    if not os.path.exists(k_path) or not os.path.exists(x_path):
        logger.error("Models not found! Please run training first (python run.py train_all).")
        return
        
    logger.info("Loading models...")
    kitsune = KitNET.load(k_path)
    xgb_model = XGBoostDetector(config['xgboost'])
    xgb_model.load(x_path)
    hybrid = HybridDetector(xgb_model, kitsune, config)
    
    # Load feature lists
    feature_list = config.get('selected_features', [])
    selected_features_lower = [f.strip().lower() for f in feature_list]
    
    # Metrics tracking
    metrics = {
        'total_flows': 0,
        'true_positives': {'xgb': 0, 'kitsune': 0, 'hybrid': 0},
        'true_negatives': {'xgb': 0, 'kitsune': 0, 'hybrid': 0},
        'false_positives': {'xgb': 0, 'kitsune': 0, 'hybrid': 0},
        'false_negatives': {'xgb': 0, 'kitsune': 0, 'hybrid': 0}
    }
    
    file_results = {}
    
    # Process files
    files_to_process = []
    if "--files" in sys.argv:
        idx = sys.argv.index("--files")
        # take all arguments after --files as the file list, unless we hit another flag
        for arg in sys.argv[idx+1:]:
            if arg.startswith("--"):
                break
            files_to_process.append(arg)
    else:
        files_to_process = [benign_path]
        if os.path.exists(dos_dir):
            for f in os.listdir(dos_dir):
                if f.endswith('.csv'):
                    files_to_process.append(os.path.join(dos_dir, f))
                    
    logger.info(f"Found {len(files_to_process)} files to evaluate.")
    
    for filepath in files_to_process:
        filename = os.path.basename(filepath)
        logger.info(f"Evaluating {filename}...")
        
        # We need labels for evaluation.
        # Check if malicious based on filename or explicit label column
        is_attack_file = "benign" not in filename.lower()
        
        skip_rows_val = 0
        if "--skip-rows" in sys.argv:
            try:
                skip_rows_val = int(sys.argv[sys.argv.index("--skip-rows")+1])
            except (ValueError, IndexError):
                skip_rows_val = 0
                
        df = load_csv(filepath, skip_rows=skip_rows_val)
        if df is None or df.empty:
            continue
            
        # Ensure features
        for f in selected_features_lower:
            if f not in df.columns:
                df[f] = 0.0
                
        X = df[selected_features_lower].values
        
        # True labels
        if 'label' in df.columns:
            y_true = df['label'].astype(str).str.upper().apply(lambda x: 0 if x in ['BENIGN', '0', '0.0'] else 1).values
        else:
            y_true = np.ones(len(df)) if is_attack_file else np.zeros(len(df))
            
        metrics['total_flows'] += len(df)
        
        # 1. XGBoost Only
        xgb_preds, _ = xgb_model.predict(X)
        
        # 2. Kitsune Only
        kitsune_rmse = kitsune.predict(X)
        kitsune_preds = (kitsune_rmse > kitsune.threshold).astype(int)
        
        # 3. Hybrid
        hybrid_results = hybrid.detect(X, input_df=df)
        hybrid_preds_str = hybrid_results['final_preds']
        # Map string to binary label
        hybrid_preds = np.array([0 if p == "Benign" else 1 for p in hybrid_preds_str])
        
        # Calculate file-level metrics
        file_stats = {
            'total': len(y_true),
            'attacks': int(sum(y_true)),
            'benign': int(len(y_true) - sum(y_true))
        }
        
        for model, preds in [('xgb', xgb_preds), ('kitsune', kitsune_preds), ('hybrid', hybrid_preds)]:
            tp = int(((y_true == 1) & (preds == 1)).sum())
            tn = int(((y_true == 0) & (preds == 0)).sum())
            fp = int(((y_true == 0) & (preds == 1)).sum())
            fn = int(((y_true == 1) & (preds == 0)).sum())
            
            metrics['true_positives'][model] += tp
            metrics['true_negatives'][model] += tn
            metrics['false_positives'][model] += fp
            metrics['false_negatives'][model] += fn
            
            file_stats[f'{model}_tp'] = tp
            file_stats[f'{model}_tn'] = tn
            file_stats[f'{model}_fp'] = fp
            file_stats[f'{model}_fn'] = fn
            
        file_results[filename] = file_stats
        
    # Calculate final aggregate metrics
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "total_flows_evaluated": metrics['total_flows'],
        "models": {}
    }
    
    for model in ['xgb', 'kitsune', 'hybrid']:
        tp = metrics['true_positives'][model]
        tn = metrics['true_negatives'][model]
        fp = metrics['false_positives'][model]
        fn = metrics['false_negatives'][model]
        
        total = tp + tn + fp + fn
        accuracy = (tp + tn) / total if total > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        final_report["models"][model] = {
            "confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn},
            "accuracy": round(accuracy * 100, 4),
            "FPR": round(fpr * 100, 4),
            "FNR": round(fnr * 100, 4),
            "precision": round(precision * 100, 4),
            "recall": round(recall * 100, 4)
        }
        
    # Calculate improvements
    prev_xgb_fnr = final_report["models"]["xgb"]["FNR"]
    hybrid_fnr = final_report["models"]["hybrid"]["FNR"]
    fnr_reduction = ((prev_xgb_fnr - hybrid_fnr) / prev_xgb_fnr * 100) if prev_xgb_fnr > 0 else 0
    
    prev_kitsune_fpr = final_report["models"]["kitsune"]["FPR"]
    hybrid_fpr = final_report["models"]["hybrid"]["FPR"]
    fpr_reduction = ((prev_kitsune_fpr - hybrid_fpr) / prev_kitsune_fpr * 100) if prev_kitsune_fpr > 0 else 0
    
    acc_improvement = final_report["models"]["hybrid"]["accuracy"] - final_report["models"]["xgb"]["accuracy"]
    
    final_report["paper_claims_check"] = {
        "Claimed_Hybrid_Accuracy_99.2%": final_report["models"]["hybrid"]["accuracy"],
        "Claimed_FNR_Reduction_68%": round(fnr_reduction, 2),
        "Claimed_FPR_Reduction_79%": round(fpr_reduction, 2),
        "Claimed_Accuracy_Improvement_0.7%": round(acc_improvement, 2),
        "Claimed_Hybrid_FNR_0.8%": hybrid_fnr,
        "Claimed_Hybrid_FPR_1.2%": hybrid_fpr
    }
    
    final_report["file_breakdown"] = file_results
    
    # Save to disk
    run_tag = ""
    if "--tag" in sys.argv:
        run_tag = sys.argv[sys.argv.index("--tag")+1]
    elif len(sys.argv) == 2 and not sys.argv[1].startswith("--"):
        run_tag = sys.argv[1]
        
    suffix = f"_{run_tag}" if run_tag else ""
    report_path = f"experimental_data/empirical_results{suffix}.json"
    
    with open(report_path, 'w') as f:
        json.dump(final_report, f, indent=4)
        
    logger.info(f"Evaluation complete! Results saved to {report_path}")
    print(json.dumps(final_report["paper_claims_check"], indent=2))

if __name__ == "__main__":
    evaluate_models()
