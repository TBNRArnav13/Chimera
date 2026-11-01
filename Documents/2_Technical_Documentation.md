# Unified DDoS Detection System - Complete Technical Documentation

## System Architecture Overview

The Unified DDoS Detection System is a sophisticated multi-model cybersecurity framework that combines supervised and unsupervised machine learning approaches to detect Distributed Denial of Service attacks. The system architecture follows a modular design pattern with clear separation of concerns across data processing, model inference, and result aggregation layers.

## File Hierarchy and Structure

```
Unified_DDoS_System/
├── config.yaml                 # Central configuration file
├── requirements.txt            # Python dependencies
├── run.py                     # Main entry point and orchestrator
├── run.bat                    # Windows batch launcher
├── analyze_tier2.py           # Post-analysis utility
├── debug_startup.py           # System diagnostics tool
│
├── src/                       # Core processing modules
│   ├── data_loader.py         # CSV data loading and preprocessing
│   ├── feature_extractor.py   # PCAP to feature conversion
│   ├── input_handler.py       # File validation and routing
│   ├── reporting.py           # Report generation and output
│   ├── utils.py              # Logging and device detection
│   └── __pycache__/          # Python bytecode cache
│
├── models/                    # Machine learning models
│   ├── xgboost_model.py      # XGBoost classifier implementation
│   ├── kitsune.py            # Kitsune autoencoder implementation  
│   ├── hybrid.py             # Hybrid decision engine
│   ├── kitsune_model.pkl     # Trained Kitsune model (generated)
│   ├── xgboost_model.json    # Trained XGBoost model (generated)
│   └── __pycache__/          # Python bytecode cache
│
├── Dataset/                   # Training and testing data
│   ├── PolishedBenign/       # Clean network traffic
│   │   └── Polished_benign.csv
│   ├── PolishedDos/          # Attack traffic samples
│   │   ├── Polished_Dos_DNS.csv
│   │   ├── Polished_Dos_LDAP.csv
│   │   ├── Polished_Dos_MSSQL.csv
│   │   ├── Polished_Dos_NetBIOS.csv
│   │   ├── Polished_Dos_NTP.csv
│   │   ├── Polished_Dos_SNMP.csv
│   │   ├── Polished_Dos_SSDP.csv
│   │   ├── Polished_Dos_Syn.csv
│   │   ├── Polished_Dos_TFTP.csv
│   │   └── Polished_Dos_UDP.csv
│   ├── test*.pcap            # Raw packet capture files
│   ├── Tier1_PureAttack_Mix_*.csv    # Pure attack datasets
│   ├── Tier2_BenignHeavy_*.csv       # Benign-heavy mixed datasets
│   └── Tier3_Mixed_Ratio_*.csv       # Balanced mixed datasets
│
└── outputs/                   # Generated results and logs
    └── [timestamp_directories]/
        ├── logs/
        ├── predictions/
        └── report/
```

## Detailed Component Analysis

### 1. Configuration Management (config.yaml)

The central configuration file defines all system parameters:

**Directory Structure Configuration:**
```yaml
directories:
  models: "models/"           # Model storage location
  training: "training/"       # Training data cache
  detection: "detection/"     # Detection workspace
  datasets: "datasets/"       # Dataset root
  outputs: "outputs/"         # Results output
  logs: "outputs/logs/"       # Log file location
```

**Dataset Configuration:**
```yaml
datasets:
  benign: "Dataset/PolishedBenign/Polished_benign.csv"  # Clean traffic
  dos: "Dataset/PolishedDos/"                           # Attack samples

data_loading:
  max_rows_per_file: 100000  # Memory management limit
```

**Model Hyperparameters:**
- **XGBoost Parameters**: Gradient boosting configuration for supervised classification
- **Kitsune Parameters**: Autoencoder architecture and anomaly detection thresholds
- **Feature Selection**: 34 carefully selected network flow features

### 2. Main Orchestrator (run.py)

The main entry point implements a command-line interface with both interactive and direct execution modes:

**Core Functions:**
- `load_config()`: Configuration file parsing and validation
- `train_kitsune()`: Unsupervised model training on benign data
- `train_xgboost()`: Supervised model training on labeled data
- `train_all()`: Unified training pipeline
- `detect_mode()`: Real-time detection and analysis
- `interactive_menu()`: User-friendly interface

**Execution Flow:**
1. Configuration loading and validation
2. Command-line argument parsing
3. Mode selection (train/detect/interactive)
4. Model initialization and loading
5. Data processing pipeline execution
6. Result generation and output

### 3. Data Processing Pipeline

#### 3.1 Data Loader (src/data_loader.py)

**Primary Functions:**
- `load_csv()`: CSV file loading with feature standardization
- `combine_datasets()`: Multi-file dataset aggregation

**Data Processing Steps:**
1. **File Validation**: Existence and format verification
2. **Memory Management**: Row limit enforcement (configurable)
3. **Column Standardization**: Lowercase, whitespace removal
4. **Feature Selection**: Intersection with configured feature set
5. **Data Cleaning**: Infinite value replacement, NaN handling
6. **Label Processing**: Binary encoding (BENIGN=0, Attack=1)

