# Experimental Evaluation & Cronbach's Alpha Validation

This directory contains the experimental verification scripts, data partitions, and empirical metrics reported in the published IEEE research paper:

> **Chimera: Priority-Ordered Hierarchical Fusion Architecture for DoS/DDoS Detection**  
> *IEEE International Conference on Communication, Information & Computing Technology (CICN 2026)*  
> DOI: [10.1109/CICN70047.2026.11594396](https://doi.org/10.1109/CICN70047.2026.11594396)

---

## Files

- **`calc_alpha.py` / `calc_alpha_latest.py`**:
  Calculates Cronbach's alpha internal consistency metric ($\alpha$) across dynamic, non-overlapping traffic slices:
  - **XGBoost**: $\alpha = 1.000$
  - **B-DAP (Kitsune)**: $\alpha = 0.811$
  - **Chimera Hybrid Engine**: $\alpha = 0.999$ ($\alpha \ge 0.90 \implies$ Excellent reliability)
- **`cronbach_alpha_report.md`**: Markdown summary report of empirical consistency.
- **`latest/empirical_results_run*.json`**: Serialized evaluation runs across the 5 independent segments.
- **`empirical_results_report.md`**: Summary of classification metrics (Accuracy, FNR, FPR) across attack vectors.
