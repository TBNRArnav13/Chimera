<div align="center">

# 🛡️ Chimera IDS
### Priority-Ordered Hierarchical Fusion Architecture for DoS/DDoS Detection

[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0%2B-18534F?style=for-the-badge)](https://xgboost.readthedocs.io/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge)](LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.1109%2FCICN70047.2026.11594396-00629B?style=for-the-badge&logo=ieee)](https://doi.org/10.1109/CICN70047.2026.11594396)
[![CI Status](https://img.shields.io/badge/build-passing-success?style=for-the-badge&logo=githubactions)](.github/workflows/ci.yml)

<p align="center">
  <b>Chimera</b> is an enterprise-grade hybrid Intrusion Detection System (IDS) designed for line-rate DoS/DDoS detection and zero-day threat mitigation. By coupling supervised gradient boosting with an unsupervised autoencoder ensemble through a priority-ordered hierarchy, Chimera delivers <b>99.70% empirical accuracy</b> and an ultralow <b>0.05% false negative rate</b> across 10 distinct attack vectors.
</p>

[Product Overview](#-product-overview) •
[2-Model Architecture](#-the-2-model-architecture) •
[Benchmark Performance](#-benchmark-performance) •
[Quick Start](#-quick-start) •
[CLI Usage](#-cli-usage-guide) •
[Published Research](#-published-research--citation) •
[Directory Layout](#-directory-layout) •
[License](#-license)

</div>

---

## 🚀 Product Overview

Denial of Service (DoS) and Distributed Denial of Service (DDoS) attacks pose existential risks to modern network services, regularly exceeding several terabits per second in volumetric scale. Standard Intrusion Detection Systems operate under two flawed extremes:
- **Purely Supervised Classifiers** (e.g., standard XGBoost, Random Forest) achieve exceptional precision on known attack signatures, but are **inherently blind to zero-day vectors** absent from their training data.
- **Purely Unsupervised Anomaly Detectors** (e.g., standard AutoEncoders) identify statistical deviations, but suffer from high false alarm rates and lower classification confidence.

**Chimera** resolves this dilemma through a **priority-ordered hierarchical fusion engine**. Grounded in the fundamental asymmetry of cybersecurity operations—where a missed attack (false negative) causes catastrophic downtime while a false alarm (false positive) is a manageable diagnostic event—Chimera guarantees that supervised detection precision is never diluted by voting averages, while unsupervised neural networks act as a reliable safety net for novel threats.

---

## ⚡ The 2-Model Architecture

Chimera employs exactly **two complementary models** orchestrated by a priority-ordered hybrid decision engine:

```text
                                  CHIMERA DETECTION PIPELINE
  
   Raw Packets (.pcap) / Extracted Flows (.csv)
                        │
                        ▼
   ┌────────────────────────────────────────────────────────────┐
   │    Input Ingestion & Feature Extraction (33 DFI Attributes)│
   └─────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
   ┌────────────────────────────────────────────────────────────┐
   │              Priority-Ordered Decision Engine              │
   │                                                            │
   │  [STAGE 1: Protocol-Aware Safe-Broadcast Heuristic]        │
   │   Identifies mDNS (port 5353), SSDP, local broadcast       │
   │   (224.0.0.0/4, 255.255.255.255) ─────────────► Benign     │
   │                                                            │
   │  [STAGE 2: Model 1 — Supervised XGBoost Classifier]        │
   │   Known attack patterns flagged (p_xgb ≥ 0.5) ─► MALICIOUS │
   │                                                            │
   │  [STAGE 3: Model 2 — B-DAP AutoEncoder Ensemble (Kitsune)] │
   │   Supervisor-cleared traffic routed to Kitsune-            │
   │   inspired 4-channel AutoEncoder Ensemble:                 │
   │   • Volume Sub-AutoEncoder    (7 features)                 │
   │   • Packet Size Sub-AE        (8 features)                 │
   │   • IAT Sub-AutoEncoder       (14 features)                │
   │   • TCP Flags Sub-AE          (4 features)                 │
   │   • Output AutoEncoder        (Combines sub-AE RMSE)       │
   │   RMSE > Threshold (μ + kσ) ──────────────────► ANOMALY    │
   │                                                            │
   │  [STAGE 4: Cleared by All Layers] ────────────► BENIGN     │
   └─────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
   ┌────────────────────────────────────────────────────────────┐
   │         Automated Reporting & MITRE ATT&CK Mapping         │
   │          (Executive Markdown Report & JSON Schema)         │
   └────────────────────────────────────────────────────────────┘
```

### 1. Model 1: Supervised XGBoost Classifier (`models/xgboost_model.py`)
- High-precision gradient-boosted decision tree ensemble trained with depth-6 regularization over balanced benign and multi-attack sets.
- Delivers microsecond response times for known volumetric and protocol floods.

### 2. Model 2: B-DAP AutoEncoder Ensemble (`models/kitsune.py`)
- **Benign-Data Alignment Processor (B-DAP)**: An ensemble autoencoder system inspired by the Kitsune architecture.
- Partitions the 33 flow attributes into **four domain-driven sub-autoencoders**:
  1. **Volume Group** (7 features): Flow duration, forward/backward packet counts, byte/packet rates.
  2. **Packet Size Group** (8 features): Max, min, mean, and standard deviation of packet lengths.
  3. **Inter-Arrival Time (IAT) Group** (14 features): Inter-arrival timing statistics across flow and forward/backward bursts.
  4. **TCP Control Flags Group** (4 features): PSH and URG directional flags.
- An **Output AutoEncoder** combines the reconstruction RMSE scores from all four sub-networks.
- Trained **exclusively on clean benign traffic**, measuring deviations against a statistical threshold ($\mu + k\sigma$) to catch novel, zero-day attack shifts.

### 3. Priority-Ordered Decision Engine (`models/hybrid.py`)
- Replaces naive majority voting with an asymmetric priority hierarchy. Traffic flagged by XGBoost is immediately classified without being diluted by unsupervised false negatives.
- **Protocol-Aware Safe-Broadcast Heuristic**: Built-in domain heuristic that inspects destination IP, destination port, and packet count to reclassify legitimate local broadcast/multicast services (NetBIOS, SSDP, mDNS, DHCP) as benign.

---

## 📊 Benchmark Performance

Chimera has been evaluated across **5.5 million unique network flows** drawn from an empirical corpus of **48.9 million flows** across **10 distinct DoS attack classes** (CIC-IDS2017 & CIC-DDoS2019):

### System Metrics Summary

| Evaluation Metric | Standalone XGBoost | Standalone B-DAP | Chimera Hybrid Engine |
| :--- | :---: | :---: | :---: |
| **Accuracy** | 99.82% | 79.56% | **99.70%** |
| **False Negative Rate (FNR)** | 0.18% | 22.43% | **0.05%** |
| **False Positive Rate (FPR)** | 0.17% | 20.44% | **2.72%** |
| **Cronbach's Alpha ($\alpha$) Reliability** | 1.000 | 0.811 | **0.999 (Excellent)** |
| **Zero-Day Attack Catch Rate** | 64.79% | 94.20% | **99.83%** |

> **Key Takeaway**: By deploying B-DAP behind XGBoost in a priority hierarchy, Chimera reduces the critical False Negative Rate from 0.18% down to **0.05%**—meaning fewer than 5 attacks out of 10,000 go undetected—while maintaining temporal consistency across unseen data splits ($\alpha = 0.999$).

### Throughput & Operational Footprint

| Pipeline Stage | Processing Latency | Throughput (Predictions/sec) | Memory Size |
| :--- | :---: | :---: | :---: |
| **XGBoost Inference (CPU)** | $12.5\ \mu\text{s}$ | $\sim 80{,}000\text{ flows/sec}$ | $0.42\text{ MB}$ |
| **XGBoost Inference (GPU)** | $5.0\ \mu\text{s}$ | $\sim 200{,}000\text{ flows/sec}$ | $0.42\text{ MB}$ |
| **B-DAP Ensemble Inference (CPU)** | $98.0\ \mu\text{s}$ | $\sim 10{,}000\text{ flows/sec}$ | $0.04\text{ MB}$ |
| **B-DAP Ensemble Inference (GPU)** | $20.0\ \mu\text{s}$ | $\sim 50{,}000\text{ flows/sec}$ | $0.04\text{ MB}$ |
| **Chimera End-to-End Pipeline** | **$18.5\ \mu\text{s}$ (avg)** | **$\sim 54{,}000\text{ flows/sec}$** | **Total: $< 0.5\text{ MB}$** |

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python**: 3.9, 3.10, or 3.11
- **Operating System**: Windows, Linux, or macOS
- **Pretrained Checkpoints**: Included directly in [`models/`](models/) (`xgboost_model.json` and `kitsune_model.pkl`).

### 2. One-Click Setup

#### Windows
Run [`run.bat`](run.bat):
```cmd
run.bat
```

#### Linux / macOS
Run [`run.sh`](run.sh):
```bash
chmod +x run.sh
./run.sh
```

The script automatically initializes a virtual environment, installs all required packages from `requirements.txt`, and executes a detection run on `data/sample_flows.csv`.

### 3. Manual Installation

```bash
# 1. Clone repository
git clone https://github.com/<your-username>/chimera.git
cd chimera

# 2. Initialize virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Install editable package
pip install -e .
```

---

## 💻 CLI Usage Guide

Chimera provides both a command-line interface and an interactive console:

```text
usage: run.py [-h] [{train_kitsune,train_xgboost,train_all,detect}] [--input INPUT]
```

### 1. Real-Time Threat Detection
Analyze network traffic from PCAP files or flow CSV extracts:
```bash
python run.py detect --input data/sample_flows.csv
```
**Output generated**:
- Creates a timestamped directory in `outputs/<input_name>_YYYYMMDD_HHMMSS/`.
- **`report/Report.md`**: Human-readable executive summary report.
- **`predictions/`**: Partitioned JSONs (`benign_flows.json`, `dos_flows.json`, `anomaly_flows.json`).
- **`logs/technical_debug.log`**: Detailed execution log.

### 2. Interactive Console Mode
Run without arguments to launch the interactive management menu:
```bash
python run.py
```
```text
=== Unified DDoS Detection System ===
1. Train Kitsune (Benign Only)
2. Train XGBoost (Benign + DoS)
3. Train All (Unified)
4. Detect (Single File)
5. Exit
```

### 3. Model Training
Train specific components independently or retrain the full pipeline:
```bash
# Train B-DAP autoencoders on benign traffic only:
python run.py train_kitsune

# Train XGBoost classifier on combined traffic:
python run.py train_xgboost

# Train both models:
python run.py train_all
```

### 4. Running Experimental Verification & Cronbach's Alpha
Reproduce the multi-segment reliability benchmarks from the research paper:
```bash
python experimental_evaluator.py
python experimental_data/calc_alpha.py
```

---

## 🎯 MITRE ATT&CK Mapping

Chimera automatically maps flagged traffic to the **MITRE ATT&CK for Enterprise** framework:

| Technique ID | Attack Vector | Detected Flow Characteristics | Recommended Mitigation |
| :--- | :--- | :--- | :--- |
| **T1498.001** | Direct Volumetric Flood | Saturated packet rates, collapsed window sizes | Rate limiting, upstream scrubbers |
| **T1498.002** | Reflection / Amplification | Extreme byte-to-packet ratios (DNS, NTP, SNMP, SSDP) | Upstream BGP Flowspec drop rules |
| **T1499.001** | OS State Exhaustion | High forward IAT variance, SYN floods | Enable SYN Cookies, TCP proxying |
| **T1499.003** | Application Exhaustion | HTTP GET/POST floods, anomalous payload lengths | WAF rate-limiting, CAPTCHA challenges |

---

## 📚 Published Research & Citation

Chimera's 2-model architecture, empirical validation, and safe-broadcast heuristics are peer-reviewed and published in the **IEEE International Conference on Communication, Information & Computing Technology (CICN)**.

- **DOI**: [10.1109/CICN70047.2026.11594396](https://doi.org/10.1109/CICN70047.2026.11594396)
- **Direct Link**: [https://doi.org/10.1109/CICN70047.2026.11594396](https://doi.org/10.1109/CICN70047.2026.11594396)

If you use Chimera in your academic research or commercial deployment, please cite the paper:

```bibtex
@inproceedings{inamdar2026chimera,
  author    = {Inamdar, Arnav and Maniar, Kaviish and Chaudhari, Punam and Tiwari, Basant},
  title     = {Chimera: Priority-Ordered Hierarchical Fusion Architecture for DoS/DDoS Detection},
  booktitle = {Proceedings of the IEEE International Conference on Communication, Information \& Computing Technology (CICN)},
  year      = {2026},
  doi       = {10.1109/CICN70047.2026.11594396},
  publisher = {IEEE}
}
```

---

## 📁 Directory Layout

```text
Chimera/
├── .github/
│   └── workflows/
│       └── ci.yml                     # Multi-OS automated CI workflow (Ubuntu & Windows)
├── .gitignore                         # Comprehensive Git ignore rules (protects large data)
├── .gitattributes                     # Cross-platform LF/CRLF normalization
├── LICENSE                            # Apache 2.0 Open Source License
├── CONTRIBUTING.md                    # Developer contribution guidelines
├── README.md                          # Repository documentation (this file)
├── pyproject.toml                     # Modern Python packaging configuration
├── setup.py                           # Legacy setup configuration for editable installs
├── requirements.txt                   # Production dependency manifest
├── run.bat                            # Windows one-click runner
├── run.sh                             # Linux/macOS one-click runner
├── config.yaml                        # Core system configuration & hyperparameters
├── run.py                             # Primary execution entry point (train, detect, interactive)
├── experimental_evaluator.py          # Paper benchmark evaluation runner
├── run_experiments.py                 # Multi-run evaluation coordinator
│
├── models/                            # The 2 Core Models & Pretrained Weights (< 0.5 MB)
│   ├── __init__.py
│   ├── xgboost_model.py               # Model 1: Supervised XGBoost classifier wrapper
│   ├── xgboost_model.json             # Model 1: Pretrained XGBoost weights (0.42 MB)
│   ├── kitsune.py                     # Model 2: B-DAP 4-channel AutoEncoder ensemble
│   ├── kitsune_model.pkl              # Model 2: Pretrained B-DAP weights (0.04 MB)
│   ├── kitsune_model.pkl.sha256       # Checksum verification for weights
│   └── hybrid.py                      # Priority-ordered hierarchical decision engine
│
├── src/                               # Ingestion & Preprocessing Modules
│   ├── __init__.py
│   ├── input_handler.py               # PCAP and CSV unified ingestion handler
│   ├── feature_extractor.py           # Scapy-based 33-feature flow extractor
│   ├── data_loader.py                 # Out-of-core streaming CSV loader
│   ├── reporting.py                   # Automated Markdown & JSON audit reporting
│   └── utils.py                       # Logger utilities and device helpers
│
├── data/                              # Flow Datasets & Samples
│   ├── README.md                      # Guide on full dataset setup & feature mapping
│   ├── sample_flows.csv               # 200-flow sample dataset (100 Benign, 100 Attack vectors)
│   ├── raw/                           # Raw input mount (.gitkeep)
│   └── processed/                     # Preprocessed data mount (.gitkeep)
│
├── experimental_data/                 # Published Paper Empirical Validation
│   ├── README.md                      # Experimental data documentation
│   ├── calc_alpha.py                  # Cronbach's alpha consistency calculator
│   ├── calc_alpha_latest.py           # Multi-segment consistency calculator
│   ├── cronbach_alpha_report.md       # Alpha report (α = 0.999)
│   ├── empirical_results_report.md    # Multi-attack accuracy summary
│   ├── empirical_results*.json        # Serialized evaluation runs
│   └── latest/                        # Results across the 5 independent segments
│
├── tests/                             # Unit & Regression Tests
│   ├── __init__.py
│   └── test_feature_extractor.py      # Feature extraction unit tests
│
├── Documents/                         # Technical Documentation & Manuals
│   ├── README.md
│   ├── 1_User_Manual.md               # User operational manual
│   ├── 2_Technical_Documentation.md   # Deep technical specification
│   ├── 3_XGBoost_Model_Documentation.md
│   ├── 4_Kitsune_Model_Documentation.md
│   ├── 5_Hybrid_Engine_Documentation.md
│   ├── Chimera_Architecture.drawio    # Editable Draw.io architecture diagram
│   └── Unified_DoS_DDoS_XGBoost_Kitsune_PRD.txt # Product Requirements Document
│
└── outputs/                           # Empirical Results & Generated Reports
    └── README.md
```

---

## 📄 License

This software is released under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for complete details.

---

<div align="center">
  <b>Developed by the Chimera Research Team</b><br>
  <i>Department of Computer Science and Application<br>
  Dr. Vishwanath Karad MIT World Peace University, Pune, India</i>
</div>