**Robustness Features:**
- Missing column handling with zero-fill
- Infinite value detection and replacement
- Memory-efficient loading for large files
- Error logging and graceful degradation

#### 3.2 Feature Extractor (src/feature_extractor.py)

**PCAP Processing Pipeline:**
1. **Packet Parsing**: Scapy-based packet dissection
2. **Flow Aggregation**: Bidirectional session reconstruction
3. **Statistical Calculation**: 34 network flow features
4. **Feature Standardization**: Consistent output format

**Bidirectional Flow Analysis:**
- **Flow Identification**: 5-tuple (src_ip, dst_ip, src_port, dst_port, protocol)
- **Direction Determination**: Forward/backward packet classification
- **Session Reconstruction**: Temporal packet ordering and aggregation

**Extracted Features (34 total):**
- **Temporal Features**: Flow duration, inter-arrival times (IAT)
- **Volume Features**: Packet counts, byte counts, rates
- **Statistical Features**: Min, max, mean, standard deviation
- **Protocol Features**: TCP flags (PSH, URG), packet sizes
- **Directional Features**: Forward vs backward flow characteristics

**Feature Categories:**
1. **Basic Flow Metrics**: Duration, packet counts, byte counts
2. **Packet Size Statistics**: Length distributions per direction
3. **Timing Analysis**: Inter-arrival time patterns
4. **Rate Calculations**: Bytes/second, packets/second
5. **Protocol Flags**: TCP control flag analysis

#### 3.3 Input Handler (src/input_handler.py)

**File Type Support:**
- **CSV Files**: Pre-processed flow data (direct model input)
- **PCAP Files**: Raw packet captures (requires feature extraction)
- **PCAPNG Files**: Next-generation packet capture format

**Processing Logic:**
1. **File Validation**: Extension checking, existence verification
2. **Format Detection**: Automatic processing pipeline selection
3. **Error Handling**: Graceful failure with detailed logging

### 4. Machine Learning Models

#### 4.1 XGBoost Classifier (models/xgboost_model.py)

**Architecture:**
- **Algorithm**: Gradient Boosted Decision Trees
- **Objective**: Binary logistic regression
- **Hardware Acceleration**: GPU support via CUDA

**Training Process:**
1. **Data Preparation**: Feature matrix (X) and label vector (y)
2. **Parameter Configuration**: Depth, learning rate, estimators
3. **Hardware Detection**: Automatic GPU/CPU selection
4. **Training Execution**: Gradient boosting with early stopping
5. **Model Persistence**: JSON format serialization

**Inference Pipeline:**
1. **Data Matrix Creation**: XGBoost DMatrix format
2. **Probability Prediction**: Continuous output [0,1]
3. **Binary Classification**: Threshold-based decision (0.5)
4. **Confidence Scoring**: Probability as confidence metric

#### 4.2 Kitsune AutoEncoder (models/kitsune.py)

**Neural Architecture:**
```python
Input Layer (34 features)
    ↓
Encoder: Linear → ReLU → Linear → ReLU
    ↓
Bottleneck (compressed representation)
    ↓  
Decoder: Linear → ReLU → Linear
    ↓
Output Layer (34 reconstructed features)
```

**Training Methodology:**
1. **Unsupervised Learning**: Benign-only training data
2. **Reconstruction Objective**: Minimize Mean Squared Error (MSE)
3. **Threshold Calculation**: Statistical anomaly boundary
4. **Device Optimization**: Automatic GPU/CPU selection

**Anomaly Detection:**
- **Reconstruction Error**: RMSE between input and output
- **Threshold Setting**: Mean + (k × Standard Deviation)
- **Anomaly Scoring**: Continuous anomaly score
- **Binary Decision**: Score > Threshold = Anomaly

#### 4.3 Hybrid Decision Engine (models/hybrid.py)

**Decision Logic:**
```python
if XGBoost_prediction == "Attack":
    final_verdict = "DoS/DDoS"
    confidence = XGBoost_probability
elif Kitsune_score > Kitsune_threshold:
    final_verdict = "Anomaly"  
    confidence = Kitsune_RMSE
else:
    final_verdict = "Benign"
    confidence = "Clean"
```

**Advanced Heuristics:**
1. **Safe Broadcast Detection**: Low-volume multicast/broadcast filtering
2. **Volume Analysis**: Packet count thresholds for broadcast traffic
3. **Port-based Filtering**: Known safe services (NetBIOS, SSDP, mDNS)
4. **IP Pattern Recognition**: Broadcast and multicast IP identification

**Override Logic:**
- **Broadcast Traffic**: Automatic benign classification for safe broadcasts
- **Volume Thresholds**: Low packet count exemptions
- **Protocol Awareness**: Service-specific safe port recognition

### 5. Reporting and Output Generation

#### 5.1 Report Generator (src/reporting.py)

