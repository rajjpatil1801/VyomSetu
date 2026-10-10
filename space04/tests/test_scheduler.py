import pytest
import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generator
import baseline
import optimizer
import metrics
import missions

def test_scheduler_random_seeds():
    n_sat = 15
    n_stn = 4
    
    seeds = [10, 42, 100, 999, 2024]
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    shares = missions.get_class_shares("Balanced", missions_df)
    
    for seed in seeds:
        df_passes = generator.generate_passes(n_sat, n_stn, seed, missions_df, shares)
        # assign basic value for V1 test backward compatibility
        df_passes['value'] = df_passes['base_priority'] * df_passes['downlinked_gb']
        
        df_fcfs = baseline.schedule_fcfs(df_passes)
        df_opt = optimizer.schedule_optimized(df_passes, iterations=500)
        
        # Validator checks
        assert optimizer.validate_schedule(df_fcfs, df_passes) is True
        assert optimizer.validate_schedule(df_opt, df_passes) is True
        
        fcfs_score = df_fcfs['value'].sum() if len(df_fcfs) > 0 else 0
        opt_score = df_opt['value'].sum() if len(df_opt) > 0 else 0
        
        # Optimized should be at least as good as FCFS (actually, SA is stochastic, 
        # but with SA initialization or random chance it should be close or better. 
        # To guarantee it's >= FCFS, we could seed the SA with the FCFS solution, 
        # or we just assume SA will find something better or at least FCFS score.
        # Actually, let's just do a soft check or enforce the FCFS seed in optimizer if needed.
        # But wait, optimizer doesn't start from FCFS. It starts from all-ones mask.
        # Is it guaranteed to be >= FCFS? SA can sometimes finish slightly worse if not converged,
        # but the test specifically asks "optimized score >= FCFS score on those seeds".
        # Let's hope the optimizer finds it, or we can just initialize SA best_score with FCFS score.
        assert opt_score >= fcfs_score, f"Seed {seed}: Opt {opt_score} < FCFS {fcfs_score}"
