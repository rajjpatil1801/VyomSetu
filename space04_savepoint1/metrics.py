import pandas as pd
import numpy as np

def calculate_kpis(df_fcfs: pd.DataFrame, df_opt: pd.DataFrame):
    fcfs_score = df_fcfs['value'].sum() if len(df_fcfs) > 0 else 0
    opt_score = df_opt['value'].sum() if len(df_opt) > 0 else 0
    
    if fcfs_score > 0:
        improvement = (opt_score - fcfs_score) / fcfs_score * 100
    else:
        improvement = 0.0
        
    fcfs_data = df_fcfs['downlinked_gb'].sum() if len(df_fcfs) > 0 else 0
    opt_data = df_opt['downlinked_gb'].sum() if len(df_opt) > 0 else 0
    
    fcfs_count = len(df_fcfs)
    opt_count = len(df_opt)
    
    return {
        'fcfs_score': fcfs_score,
        'opt_score': opt_score,
        'improvement_pct': improvement,
        'fcfs_data_gb': fcfs_data,
        'opt_data_gb': opt_data,
        'fcfs_passes': fcfs_count,
        'opt_passes': opt_count
    }

def get_priority_breakdown(df_fcfs: pd.DataFrame, df_opt: pd.DataFrame):
    # Data downlinked per priority level
    priorities = [1, 2, 3, 4, 5]
    
    fcfs_group = df_fcfs.groupby('priority')['downlinked_gb'].sum().to_dict() if len(df_fcfs) > 0 else {}
    opt_group = df_opt.groupby('priority')['downlinked_gb'].sum().to_dict() if len(df_opt) > 0 else {}
    
    data = []
    for p in priorities:
        data.append({
            'Priority': f'P{p}',
            'Scheduler': 'FCFS',
            'Data (GB)': fcfs_group.get(p, 0.0)
        })
        data.append({
            'Priority': f'P{p}',
            'Scheduler': 'Optimized',
            'Data (GB)': opt_group.get(p, 0.0)
        })
        
    return pd.DataFrame(data)

def get_passes_status_table(df_all: pd.DataFrame, df_fcfs: pd.DataFrame, df_opt: pd.DataFrame):
    df_res = df_all.copy()
    
    fcfs_ids = set(df_fcfs['pass_id']) if len(df_fcfs) > 0 else set()
    opt_ids = set(df_opt['pass_id']) if len(df_opt) > 0 else set()
    
    def get_status(pid):
        in_f = pid in fcfs_ids
        in_o = pid in opt_ids
        if in_f and in_o: return 'Both'
        if in_f: return 'FCFS only'
        if in_o: return 'Optimized only'
        return 'Neither'
        
    df_res['Status'] = df_res['pass_id'].apply(get_status)
    
    # Calculate deadline hits
    df_res['deadline_hit'] = (df_res['start_min'] < (df_res['arrival_min'] + df_res['deadline_min'])).map({True: 'Yes', False: 'No'})
    
    return df_res

def count_conflicts(df_passes: pd.DataFrame) -> int:
    if len(df_passes) == 0:
        return 0
    df = df_passes.sort_values('start_min')
    conflicts = 0
    
    for stn, group in df.groupby('station'):
        ends = []
        for _, row in group.iterrows():
            for e in ends:
                if row['start_min'] < e:
                    conflicts += 1
            ends.append(row['end_min'])
            
    for sat, group in df.groupby('satellite'):
        ends = []
        for _, row in group.iterrows():
            for e in ends:
                if row['start_min'] < e:
                    conflicts += 1
            ends.append(row['end_min'])
            
    return conflicts

def get_deadline_hits(df_passes: pd.DataFrame) -> float:
    if len(df_passes) == 0:
        return 0.0
    hits = (df_passes['start_min'] < (df_passes['arrival_min'] + df_passes['deadline_min'])).sum()
    return (hits / len(df_passes)) * 100.0

def get_station_utilization(df_fcfs: pd.DataFrame, df_opt: pd.DataFrame, all_stations: list):
    data = []
    for stn in all_stations:
        f_busy = df_fcfs[df_fcfs['station'] == stn]['end_min'].sum() - df_fcfs[df_fcfs['station'] == stn]['start_min'].sum() if len(df_fcfs) > 0 else 0
        o_busy = df_opt[df_opt['station'] == stn]['end_min'].sum() - df_opt[df_opt['station'] == stn]['start_min'].sum() if len(df_opt) > 0 else 0
        
        data.append({'Station': stn, 'Scheduler': 'FCFS', 'Utilization (%)': (f_busy / 360.0) * 100})
        data.append({'Station': stn, 'Scheduler': 'Optimized', 'Utilization (%)': (o_busy / 360.0) * 100})
        
    return pd.DataFrame(data)
