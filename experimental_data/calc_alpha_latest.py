import json
import numpy as np
import os

def cronbach_alpha(item_scores):
    item_scores = np.asarray(item_scores)
    n_items = item_scores.shape[1]
    
    item_vars = item_scores.var(axis=0, ddof=1)
    total_scores = item_scores.sum(axis=1)
    total_var = total_scores.var(ddof=1)
    
    if total_var == 0:
        return np.nan
        
    alpha = (n_items / (n_items - 1)) * (1 - item_vars.sum() / total_var)
    return alpha

def get_file_accuracy(data, model_name):
    accuracies = []
    file_breakdown = data['file_breakdown']
    files = sorted(file_breakdown.keys())
    for f in files:
        metrics = file_breakdown[f]
        tp = metrics.get(f'{model_name}_tp', 0)
        tn = metrics.get(f'{model_name}_tn', 0)
        fp = metrics.get(f'{model_name}_fp', 0)
        fn = metrics.get(f'{model_name}_fn', 0)
        total = tp + tn + fp + fn
        if total > 0:
            acc = (tp + tn) / total
        else:
            acc = 0.0
        accuracies.append(acc)
    return accuracies

def main():
    base_dir = r"e:\Coding\College\PBL Sem 4\Chimera\experimental_data\latest"
    
    runs_files = [
        "empirical_results_run1.json",
        "empirical_results_run2.json",
        "empirical_results_run3.json",
        "empirical_results_run4.json",
        "empirical_results_run5.json"
    ]
    
    runs_data = []
    for f in runs_files:
        path = os.path.join(base_dir, f)
        with open(path, 'r') as file:
            runs_data.append(json.load(file))
            
    models = ["xgb", "kitsune", "hybrid"]
    
    report_lines = []
    report_lines.append("# Cronbach's Alpha Reliability Report (Latest with TFTP)")
    report_lines.append("This report calculates the internal consistency (Cronbach's alpha) of the evaluation metrics (Accuracy) across the three separate runs for each model, including all datasets.")
    report_lines.append("")
    report_lines.append("## Results")
    
    results = {}
    for model in models:
        item_scores = []
        for run_idx in range(len(runs_data)):
            run_acc = get_file_accuracy(runs_data[run_idx], model)
            item_scores.append(run_acc)
            
        item_scores = np.array(item_scores).T
        alpha = cronbach_alpha(item_scores)
        results[model] = alpha
        
        report_lines.append(f"- **{model.upper()} Accuracy Cronbach's Alpha:** {alpha:.4f}")
        
    report_lines.append("")
    report_lines.append("## Interpretation")
    report_lines.append("- **α ≥ 0.9:** Excellent reliability.")
    report_lines.append("- **0.8 ≤ α < 0.9:** Good reliability.")
    report_lines.append("- **0.7 ≤ α < 0.8:** Acceptable reliability.")
    report_lines.append("- **α < 0.7:** Questionable/Poor reliability.")
    
    report_lines.append("")
    report_lines.append("## Raw Accuracy Data by Run")
    
    for model in models:
        report_lines.append(f"### {model.upper()}")
        report_lines.append("| File | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |")
        report_lines.append("|---|---|---|---|---|---|")
        
        files = sorted(runs_data[0]['file_breakdown'].keys())
        for i, f in enumerate(files):
            r1 = get_file_accuracy(runs_data[0], model)[i]
            r2 = get_file_accuracy(runs_data[1], model)[i]
            r3 = get_file_accuracy(runs_data[2], model)[i]
            r4 = get_file_accuracy(runs_data[3], model)[i]
            r5 = get_file_accuracy(runs_data[4], model)[i]
            report_lines.append(f"| {f} | {r1:.4f} | {r2:.4f} | {r3:.4f} | {r4:.4f} | {r5:.4f} |")
        report_lines.append("")
        
    report_path = os.path.join(base_dir, "cronbach_alpha_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
        
    print(f"Report successfully saved to {report_path}")

if __name__ == '__main__':
    main()
