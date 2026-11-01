#!/usr/bin/env bash
set -e

echo "=============================================================================="
echo " Chimera Intrusion Detection System (IDS) — Unix/Linux Launcher"
echo " (XGBoost + B-DAP AutoEncoder Ensemble + Priority-Ordered Hybrid Engine)"
echo "=============================================================================="

VENV_DIR="venv"

# Check Python version
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python 3.9+ is not found. Please install Python."
    exit 1
fi

# Create virtual environment if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating Python virtual environment in $VENV_DIR..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    
    echo "[INFO] Installing required packages from requirements.txt..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "[INFO] Environment successfully prepared."
else
    source "$VENV_DIR/bin/activate"
fi

# Run detection on sample data or passed arguments
if [ $# -eq 0 ]; then
    echo "[INFO] Running baseline detection on sample flows (data/sample_flows.csv)..."
    python run.py detect --input data/sample_flows.csv
else
    echo "[INFO] Executing Chimera with arguments: $@"
    python run.py "$@"
fi

echo "[SUCCESS] Execution completed successfully."
