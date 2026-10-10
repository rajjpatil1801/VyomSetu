import pandas as pd
import numpy as np

def apply_aging(df_passes: pd.DataFrame, alpha: float) -> pd.DataFrame:
    if len(df_passes) == 0:
        return df_passes
    df = df_passes.copy()
    wait = np.maximum(0, df['start_min'] - df['arrival_min'])
    factor = 1.0 + alpha * np.minimum(wait / df['deadline_min'], 2.0)
    df['effective_priority'] = df['base_priority'] * factor
    df['value'] = df['effective_priority'] * df['downlinked_gb']
    return df
