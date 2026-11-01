# Contributing to Chimera IDS

Thank you for your interest in contributing to the **Chimera Intrusion Detection System**! This repository hosts the official 2-model (XGBoost + B-DAP Kitsune Ensemble + Hybrid Decision Engine) codebase as described in our IEEE conference publication.

---

## 1. Development Setup

1. **Fork the Repository**:
   Click the "Fork" button on the GitHub repository page.

2. **Clone your Fork**:
   ```bash
   git clone https://github.com/<your-username>/chimera.git
   cd chimera
   ```

3. **Initialize Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux / macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

4. **Verify Pipeline Execution**:
   ```bash
   python run.py detect --input data/sample_flows.csv
   ```

---

## 2. Contribution Guidelines

- **Architectural Integrity**: Maintain the priority-ordered hierarchical structure (Supervised XGBoost $\to$ B-DAP Unsupervised Ensemble $\to$ Safe-Broadcast Heuristics).
- **Code Standards**: Adhere to PEP 8 style conventions.
- **Pull Requests**: Provide clear descriptions of bug fixes or enhancements alongside benchmark tests.
