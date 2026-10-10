import pytest
import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generator
import baseline
import optimizer
import metrics
import priority
import missions
import replan

def test_alpha_zero_identical():
    n_sat = 15
    n_stn = 4
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    shares = missions.get_class_shares("Balanced", missions_df)
    
    seeds = [10, 42, 100, 999, 2024]
    for seed in seeds:
        df_passes = generator.generate_passes(n_sat, n_stn, seed, missions_df, shares)
        df_passes_v1 = df_passes.copy()
        df_passes_v1['value'] = df_passes_v1['base_priority'] * df_passes_v1['downlinked_gb']
        
        df_passes_v2 = priority.apply_aging(df_passes, alpha=0.0)
        
        # Test values are exactly equal
        assert (df_passes_v1['value'] == df_passes_v2['value']).all()

def test_effective_priority_formula():
    df = pd.DataFrame([
        {'base_priority': 3, 'start_min': 100, 'arrival_min': 50, 'deadline_min': 100, 'downlinked_gb': 10.0},
        {'base_priority': 5, 'start_min': 200, 'arrival_min': 250, 'deadline_min': 90, 'downlinked_gb': 5.0},
        {'base_priority': 2, 'start_min': 300, 'arrival_min': -100, 'deadline_min': 100, 'downlinked_gb': 20.0}
    ])
    
    df_out = priority.apply_aging(df, alpha=0.5)
    
    # Ex 1: wait = 50, deadline = 100. wait/deadline = 0.5. factor = 1 + 0.5 * 0.5 = 1.25. eff = 3 * 1.25 = 3.75
    assert abs(df_out.at[0, 'effective_priority'] - 3.75) < 1e-5
    
    # Ex 2: wait = max(0, 200 - 250) = 0. factor = 1 + 0 = 1.0. eff = 5.0
    assert abs(df_out.at[1, 'effective_priority'] - 5.0) < 1e-5
    
    # Ex 3: wait = 400. deadline = 100. wait/deadline = 4.0 -> min(4.0, 2.0) = 2.0. factor = 1 + 0.5 * 2 = 2.0. eff = 2 * 2 = 4.0
    assert abs(df_out.at[2, 'effective_priority'] - 4.0) < 1e-5

def test_aging_monotonic():
    df = pd.DataFrame([
        {'base_priority': 3, 'start_min': 100, 'arrival_min': 100, 'deadline_min': 100, 'downlinked_gb': 10.0}
    ])
    
    prev_eff = -1
    for arrival in range(100, -100, -10):
        df.at[0, 'arrival_min'] = arrival
        df_out = priority.apply_aging(df, alpha=1.0)
        eff = df_out.at[0, 'effective_priority']
        assert eff >= prev_eff
        prev_eff = eff

def test_replan_logic():
    n_sat = 20
    n_stn = 4
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    shares = missions.get_class_shares("Balanced", missions_df)
    
    df_passes = generator.generate_passes(n_sat, n_stn, 42, missions_df, shares)
    df_passes = priority.apply_aging(df_passes, alpha=0.5)
    
    current_plan = optimizer.schedule_optimized(df_passes, iterations=200)
    
    t = 120
    target_sat = "SAT-05" # ensure it has passes > t
    urgent_size = 20.0
    
    new_all_passes, frozen, new_plan, event, old_score, new_score, added, dropped, msg = replan.replan(
        current_plan, df_passes, t, target_sat, urgent_size, missions_df, 0.5, iterations=200
    )
    
    # If SAT-05 has passes, test constraints
    if new_plan is not None:
        # Frozen unchanged
        old_frozen = current_plan[current_plan['start_min'] < t]
        new_frozen = new_plan[new_plan['start_min'] < t]
        assert len(old_frozen) == len(new_frozen)
        assert set(old_frozen['pass_id']) == set(new_frozen['pass_id'])
        
        # Passes validator
        assert optimizer.validate_schedule(new_plan, new_all_passes) is True
        
        # Score >= old plan on new data
        old_plan_new_data = current_plan['pass_id'].map(new_all_passes.set_index('pass_id')['value']).sum()
        assert new_score >= old_plan_new_data - 1e-3  # allowing tiny float diff

def test_replan_no_future():
    # If a satellite has no passes after t, replan returns None
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    df = pd.DataFrame([
        {'pass_id': 'P1', 'satellite': 'SAT-01', 'station': 'STN-01', 'start_min': 10, 'end_min': 20, 
         'mission_class': 'Routine', 'base_priority': 1, 'deadline_min': 100, 'arrival_min': 0, 
         'data_gb': 10, 'rate_gb_per_min': 1, 'downlinked_gb': 10}
    ])
    df = priority.apply_aging(df, 0.5)
    
    current_plan = df.copy()
    
    _, _, new_plan, _, _, _, _, _, _ = replan.replan(
        current_plan, df, 100, 'SAT-01', 20.0, missions_df, 0.5, 100
    )
    
    assert new_plan is None

def test_optimized_ge_fcfs_v2():
    n_sat = 15
    n_stn = 4
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    shares = missions.get_class_shares("Balanced", missions_df)
    
    seeds = [10, 42, 100, 999, 2024]
    for seed in seeds:
        df_passes = generator.generate_passes(n_sat, n_stn, seed, missions_df, shares)
        df_passes = priority.apply_aging(df_passes, alpha=0.5)
        
        df_fcfs = baseline.schedule_fcfs(df_passes)
        df_opt = optimizer.schedule_optimized(df_passes, iterations=100)
        
        fcfs_score = df_fcfs['value'].sum() if len(df_fcfs) > 0 else 0
        opt_score = df_opt['value'].sum() if len(df_opt) > 0 else 0
        
        assert opt_score >= fcfs_score - 1e-3
