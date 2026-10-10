import pytest
import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generator
import optimizer
import exact
import missions
import priority

def test_exact_validator_pass():
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    shares = missions.get_class_shares("Balanced", missions_df)
    df_passes = generator.generate_passes(10, 2, 42, missions_df, shares)
    df_passes = priority.apply_aging(df_passes, 1.0)
    
    res = exact.solve_exact(df_passes, time_limit_s=5)
    # the function internally calls validate_schedule, so if it doesn't raise, we're good
    assert res['status'] in ['OPTIMAL', 'FEASIBLE']
    
def test_exact_vs_heuristic_small_instances():
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    shares = missions.get_class_shares("Balanced", missions_df)
    
    for seed in [10, 20, 30, 40, 50]:
        df_passes = generator.generate_passes(10, 2, seed, missions_df, shares)
        df_passes = priority.apply_aging(df_passes, 0.5)
        
        df_opt = optimizer.schedule_optimized(df_passes, iterations=500)
        opt_score = df_opt['value'].sum() if len(df_opt) > 0 else 0.0
        
        res = exact.solve_exact(df_passes, time_limit_s=10)
        assert res['status'] == 'OPTIMAL'
        exact_score = res['objective']
        
        # Exact should be >= heuristic (within small rounding error)
        assert exact_score >= opt_score - 1e-3

def test_known_optimum():
    # 3 passes, hand-built
    passes = [
        {'pass_id': 'p1', 'satellite': 'SAT-01', 'station': 'STN-01', 'start_min': 10, 'end_min': 20, 'value': 100},
        {'pass_id': 'p2', 'satellite': 'SAT-02', 'station': 'STN-01', 'start_min': 15, 'end_min': 25, 'value': 200}, # overlaps with p1 on STN-01
        {'pass_id': 'p3', 'satellite': 'SAT-03', 'station': 'STN-01', 'start_min': 22, 'end_min': 30, 'value': 50}  # can go with p1, but p2+p3 = 250 > p1+p3 = 150
    ]
    df_passes = pd.DataFrame(passes)
    res = exact.solve_exact(df_passes, time_limit_s=5)
    
    assert res['status'] == 'OPTIMAL'
    assert res['objective'] == 200.0
    assert set(res['selected_ids']) == {'p2'}
