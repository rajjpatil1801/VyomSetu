import numpy as np
import pandas as pd
from bisect import bisect_right
from collections import deque

def run_dp_station(passes):
    if not passes:
        return []
    
    passes = sorted(passes, key=lambda x: x['end_min'])
    n = len(passes)
    
    ends = [p['end_min'] for p in passes]
    p_idx = []
    for i in range(n):
        # Find the last pass that ends before or at the start time of passes[i]
        # bisect_right returns insertion point. We need <= start_min
        idx = bisect_right(ends, passes[i]['start_min']) - 1
        p_idx.append(idx)
        
    dp = [0.0] * (n + 1)
    choice = [False] * (n + 1)
    
    for i in range(1, n + 1):
        incl = passes[i-1]['value']
        prev_idx = p_idx[i-1] + 1
        incl += dp[prev_idx]
        
        excl = dp[i-1]
        if incl > excl:
            dp[i] = incl
            choice[i] = True
        else:
            dp[i] = excl
            choice[i] = False
            
    selected = []
    curr = n
    while curr > 0:
        if choice[curr]:
            selected.append(passes[curr-1])
            curr = p_idx[curr-1] + 1
        else:
            curr -= 1
    return selected

def evaluate_mask(mask, passes_list, stn_indices):
    selected_all_stations = []
    # passes_list is a list of dicts
    # stn_indices is a dict mapping station name to list of indices in passes_list
    
    for stn, indices in stn_indices.items():
        stn_passes = [passes_list[i] for i in indices if mask[i]]
        if stn_passes:
            selected_all_stations.extend(run_dp_station(stn_passes))
            
    final_passes = []
    if selected_all_stations:
        # Sort by value desc
        selected_all_stations.sort(key=lambda x: x['value'], reverse=True)
        
        sat_usage = {}
        for row in selected_all_stations:
            sat = row['satellite']
            start = row['start_min']
            end = row['end_min']
            
            if sat not in sat_usage:
                sat_usage[sat] = set()
            
            overlap = False
            for m in range(start, end):
                if m in sat_usage[sat]:
                    overlap = True
                    break
                    
            if not overlap:
                for m in range(start, end):
                    sat_usage[sat].add(m)
                final_passes.append(row)
                
    if not final_passes:
        return 0.0, []
        
    return sum(p['value'] for p in final_passes), final_passes

