import pandas as pd
import time
from ortools.sat.python import cp_model
from optimizer import validate_schedule

def solve_exact(df_passes: pd.DataFrame, time_limit_s: int = 20) -> dict:
    if len(df_passes) == 0:
        return {
            'selected_ids': [], 'objective': 0.0, 'best_bound': 0.0,
            'status': 'OPTIMAL', 'solve_time_s': 0.0, 'schedule': df_passes.copy()
        }
        
    model = cp_model.CpModel()
    passes = df_passes.to_dict('records')
    n = len(passes)
    
    x = {}
    stn_intervals = {}
    sat_intervals = {}
    
    for i, p in enumerate(passes):
        x[i] = model.NewBoolVar(f'x_{i}')
        start, end = int(p['start_min']), int(p['end_min'])
        duration = end - start
        interval = model.NewOptionalIntervalVar(start, duration, end, x[i], f'interval_{i}')
        
        stn = p['station']
        sat = p['satellite']
        
        if stn not in stn_intervals: stn_intervals[stn] = []
        if sat not in sat_intervals: sat_intervals[sat] = []
        
        stn_intervals[stn].append(interval)
        sat_intervals[sat].append(interval)
        
    for stn, ivs in stn_intervals.items():
        model.AddNoOverlap(ivs)
        
    for sat, ivs in sat_intervals.items():
        model.AddNoOverlap(ivs)
        
    obj_vars = []
    obj_coeffs = []
    for i, p in enumerate(passes):
        coeff = int(round(p['value'] * 1000))
        obj_vars.append(x[i])
        obj_coeffs.append(coeff)
        
    model.Maximize(cp_model.LinearExpr.WeightedSum(obj_vars, obj_coeffs))
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 42
    solver.parameters.log_search_progress = False
    
    start_t = time.time()
    status_val = solver.Solve(model)
    solve_time = time.time() - start_t
    
    status_str = solver.StatusName(status_val)
    
    if status_str in ['OPTIMAL', 'FEASIBLE']:
        selected = [passes[i]['pass_id'] for i in range(n) if solver.BooleanValue(x[i])]
        df_res = df_passes[df_passes['pass_id'].isin(selected)].copy()
        obj = df_res['value'].sum() if len(df_res) > 0 else 0.0
        bound = solver.BestObjectiveBound() / 1000.0
    else:
        selected = []
        obj = 0.0
        bound = 0.0
        df_res = pd.DataFrame()
    if len(df_res) > 0:
        validate_schedule(df_res, df_passes)
        
    return {
        'selected_ids': selected,
        'objective': obj,
        'best_bound': bound,
        'status': status_str,
        'solve_time_s': solve_time,
        'schedule': df_res
    }
