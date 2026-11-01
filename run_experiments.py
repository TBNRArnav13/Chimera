import os
import subprocess

def main():
    base_dir = r"e:\Coding\College\PBL Sem 4\Chimera"
    os.chdir(base_dir)
    
    latest_dir = os.path.join(base_dir, "experimental_data", "latest")
    os.makedirs(latest_dir, exist_ok=True)
    
    # 5 runs, stepping by 100,000 rows each time so flows are completely different
    tags = [("run1", 0), ("run2", 100000), ("run3", 200000), ("run4", 300000), ("run5", 400000)]
    for tag, skip_rows in tags:
        print(f"Starting evaluation for {tag} with offset {skip_rows}...")
        subprocess.run(["python", "experimental_evaluator.py", "--tag", tag, "--skip-rows", str(skip_rows)], check=True)
        
        src = os.path.join(base_dir, "experimental_data", f"empirical_results_{tag}.json")
        dst = os.path.join(latest_dir, f"empirical_results_{tag}.json")
        if os.path.exists(dst):
            os.remove(dst)
        os.rename(src, dst)
        print(f"Moved {tag} results to latest folder.")

    # Now calculate alpha
    print("\nCalculating Cronbach's alpha...")
    subprocess.run(["python", r"experimental_data\calc_alpha_latest.py"], check=True)
    print("All tasks completed successfully!")

if __name__ == "__main__":
    main()
