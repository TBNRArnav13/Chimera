# Unified DDoS Detection System - User Manual

## System Overview

The Unified DDoS Detection System is a sophisticated cybersecurity tool that combines machine learning and deep learning techniques to detect Distributed Denial of Service (DDoS) attacks in network traffic. The system employs a hybrid approach using two complementary models:

1. **XGBoost Classifier** - Supervised learning model trained on labeled attack data
2. **Kitsune AutoEncoder** - Unsupervised anomaly detection model for zero-day attacks
3. **Hybrid Engine** - Intelligent fusion system that combines both models' outputs

## System Architecture Flow Diagram

```
Input File (CSV/PCAP)
        ↓
Input Handler & Validation
        ↓
Feature Extraction (if PCAP)
        ↓
Data Preprocessing & Normalization
        ↓
┌─────────────────┐    ┌─────────────────┐
│   XGBoost       │    │   Kitsune       │
│   Classifier    │    │   AutoEncoder   │
│   (Supervised)  │    │   (Unsupervised)│
└─────────────────┘    └─────────────────┘
        ↓                       ↓
        └───────┬───────────────┘
                ↓
        Hybrid Decision Engine
                ↓
        Final Classification
                ↓
    Report Generation & Output

```

## Installation and Setup

### Prerequisites
- Python 3.8 or higher
- Windows Operating System
- At least 8GB RAM (16GB recommended for large datasets)
- GPU support optional (NVIDIA CUDA for enhanced performance)

### Quick Start (Windows)
1. Double-click `run.bat` to automatically setup environment and start the system
2. The batch file will:
   - Create a Python virtual environment
   - Install all required dependencies
   - Launch the interactive menu

### Manual Installation
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Command Line Usage

### Interactive Mode (Recommended)
```cmd
python run.py
```
This launches an interactive menu with options:
1. Train Kitsune (Benign Only)
2. Train XGBoost (Benign + DoS)
3. Train All (Unified)
4. Detect (Single File)
5. Exit

### Direct Command Mode

#### Training Commands
```cmd
# Train only Kitsune model
python run.py train_kitsune

# Train only XGBoost model  
python run.py train_xgboost

# Train both models
python run.py train_all
```

#### Detection Commands
```cmd
# Detect threats in a file
python run.py detect --input "path/to/file.csv"
python run.py detect --input "path/to/file.pcap"
```

## File Location Specifications

### Relative Paths (Recommended)
The system is designed to work with relative paths from the project root:
```cmd
# CSV files
python run.py detect --input "Dataset/test_file.csv"

# PCAP files  
python run.py detect --input "Dataset/test.pcap"

# Tier datasets
python run.py detect --input "Dataset/Tier2_BenignHeavy_1.csv"
```

### Absolute Paths (Also Supported)
```cmd
# Full Windows paths
python run.py detect --input "C:\Users\Username\Documents\network_data.pcap"
python run.py detect --input "E:\Security\Datasets\suspicious_traffic.csv"
```

### Path Handling Rules
- **Quotes**: Always use quotes around paths containing spaces
- **Backslashes**: Use either `\` or `/` - system handles both
- **Case Sensitivity**: Windows paths are case-insensitive
- **Special Characters**: Avoid special characters in filenames for best compatibility

## Supported File Formats

### CSV Files (.csv)
- Pre-processed network flow data
- Must contain the required feature columns (see Technical Documentation)
- Can include ground truth labels for accuracy assessment
- Maximum recommended size: 100,000 rows per file (configurable)

### PCAP Files (.pcap, .pcapng)
- Raw network packet captures
- Automatically processed through feature extraction pipeline
- Supports bidirectional flow analysis
- Compatible with Wireshark, tcpdump, and other standard tools

## Configuration Options

### config.yaml Settings

#### Dataset Paths
```yaml
datasets:
  benign: "Dataset/PolishedBenign/Polished_benign.csv"
  dos: "Dataset/PolishedDos/"
```

#### Model Parameters
```yaml
# XGBoost Configuration
xgboost:
  max_depth: 6
  learning_rate: 0.1
  n_estimators: 100
  objective: "binary:logistic"

# Kitsune Configuration  
kitsune:
  max_autoencoder_size: 10
  learning_rate: 0.001
  hidden_ratio: 0.75
  threshold_std_factor: 3.0
```

#### Detection Thresholds
```yaml
thresholds:
  malicious_file_ratio: 0.30  # 30% malicious flows = file flagged as malicious
```

## Output Structure

Each detection run creates a timestamped output directory:
```
outputs/
└── filename_YYYYMMDD_HHMMSS/
    ├── logs/
    │   └── technical_debug.log
    ├── predictions/
    │   ├── benign/
    │   │   └── benign_flows.json
    │   ├── ddos/
    │   │   └── dos_flows.json
    │   └── miscellaneous/
    │       └── anomaly_flows.json
    └── report/
        └── Report.md
```

## Understanding Results

### Classification Categories
- **Benign**: Normal, legitimate network traffic
- **DoS/DDoS**: Confirmed attack traffic detected by XGBoost
- **Anomaly**: Suspicious traffic detected by Kitsune (potential zero-day)

### File Verdicts
- **SAFE**: Less than 30% malicious flows detected
- **SUSPICIOUS**: Contains anomalies but below malicious threshold
- **MALICIOUS**: More than 30% flows classified as attacks

### Confidence Metrics
- **XGBoost Confidence**: Probability score (0.0-1.0) for attack classification
- **Kitsune RMSE**: Reconstruction error score (higher = more anomalous)

## Troubleshooting

### Common Issues

#### "File not found" Error
- Verify file path is correct
- Use quotes around paths with spaces
- Check file permissions

#### "Models not found" Error
- Run training first: `python run.py train_all`
- Verify models directory contains .pkl and .json files

#### Memory Issues with Large Files
- Increase `max_rows_per_file` in config.yaml
- Process files in smaller chunks
- Ensure sufficient RAM available

#### GPU Detection Issues
- Install NVIDIA CUDA drivers
- Verify PyTorch CUDA installation: `torch.cuda.is_available()`
- System falls back to CPU automatically

### Performance Optimization

#### For Large Datasets
- Enable GPU acceleration (CUDA)
- Increase batch sizes in configuration
- Use SSD storage for faster I/O

#### For Real-time Detection
- Pre-train models on representative data
- Use CSV input format (faster than PCAP processing)
- Optimize feature selection in config.yaml

## Advanced Usage

### Batch Processing Multiple Files
```cmd
# Process multiple files sequentially
for %f in (Dataset\*.pcap) do python run.py detect --input "%f"
```

### Custom Feature Selection
Edit `selected_features` in config.yaml to include only relevant network features for your environment.

### Model Retraining
- Retrain periodically with new attack samples
- Use `train_all` command to update both models
- Backup existing models before retraining

## Security Considerations

- Run system in isolated environment for sensitive data
- Regularly update training datasets with latest attack patterns  
- Monitor false positive rates and adjust thresholds accordingly
- Validate results with network security experts

## Support and Maintenance

### Log Analysis
- Check `technical_debug.log` for detailed execution information
- Monitor system performance metrics
- Review prediction accuracy using ground truth labels

### Model Updates
- Retrain models monthly or after significant network changes
- Update feature selection based on network environment
- Adjust detection thresholds based on operational requirements

This user manual provides comprehensive guidance for operating the Unified DDoS Detection System effectively and safely.