def schedule_optimized(df_passes: pd.DataFrame, iterations: int = 1000, frozen_passes: pd.DataFrame = None, previous_plan: pd.DataFrame = None) -> pd.DataFrame:
    n = len(df_passes)
    if n == 0:
        return df_passes.copy()
        
    passes_list = df_passes.to_dict('records')
    
    forced_ids = set()
    if frozen_passes is not None and len(frozen_passes) > 0:
        forced_ids = set(frozen_passes['pass_id'])
        
        stn_usage = {}
        sat_usage = {}
        for _, row in frozen_passes.iterrows():
            stn = row['station']
            sat = row['satellite']
            start = row['start_min']
            end = row['end_min']
            if stn not in stn_usage: stn_usage[stn] = []
            if sat not in sat_usage: sat_usage[sat] = []
            stn_usage[stn].append((start, end))
            sat_usage[sat].append((start, end))
            
        def is_conflict(row):
            if row['pass_id'] in forced_ids:
                return False
            start = row['start_min']
            end = row['end_min']
            stn = row['station']
            sat = row['satellite']
            if stn in stn_usage:
                for s, e in stn_usage[stn]:
                    if not (end <= s or start >= e): return True
            if sat in sat_usage:
                for s, e in sat_usage[sat]:
                    if not (end <= s or start >= e): return True
            return False
            
        passes_list = [p for p in passes_list if not is_conflict(p)]
        
    stn_indices = {}
    for i, p in enumerate(passes_list):
        stn = p['station']
        if stn not in stn_indices:
            stn_indices[stn] = []
        stn_indices[stn].append(i)
        
    if previous_plan is not None:
        init_ids = set(previous_plan['pass_id'])
        init_mask = np.array([p['pass_id'] in init_ids for p in passes_list])
    else:
        from baseline import schedule_fcfs
        df_fcfs = schedule_fcfs(df_passes)
        fcfs_ids = set(df_fcfs['pass_id'])
        init_mask = np.array([p['pass_id'] in fcfs_ids for p in passes_list])
        
    for i, p in enumerate(passes_list):
        if p['pass_id'] in forced_ids:
            init_mask[i] = True
            
    best_score, best_passes = evaluate_mask(init_mask, passes_list, stn_indices)
    best_mask = init_mask.copy()
    
    all_ones_mask = np.ones(len(passes_list), dtype=bool)
    all_ones_score, all_ones_passes = evaluate_mask(all_ones_mask, passes_list, stn_indices)
    
    if all_ones_score > best_score:
        best_score = all_ones_score
        best_mask = all_ones_mask.copy()
        best_passes = all_ones_passes
    
    curr_score = best_score
    curr_mask = best_mask.copy()
    
    max_val = df_passes['value'].max()
    t0 = 0.3 * max_val
    t_end = 0.01 * t0
    
    if iterations > 1:
        alpha = (t_end / t0) ** (1 / iterations)
    else:
        alpha = 0.0
        
    t = t0
    tabu_list = deque(maxlen=8)
    
    flippable_indices = [i for i, p in enumerate(passes_list) if p['pass_id'] not in forced_ids]
    if not flippable_indices:
        iterations = 0
    
    history = []
    
    for i in range(iterations):
        if i % 10 == 0:
            history.append({'iteration': i, 'best_score': best_score, 'current_score': curr_score, 'temperature': t})
            
        available_indices = [idx for idx in flippable_indices if idx not in tabu_list]
        if not available_indices:
            available_indices = flippable_indices
            
        flip_idx = np.random.choice(available_indices)
        
        new_mask = curr_mask.copy()
        new_mask[flip_idx] = not new_mask[flip_idx]
        
        new_score, new_passes = evaluate_mask(new_mask, passes_list, stn_indices)
        
        delta = new_score - curr_score
        
        if delta > 0:
            curr_score = new_score
            curr_mask = new_mask
            tabu_list.append(flip_idx)
            if curr_score > best_score:
                best_score = curr_score
                best_mask = curr_mask.copy()
                best_passes = new_passes
        else:
            # delta <= 0
            if t > 0:
                prob = np.exp(delta / t)
            else:
                prob = 0
            if np.random.rand() < prob:
                curr_score = new_score
                curr_mask = new_mask
                tabu_list.append(flip_idx)
                
        t *= alpha
        
    if iterations > 0 and iterations % 10 != 0:
        history.append({'iteration': iterations, 'best_score': best_score, 'current_score': curr_score, 'temperature': t})
        
    if not best_passes:
        df_res = pd.DataFrame(columns=df_passes.columns)
    else:
        df_res = pd.DataFrame(best_passes).sort_values('start_min').reset_index(drop=True)
        
    df_res.attrs['history'] = history
    return df_res

def validate_schedule(df_scheduled: pd.DataFrame, df_original: pd.DataFrame):
    """
    Checks constraints:
    1. One sat per station at a time.
    2. One station per sat at a time.
    3. Pass only inside its own window.
    4. Only valid pass_ids used.
    """
    if len(df_scheduled) == 0:
        return True
        
    stn_usage = {}
    sat_usage = {}
    
    orig_dict = df_original.set_index('pass_id').to_dict('index')
    
    for idx, row in df_scheduled.iterrows():
        pid = row['pass_id']
        if pid not in orig_dict:
            raise ValueError(f"Invalid pass_id {pid}")
            
        orig = orig_dict[pid]
        
        start = row['start_min']
        end = row['end_min']
        
        if start < orig['start_min'] or end > orig['end_min']:
            raise ValueError(f"Pass {pid} outside its window: {start}-{end} vs {orig['start_min']}-{orig['end_min']}")
            
        stn = row['station']
        sat = row['satellite']
        
        if stn not in stn_usage:
            stn_usage[stn] = set()
        if sat not in sat_usage:
            sat_usage[sat] = set()
            
        for m in range(start, end):
            if m in stn_usage[stn]:
                raise ValueError(f"Station overlap on {stn} at minute {m}")
            if m in sat_usage[sat]:
                raise ValueError(f"Satellite overlap on {sat} at minute {m}")
                
            stn_usage[stn].add(m)
            sat_usage[sat].add(m)
            
    return True
