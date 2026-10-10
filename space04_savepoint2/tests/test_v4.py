import pytest
import sys
import os
import pandas as pd
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import optimizer
import baseline
import exact
import orbits
import demo
import missions

def test_turnaround_gap_dp():
    # Two passes that don't overlap, but are too close for the turnaround gap
    passes = [
        {'pass_id': 'p1', 'satellite': 'SAT-1', 'station': 'STN-1', 'start_min': 10, 'end_min': 20, 'value': 100},
        {'pass_id': 'p2', 'satellite': 'SAT-2', 'station': 'STN-1', 'start_min': 21, 'end_min': 30, 'value': 200}
    ]
    # Without gap, both can be selected
    sel_0 = optimizer.run_dp_station(passes, gap=0)
    assert len(sel_0) == 2
    
    # With gap=2, they conflict. p2 has higher value, should be selected
    sel_2 = optimizer.run_dp_station(passes, gap=2)
    assert len(sel_2) == 1
    assert sel_2[0]['pass_id'] == 'p2'

def test_turnaround_gap_validator():
    df_passes = pd.DataFrame([
        {'pass_id': 'p1', 'satellite': 'SAT-1', 'station': 'STN-1', 'start_min': 10, 'end_min': 20},
        {'pass_id': 'p2', 'satellite': 'SAT-2', 'station': 'STN-1', 'start_min': 21, 'end_min': 30}
    ])
    df_sched = df_passes.copy()
    
    assert optimizer.validate_schedule(df_sched, df_passes, gap=0) is True
    
    with pytest.raises(ValueError):
        optimizer.validate_schedule(df_sched, df_passes, gap=2)

def test_turnaround_gap_fcfs():
    df_passes = pd.DataFrame([
        {'pass_id': 'p1', 'satellite': 'SAT-1', 'station': 'STN-1', 'start_min': 10, 'end_min': 20},
        {'pass_id': 'p2', 'satellite': 'SAT-2', 'station': 'STN-1', 'start_min': 21, 'end_min': 30}
    ])
    
    df_0 = baseline.schedule_fcfs(df_passes, gap=0)
    assert len(df_0) == 2
    
    df_2 = baseline.schedule_fcfs(df_passes, gap=2)
    assert len(df_2) == 1
    assert 'p1' in df_2['pass_id'].values

def test_turnaround_gap_exact():
    df_passes = pd.DataFrame([
        {'pass_id': 'p1', 'satellite': 'SAT-1', 'station': 'STN-1', 'start_min': 10, 'end_min': 20, 'value': 100},
        {'pass_id': 'p2', 'satellite': 'SAT-2', 'station': 'STN-1', 'start_min': 21, 'end_min': 30, 'value': 200}
    ])
    
    res_0 = exact.solve_exact(df_passes, gap=0)
    assert len(res_0['selected_ids']) == 2
    assert res_0['objective'] == 300
    
    res_2 = exact.solve_exact(df_passes, gap=2)
    assert len(res_2['selected_ids']) == 1
    assert res_2['objective'] == 200

def test_orbital_generation():
    tles, _ = orbits.load_tles(prefer_online=False)
    assert len(tles) > 0
    
    stns = pd.DataFrame([
        {'name': 'Svalbard', 'lat': 78.2, 'lon': 15.4, 'alt_m': 450, 'min_elevation_deg': 5}
    ])
    
    start_utc = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    passes_df = orbits.compute_passes(tles[:3], stns, start_utc, horizon_min=120)
    
    assert 'satellite' in passes_df.columns

def test_orbital_enrichment():
    df = pd.DataFrame([
        {'satellite': 'SAT-1', 'station': 'Svalbard', 'start_min': 10, 'end_min': 20}
    ])
    missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    shares = missions.get_class_shares("Balanced", missions_df)
    
    enriched = orbits.enrich_orbital_passes(df, missions_df=missions_df, class_shares=shares, seed=42)
    assert 'data_gb' in enriched.columns
    assert 'value' not in enriched.columns # added by priority.py later

def test_demo_presets():
    for name, cfg in demo.PRESETS.items():
        assert 'source' in cfg
        assert 'n_sat' in cfg

def test_ground_tracks():
    tles, _ = orbits.load_tles(prefer_online=False)
    start_utc = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    tracks = orbits.compute_ground_tracks(tles[:2], start_utc, horizon_min=60)
    
    assert len(tracks) == 2
