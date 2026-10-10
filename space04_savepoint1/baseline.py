import pandas as pd

def schedule_fcfs(df_passes: pd.DataFrame) -> pd.DataFrame:
    """
    Schedules passes using a naive First-Come-First-Served logic.
    Passes are processed in order of start time.
    """
    df = df_passes.sort_values(by='start_min').copy()
    
    stn_free_time = {}
    sat_free_time = {}
    
    accepted = []
    
    # Simple check arrays (minute by minute)
    stn_usage = {}
    sat_usage = {}
    
    def is_free(usage_dict, key, start, end):
        if key not in usage_dict:
            return True
        for m in range(start, end):
            if m in usage_dict[key]:
                return False
        return True
        
    def mark_used(usage_dict, key, start, end):
        if key not in usage_dict:
            usage_dict[key] = set()
        for m in range(start, end):
            usage_dict[key].add(m)

    for idx, row in df.iterrows():
        sat = row['satellite']
        stn = row['station']
        start = row['start_min']
        end = row['end_min']
        
        if is_free(stn_usage, stn, start, end) and is_free(sat_usage, sat, start, end):
            mark_used(stn_usage, stn, start, end)
            mark_used(sat_usage, sat, start, end)
            accepted.append(True)
        else:
            accepted.append(False)
            
    df['scheduled'] = accepted
    return df[df['scheduled'] == True].drop(columns=['scheduled']).copy()
