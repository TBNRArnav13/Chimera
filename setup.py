from setuptools import setup, find_packages

setup(
    name="chimera-ids",
    version="1.0.0",
    description="Priority-Ordered Hierarchical Fusion Architecture for DoS/DDoS Detection (IEEE CICN 2026)",
    author="Arnav Inamdar, Kaviish Maniar, Punam Chaudhari, Basant Tiwari",
    packages=find_packages(),
    py_modules=["run", "experimental_evaluator", "run_experiments"],
    install_requires=[
        "pandas>=2.0.3",
        "numpy>=1.25.2",
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
        "xgboost>=2.0.0",
        "torch>=2.0.1",
        "scapy>=2.5.0",
        "psutil>=5.9.0",
        "pyyaml>=6.0.1"
    ],
    python_requires=">=3.9",
)
