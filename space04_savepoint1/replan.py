import pandas as pd
from optimizer import schedule_optimized
from priority import apply_aging
import time

def replan(current_plan: pd.DataFrame, all_passes: pd.DataFrame, t: int, target_sat: str, urgent_size: float, missions_df: pd.DataFrame, alpha: float, iterations: int):
    start_time = time.time()
    df_passes = all_passes.copy()
    
    target_idx = df_passes[(df_passes['satellite'] == target_sat) & (df_passes['start_min'] >= t)].index
    if len(target_idx) == 0:
        return None, None, None, None, 0.0, 0.0, 0, 0, "No upcoming passes for this satellite after t. Request cannot be served in this horizon."
        
    target_idx = target_idx[:2]
    
    disaster_class = missions_df[missions_df['class'] == 'Disaster response'].iloc[0]
    
    for idx in target_idx:
        df_passes.at[idx, 'mission_class'] = 'Disaster response'
        df_passes.at[idx, 'base_priority'] = disaster_class['base_priority']
        df_passes.at[idx, 'deadline_min'] = disaster_class['deadline_min']
        df_passes.at[idx, 'arrival_min'] = t
        old_data = df_passes.at[idx, 'data_gb']
        new_data = max(old_data, urgent_size)
        df_passes.at[idx, 'data_gb'] = new_data
        
        duration = df_passes.at[idx, 'end_min'] - df_passes.at[idx, 'start_min']
        rate = df_passes.at[idx, 'rate_gb_per_min']
        df_passes.at[idx, 'downlinked_gb'] = min(new_data, rate * duration)
        
    df_passes = apply_aging(df_passes, alpha)
    
    frozen_passes = current_plan[current_plan['start_min'] < t].copy()
    
    old_score = current_plan['pass_id'].map(df_passes.set_index('pass_id')['value']).sum()
    
    new_plan = schedule_optimized(df_passes, iterations=iterations, frozen_passes=frozen_passes, previous_plan=current_plan)
    new_score = new_plan['value'].sum()
    
    delta = new_score - old_score
    
    old_ids = set(current_plan[current_plan['start_min'] >= t]['pass_id'])
    new_ids = set(new_plan[new_plan['start_min'] >= t]['pass_id'])
    added = len(new_ids - old_ids)
    dropped = len(old_ids - new_ids)
    
    elapsed = time.time() - start_time
    msg = f"Injected {urgent_size} GB on {target_sat} at t={t}. +{added} passes added, {dropped} dropped, score {old_score:.1f} -> {new_score:.1f}. Replan time {elapsed:.1f} s."
    
    event = {
        'Time': f"t={t}",
        'Satellite': target_sat,
        'GB': urgent_size,
        'Added': added,
        'Dropped': dropped,
        'Score Delta': delta
    }
    
    return df_passes, frozen_passes, new_plan, event, old_score, new_score, added, dropped, msg
