import argparse
import sys
import os
import yaml
import pandas as pd
import logging
from datetime import datetime
from src.utils import logger, get_device
from src.data_loader import load_csv, combine_datasets
from src.input_handler import InputHandler
from src.reporting import ReportGenerator
from models.kitsune import KitNET
from models.xgboost_model import XGBoostDetector
from models.hybrid import HybridDetector

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def train_kitsune():
    logger.info("Starting Kitsune Training (Unsupervised)...")
    benign_path = CONFIG['datasets']['benign']
    
    # Load Benign for Kitsune
    logger.info(f"Loading Benign data for Kitsune from {benign_path}...")
    benign_df = load_csv(benign_path)
    if benign_df is None:
        logger.error("Failed to load benign data. Aborting Kitsune training.")
        return

    # Train Kitsune (Unsupervised)
    # Use only features, drop labels if exists
    input_dim = benign_df.shape[1] - 1 if 'label' in benign_df.columns else benign_df.shape[1]
    
    # Prepare X for Kitsune (drop label)
    X_benign = benign_df.drop(columns=['label'], errors='ignore').values
    
    # Get feature names for ensemble sub-AE group mapping
    feature_names = CONFIG.get('selected_features', [])
    feature_names = [f.strip().lower() for f in feature_names]

    kitsune = KitNET(input_dim, CONFIG['kitsune'], feature_names=feature_names)
    kitsune.train(X_benign)
    kitsune.save(os.path.join(CONFIG['directories']['models'], "kitsune_model.pkl"))
    logger.info("Kitsune Training Complete.")

def train_xgboost():
    logger.info("Starting XGBoost Training (Supervised)...")
    benign_path = CONFIG['datasets']['benign']
    dos_dir = CONFIG['datasets']['dos']
    
    # Train XGBoost (Supervised)
    logger.info("Loading Combined data for XGBoost...")
    combined_df = combine_datasets(benign_path, dos_dir)
    if combined_df is None:
        logger.error("Failed to load combined data. Aborting XGBoost training.")
        return

    # Encode Labels
    # Benign = 0, DoS = 1
    # Assuming 'label' column. Benign label is "BENIGN".
    # We need to normalize labels first.
    # Note: Using strict string checking might be brittle if case varies.
    combined_df['label'] = combined_df['label'].astype(str).apply(lambda x: 0 if x.strip().upper() == 'BENIGN' else 1)
    
    y = combined_df['label'].values
    X = combined_df.drop(columns=['label']).values
    
    xgb_model = XGBoostDetector(CONFIG['xgboost'])
    xgb_model.train(X, y)
    xgb_model.save(os.path.join(CONFIG['directories']['models'], "xgboost_model.json"))
    logger.info("XGBoost Training Complete.")

def train_all():
    train_kitsune()
    train_xgboost()

def detect_mode(input_file):
    # 0. Create Run Directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    # Sanitize filename
    base_name = "".join([c for c in base_name if c.isalpha() or c.isdigit() or c=='_']).rstrip()
    
    run_dir = os.path.join(CONFIG['directories']['outputs'], f"{base_name}_{timestamp}")
    
    # Subfolders
    log_dir = os.path.join(run_dir, "logs")
    pred_dir = os.path.join(run_dir, "predictions")
    report_dir = os.path.join(run_dir, "report")
    
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(pred_dir, exist_ok=True)
    
    # 1. Setup Logger for this run
    # Disconnect existing handlers if any to avoid pollution (optional, or just add new one)
    # For simplicity, we just add a new file handler to the existing logger or setup a run-specific one.
    # We'll re-setup the global logger to point to this new file.
    log_file = os.path.join(log_dir, "technical_debug.log")
    
    # Force setup logger to new file
    # Note: This modifies the global logger.
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    
    logger.info(f"=== Starting New Detection Run: {run_dir} ===")

    # Security Fix: Path Traversal Validation
    input_file = os.path.abspath(input_file)
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return
    if not os.path.isfile(input_file):
        logger.error(f"Input path is not a file: {input_file}")
        return
        
    # Check for suspicious patterns (e.g. system files)
    if ".." in input_file or input_file.startswith("/etc") or input_file.startswith("C:\\Windows"):
         logger.warning(f"Suspicious file path blocked: {input_file}")
         return

    logger.info(f"Input: {input_file}")
    
    handler_obj = InputHandler(CONFIG)
    df = handler_obj.process_file(input_file)
    
    if df is None:
        logger.error("Failed to process input file.")
        return

    # Feature: Save extracted features to CSV if input was PCAP
    if input_file.lower().endswith('.pcap') or input_file.lower().endswith('.pcapng'):
        csv_name = f"{base_name}_extracted.csv"
        csv_path = os.path.join(run_dir, csv_name)
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved extracted features to: {csv_path}")

    # Load Models
    k_path = os.path.join(CONFIG['directories']['models'], "kitsune_model.pkl")
    x_path = os.path.join(CONFIG['directories']['models'], "xgboost_model.json")
    
    kitsune = KitNET.load(k_path)
    xgb_model = XGBoostDetector(CONFIG['xgboost'])
    xgb_model.load(x_path)
    
    if not kitsune or not xgb_model.model:
        logger.error("Models not found. Please train first.")
        return

    # Prepare Data
    # 1. Ensure all features exist and strictly select them
    # This prevents 'label', 'IPs', 'Prediction', 'Reason' from polluting the model input
    feature_list = CONFIG.get('selected_features', [])
    
    # Fill missing features with 0 (robustness)
    for f in feature_list:
        if f not in df.columns:
            df[f] = 0.0
            
    # Select only the features the model expects, in order
    X = df[feature_list].values
    
    # Run Hybrid
    detector = HybridDetector(xgb_model, kitsune, CONFIG)
    results = detector.detect(X, input_df=df)
    
    # Report & CSVs
    reporter = ReportGenerator(CONFIG)
    reporter.generate_report(results, input_file, {}, {'xgboost': x_path, 'kitsune': k_path}, run_dir=run_dir, df=df)
    reporter.save_predictions(df, results, run_dir)
    
    print(f"\n[SUCCESS] Run Complete. Output: {run_dir}")
    print(f"  - Report: {os.path.join(report_dir, 'Report.md')}")
    print(f"  - Logs: {log_file}")
    
    # Clean up handler to avoid duplicate logs in next run if process stays alive
    logger.removeHandler(handler)

def interactive_menu():
    while True:
        print("\n=== Unified DDoS Detection System ===")
        print("1. Train Kitsune (Benign Only)")
        print("2. Train XGBoost (Benign + DoS)")
        print("3. Train All (Unified)")
        print("4. Detect (Single File)")
        print("5. Exit")
        choice = input("Select option: ")
        
        if choice == '1':
            train_kitsune()
        elif choice == '2':
            train_xgboost()
        elif choice == '3':
            train_all()
        elif choice == '4':
            path = input("Enter path to CSV/PCAP file: ").strip('"').strip("'")
            detect_mode(path)
        elif choice == '5':
            sys.exit()
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified DDoS Detection System")
    parser.add_argument('mode', nargs='?', choices=['train_kitsune', 'train_xgboost', 'train_all', 'detect'], help="Execution mode")
    parser.add_argument('--input', help="Input file for detection")
    
    args = parser.parse_args()
    
    if args.mode == 'train_kitsune':
        train_kitsune()
    elif args.mode == 'train_xgboost':
        train_xgboost()
    elif args.mode == 'train_all':
        train_all()
    elif args.mode == 'detect':
        if not args.input:
            print("Error: --input required for detect mode")
        else:
            detect_mode(args.input)
    else:
        interactive_menu()
