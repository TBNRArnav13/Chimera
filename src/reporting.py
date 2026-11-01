import os
import pandas as pd
from datetime import datetime
from src.utils import logger

class ReportGenerator:
    def __init__(self, config, output_dir="outputs/reports"):
        self.config = config
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def generate_report(self, results, input_file, stats, models_used, run_dir=None, df=None):
        """
        Generates a markdown report for the run.
        """
        if run_dir:
            # Use specific run folder structure
            report_dir = os.path.join(run_dir, "report")
            pred_dir = os.path.join(run_dir, "predictions")
            os.makedirs(report_dir, exist_ok=True)
            os.makedirs(os.path.join(pred_dir, "benign"), exist_ok=True)
            os.makedirs(os.path.join(pred_dir, "ddos"), exist_ok=True)
            os.makedirs(os.path.join(pred_dir, "miscellaneous"), exist_ok=True)
            
            filename = "Report.md"
            filepath = os.path.join(report_dir, filename)
        else:
            # Fallback
            filepath = os.path.join(self.output_dir, f"Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate summary stats
        final_preds = results['final_preds']
        total_flows = len(final_preds)
        dos_count = final_preds.count("DoS/DDoS")
        anomaly_count = final_preds.count("Anomaly")
        benign_count = final_preds.count("Benign")
        
        dos_percent = (dos_count / total_flows) * 100 if total_flows > 0 else 0
        
        # Get threshold from config (default 25%)
        # Note: Config value is ratio (0.25), convert to percent (25)
        thresh_ratio = self.config.get('thresholds', {}).get('malicious_file_ratio', 0.25)
        thresh_percent = thresh_ratio * 100
        
        verdict = "SAFE"
        if dos_percent > thresh_percent: 
            verdict = "MALICIOUS"
        elif anomaly_count > 0:
            verdict = "SUSPICIOUS"

        # --- Save Segregated CSVs ---
        if run_dir:
            # We assume results['df'] might exist or we construct from indices if input was DF
            # Or simpler: We don't have the original features here easily unless passed.
            # TODO: Ideally pass the full DF to generate_report to save it. 
            pass # See next block for fixing this integration
        
        content = f"""# Unified DDoS Detection Report
**Date**: {timestamp}
**Input File**: `{input_file}`
**Verdict**: **{verdict}**

## Summary
- **Total Flows**: {total_flows}
- **Detected DoS/DDoS**: {dos_count}
- **Detected Anomalies**: {anomaly_count}
- **Benign Flows**: {benign_count}

## Models Used
- XGBoost: `{models_used.get('xgboost', 'Unknown')}`
- Kitsune: `{models_used.get('kitsune', 'Unknown')}`

## Investigation Details
| Flow ID | Prediction | Reason |
| :--- | :--- | :--- |
"""
        # Add first 50 interesting rows (DoS/Anomaly) to avoid massive reports
        count = 0
        for i in range(total_flows):
            if final_preds[i] != "Benign":
                content += f"| {i} | {final_preds[i]} | {results['reasons'][i]} |\n"
                count += 1
                if count >= 50:
                    break
        
        if count == 0:
            content += "| - | Benign | All clean |\n"

        # --- Accuracy Analysis (If Labels Provided) ---
        if df is not None and 'label' in df.columns:
            try:
                # Add Predictions if not present (safeguard)
                if 'Prediction' not in df.columns:
                    df['Prediction'] = final_preds
                
                # Calculate Matrix
                # TP: Label!=Benign & Pred!=Benign (Attack Caught)
                # TN: Label==Benign & Pred==Benign (Benign Ignored)
                # FP: Label==Benign & Pred!=Benign (False Alarm)
                # FN: Label!=Benign & Pred==Benign (Attack Missed)
                
                # Normalize Label to upper for check
                # Fix: Handle numeric 0/0.0 as Benign too
                y_true = df['label'].astype(str).str.upper().apply(lambda x: x not in ['BENIGN', '0', '0.0']) # True if Attack
                y_pred = df['Prediction'] != 'Benign' # True if Attack
                
                tp = ((y_true == True) & (y_pred == True)).sum()
                tn = ((y_true == False) & (y_pred == False)).sum()
                fp = ((y_true == False) & (y_pred == True)).sum()
                fn = ((y_true == True) & (y_pred == False)).sum()
                
                accuracy = (tp + tn) / total_flows if total_flows > 0 else 0
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                content += f"""
## Confusion Matrix & Accuracy
> **Auto-Analysis**: Ground Truth labels detected in input file.

| Metric | Value | Description |
| :--- | :--- | :--- |
| **True Positives (TP)** | {tp} | Attacks correctly caught |
| **False Positives (FP)** | {fp} | Benign flows wrongly flagged (False Alarms) |
| **True Negatives (TN)** | {tn} | Benign flows correctly ignored |
| **False Negatives (FN)** | {fn} | Attacks missed (Dangerous!) |
| **Accuracy** | {accuracy:.4f} | Overall correctness |
| **Precision** | {precision:.4f} | How strictly it Flags |
| **Recall** | {recall:.4f} | Detection Rate |
| **F1-Score** | {f1:.4f} | Balance of Precision & Recall |
"""
            except Exception as e:
                logger.error(f"Failed to calculate accuracy stats: {e}")


        with open(filepath, 'w') as f:
            f.write(content)
            
        logger.info(f"Report generated: {filepath}")
        return filepath

    def save_predictions(self, df, results, run_dir):
        """
        Saves the flows into segregated JSONs.
        """
        if not run_dir or df is None:
            return

        pred_dir = os.path.join(run_dir, "predictions")
        
        # Add predictions to DF
        df['Prediction'] = results['final_preds']
        df['Reason'] = results['reasons']
        
        # Split
        benign_df = df[df['Prediction'] == 'Benign']
        dos_df = df[df['Prediction'] == 'DoS/DDoS']
        misc_df = df[df['Prediction'] == 'Anomaly']
        
        # Save as JSON
        if not benign_df.empty:
            benign_df.to_json(os.path.join(pred_dir, "benign", "benign_flows.json"), orient='records', indent=4)
        if not dos_df.empty:
            dos_df.to_json(os.path.join(pred_dir, "ddos", "dos_flows.json"), orient='records', indent=4)
        if not misc_df.empty:
            misc_df.to_json(os.path.join(pred_dir, "miscellaneous", "anomaly_flows.json"), orient='records', indent=4)
            
        logger.info(f"Predictions saved (JSON) to {pred_dir}")
