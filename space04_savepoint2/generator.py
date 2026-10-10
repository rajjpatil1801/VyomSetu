import numpy as np
import pandas as pd

def generate_passes(n_sat: int, n_stn: int, seed: int, missions_df: pd.DataFrame, class_shares: list) -> pd.DataFrame:
    """
    Generates synthetic satellite passes.
    """
    np.random.seed(seed)
    
    passes = []
    pass_id_counter = 1
    classes = missions_df.to_dict('records')
    
    for sat in range(1, n_sat + 1):
        num_passes = np.random.randint(3, 6)
        for _ in range(num_passes):
            station = np.random.randint(1, n_stn + 1)
            duration = np.random.randint(5, 13)
            start_min = np.random.randint(0, 360 - duration + 1)
            end_min = start_min + duration
            
            cls_idx = np.random.choice(len(classes), p=class_shares)
            mission = classes[cls_idx]
            
            arrival_min = np.random.randint(-120, start_min + 1)
            
            data_gb = np.random.uniform(3, 30)
            rate_gb_per_min = np.random.uniform(0.8, 2.5)
            
            downlinked_gb = min(data_gb, rate_gb_per_min * duration)
            
            passes.append({
                'pass_id': f"P{pass_id_counter:04d}",
                'satellite': f"SAT-{sat:02d}",
                'station': f"STN-{station:02d}",
                'start_min': start_min,
                'end_min': end_min,
                'mission_class': mission['class'],
                'base_priority': mission['base_priority'],
                'deadline_min': mission['deadline_min'],
                'arrival_min': arrival_min,
                'data_gb': data_gb,
                'rate_gb_per_min': rate_gb_per_min,
                'downlinked_gb': downlinked_gb
            })
            pass_id_counter += 1
            
    df = pd.DataFrame(passes)
    df = df.sort_values(by='start_min').reset_index(drop=True)
    return df
