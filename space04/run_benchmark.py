import os
import json
from benchmark import run_benchmark

def main():
    sizes = [(10,2), (20,3), (30,4), (50,6), (80,8), (120,10)]
    seeds = [10]
    
    print("Running benchmark...")
    df = run_benchmark(sizes, seeds, alpha=0.5, iters=1000, exact_limit_s=20)
    
    os.makedirs("results", exist_ok=True)
    df.to_csv("results/benchmark.csv", index=False)
    print("Wrote results/benchmark.csv")
    
    summary = {}
    for size, group in df.groupby(['n_sat', 'n_stn']):
        summary[str(size)] = {
            'mean_gap': group['gap_pct'].mean(),
            'mean_t_exact': group['t_exact'].mean()
        }
    with open("results/benchmark_summary.json", "w") as f:
        json.dump(summary, f)
        
    print("Done.")

if __name__ == "__main__":
    main()