**Output Structure:**
```
outputs/filename_YYYYMMDD_HHMMSS/
├── logs/technical_debug.log           # Detailed execution log
├── predictions/
│   ├── benign/benign_flows.json      # Clean traffic flows
│   ├── ddos/dos_flows.json           # Attack traffic flows  
│   └── miscellaneous/anomaly_flows.json  # Suspicious flows
└── report/Report.md                   # Executive summary
```

**Report Components:**
1. **Executive Summary**: High-level verdict and statistics
2. **Detection Breakdown**: Per-category flow counts and percentages
3. **Investigation Details**: Individual flow analysis (top 50 threats)
4. **Accuracy Analysis**: Confusion matrix (if ground truth available)
5. **Model Information**: Training data and model file references

**Accuracy Metrics (when labels available):**
- **True Positives (TP)**: Attacks correctly identified
- **False Positives (FP)**: Benign traffic incorrectly flagged
- **True Negatives (TN)**: Benign traffic correctly ignored
- **False Negatives (FN)**: Attacks missed (critical metric)
- **Derived Metrics**: Precision, Recall, F1-Score, Accuracy

### 6. System Utilities

#### 6.1 Logging System (src/utils.py)

**Multi-destination Logging:**
- **Console Output**: Real-time progress monitoring
- **File Logging**: Persistent execution records
- **Timestamped Files**: Unique log per execution run

**Hardware Detection:**
- **PyTorch Device**: CUDA availability for Kitsune
- **XGBoost Acceleration**: GPU histogram optimization
- **Automatic Fallback**: CPU execution when GPU unavailable

#### 6.2 Analysis Tools

**analyze_tier2.py**: Post-execution analysis utility
- **Prediction Breakdown**: Category-wise flow analysis
- **Accuracy Assessment**: True/False positive calculation
- **Performance Metrics**: Model effectiveness evaluation

**debug_startup.py**: System diagnostic tool
- **Import Verification**: Module loading validation
- **Directory Creation**: Output structure testing
- **Environment Check**: Dependency availability

## Technical Flow Diagram - Complete Pipeline

```
┌─────────────────┐
│   Input File    │
│  (CSV/PCAP)     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Input Handler   │
│ - Validation    │
│ - Format Check  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│   CSV Path      │    │   PCAP Path     │
│ - Direct Load   │    │ - Feature       │
│ - Preprocessing │    │   Extraction    │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
          ┌─────────────────┐
          │ Feature Matrix  │
          │ (34 features)   │
          └─────────┬───────┘
                    │
                    ▼
    ┌───────────────┴───────────────┐
    │                               │
    ▼                               ▼
┌─────────────────┐    ┌─────────────────┐
│   XGBoost       │    │   Kitsune       │
│ - Supervised    │    │ - Unsupervised  │
│ - Binary Class  │    │ - Anomaly Score │
│ - Confidence    │    │ - RMSE Threshold│
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
          ┌─────────────────┐
          │ Hybrid Engine   │
          │ - Decision Fusion│
          │ - Heuristics    │
          │ - Final Verdict │
          └─────────┬───────┘
                    │
                    ▼
          ┌─────────────────┐
          │ Report Generator│
          │ - Markdown      │
          │ - JSON Outputs  │
          │ - Statistics    │
          └─────────────────┘
```

## Command Execution Technical Flow

### Training Mode Execution:

1. **Configuration Loading**: YAML parsing and validation
2. **Dataset Loading**: Multi-file CSV aggregation
3. **Data Preprocessing**: Feature standardization and cleaning
4. **Model Training**: 
   - Kitsune: Unsupervised autoencoder training on benign data
   - XGBoost: Supervised classification on labeled data
5. **Model Persistence**: Serialization to disk (PKL/JSON formats)
6. **Validation**: Training metrics and threshold calculation

### Detection Mode Execution:

1. **Input Validation**: File existence and format verification
2. **Data Processing**: Format-specific pipeline selection
3. **Feature Preparation**: 34-feature vector construction
4. **Model Loading**: Trained model deserialization
5. **Parallel Inference**: Simultaneous XGBoost and Kitsune execution
6. **Decision Fusion**: Hybrid engine verdict calculation
7. **Output Generation**: Multi-format result production

## Performance Characteristics

### Memory Usage:
- **Base System**: ~500MB Python environment
- **Model Loading**: ~100MB (XGBoost + Kitsune)
- **Data Processing**: Variable (depends on input size)
- **PCAP Processing**: ~2-3x input file size in memory

### Processing Speed:
- **CSV Processing**: ~10,000 flows/second
- **PCAP Processing**: ~1,000 packets/second (feature extraction)
- **Model Inference**: ~50,000 predictions/second (GPU)
- **Report Generation**: ~1-2 seconds (typical dataset)

### Scalability Limits:
- **Maximum CSV Size**: 100,000 rows (configurable)
- **PCAP File Size**: Limited by available RAM
- **Concurrent Processing**: Single-threaded (can be parallelized)

This technical documentation provides comprehensive coverage of the system's internal architecture, data flow, and implementation details for developers and system administrators.