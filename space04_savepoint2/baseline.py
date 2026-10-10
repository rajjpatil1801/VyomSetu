import pandas as pd

def schedule_fcfs(df_passes: pd.DataFrame, gap: int = 0) -> pd.DataFrame:
    """
    Schedules passes using a naive First-Come-First-Served logic.
    Passes are processed in order of start time.
    gap: turnaround time in minutes between consecutive passes on the same station or satellite.
    """
    df = df_passes.sort_values(by='start_min').copy()
    
    accepted = []
    
    # Track end times per station and satellite
    stn_end_times = {}  # station -> list of (start, end)
    sat_end_times = {}  # satellite -> list of (start, end)
    
    def is_free(usage_list, start, end, gap_val):
        if not usage_list:
            return True
        for s, e in usage_list:
            # Two passes conflict if they overlap considering the gap
            if not (end + gap_val <= s or start >= e + gap_val):
                return False
        return True

    for idx, row in df.iterrows():
        sat = row['satellite']
        stn = row['station']
        start = int(row['start_min'])
        end = int(row['end_min'])
        
        stn_list = stn_end_times.get(stn, [])
        sat_list = sat_end_times.get(sat, [])
        
        if is_free(stn_list, start, end, gap) and is_free(sat_list, start, end, gap):
            if stn not in stn_end_times:
                stn_end_times[stn] = []
            if sat not in sat_end_times:
                sat_end_times[sat] = []
            stn_end_times[stn].append((start, end))
            sat_end_times[sat].append((start, end))
            accepted.append(True)
        else:
            accepted.append(False)
            
    df['scheduled'] = accepted
    return df[df['scheduled'] == True].drop(columns=['scheduled']).copy()
