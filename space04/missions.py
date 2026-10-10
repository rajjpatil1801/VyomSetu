import pandas as pd

DEFAULT_CLASSES = [
    {"class": "Disaster response", "base_priority": 5, "deadline_min": 90, "share_in_generator": 0.08},
    {"class": "Defense and security", "base_priority": 4, "deadline_min": 180, "share_in_generator": 0.12},
    {"class": "Agriculture and climate", "base_priority": 3, "deadline_min": 240, "share_in_generator": 0.20},
    {"class": "Commercial imaging", "base_priority": 2, "deadline_min": 300, "share_in_generator": 0.25},
    {"class": "Routine mapping", "base_priority": 1, "deadline_min": 360, "share_in_generator": 0.35},
]

def get_class_shares(mix_name: str, base_df: pd.DataFrame):
    if mix_name == "Mostly routine":
        return [0.02, 0.05, 0.15, 0.28, 0.50]
    elif mix_name == "Mostly urgent":
        return [0.35, 0.25, 0.20, 0.15, 0.05]
    else: # Balanced
        return base_df['share_in_generator'].tolist()
