import pandas as pd
import time
from generator import generate_passes
from priority import apply_aging
from baseline import schedule_fcfs
from optimizer import schedule_optimized
from exact import solve_exact
import missions

def run_benchmark(sizes, seeds, alpha=0.5, iters=1000, exact_limit_s=20):
    results = []
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    shares = missions.get_class_shares("Balanced", missions_df)
    
    for (n_sat, n_stn) in sizes:
        for seed in seeds:
            df_passes = generate_passes(n_sat, n_stn, seed, missions_df, shares)
            df_passes = apply_aging(df_passes, alpha)
            n_passes = len(df_passes)
            
            t0 = time.time()
            df_fcfs = schedule_fcfs(df_passes)
            t_fcfs = time.time() - t0
            fcfs_score = df_fcfs['value'].sum() if len(df_fcfs) > 0 else 0.0
            
            t0 = time.time()
            df_opt = schedule_optimized(df_passes, iterations=iters)
            t_opt = time.time() - t0
            opt_score = df_opt['value'].sum() if len(df_opt) > 0 else 0.0
            
            t0 = time.time()
            exact_res = solve_exact(df_passes, time_limit_s=exact_limit_s)
            t_exact = time.time() - t0
            
            exact_score = exact_res['objective']
            exact_status = exact_res['status']
            
            if exact_status in ['OPTIMAL', 'FEASIBLE']:
                if opt_score > exact_score:
                    gap_pct = 0.0
                else:
                    denom = exact_res['best_bound'] if exact_status == 'FEASIBLE' else exact_score
                    gap_pct = ((denom - opt_score) / denom * 100.0) if denom > 0 else 0.0
            else:
                gap_pct = None
                exact_score = None
                
            improvement_pct = ((opt_score - fcfs_score) / fcfs_score * 100.0) if fcfs_score > 0 else 0.0
            
            results.append({
                'n_sat': n_sat, 'n_stn': n_stn, 'n_passes': n_passes, 'seed': seed,
                'fcfs_score': fcfs_score, 'opt_score': opt_score, 'exact_score': exact_score,
                'exact_status': exact_status, 'gap_pct': gap_pct, 'improvement_pct': improvement_pct,
                't_fcfs': t_fcfs, 't_opt': t_opt, 't_exact': t_exact
            })
    return pd.DataFrame(results)
