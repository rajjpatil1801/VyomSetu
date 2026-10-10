"""
orbits.py - Real orbital pass computation using Skyfield and TLE data.
No Streamlit imports.
"""
import os
import time
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

try:
    from skyfield.api import load as sf_load, EarthSatellite, wgs84
    from skyfield.api import Topos
    HAS_SKYFIELD = True
except ImportError:
    HAS_SKYFIELD = False

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CACHE_FILE = os.path.join(DATA_DIR, 'tle_cache.txt')
CACHE_TS_FILE = os.path.join(DATA_DIR, 'tle_cache_ts.txt')
SAMPLE_FILE = os.path.join(DATA_DIR, 'tle_sample.txt')
STATIONS_FILE = os.path.join(DATA_DIR, 'stations.csv')
CELESTRAK_URL = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=planet&FORMAT=tle'
CACHE_TTL_S = 7200  # 2 hours


def _parse_tle_text(text: str) -> list:
    """Parse raw TLE text into list of (name, line1, line2) tuples."""
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    tles = []
    i = 0
    while i + 2 < len(lines):
        name = lines[i]
        l1 = lines[i + 1]
        l2 = lines[i + 2]
        if l1.startswith('1 ') and l2.startswith('2 '):
            tles.append((name, l1, l2))
            i += 3
        else:
            i += 1
    return tles


def load_tles(prefer_online: bool = True) -> tuple:
    """
    Load TLE data. Returns (tles, source_description).
    tles: list of (name, line1, line2)
    source_description: string like "CelesTrak, fetched 2026-10-09 12:00" or "bundled sample file"
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # Check if cache is fresh
    if os.path.exists(CACHE_FILE) and os.path.exists(CACHE_TS_FILE):
        with open(CACHE_TS_FILE, 'r') as f:
            ts = float(f.read().strip())
        age = time.time() - ts
        if age < CACHE_TTL_S:
            with open(CACHE_FILE, 'r') as f:
                text = f.read()
            tles = _parse_tle_text(text)
            if tles:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                return tles, f"CelesTrak, fetched {dt}"

    # Try online fetch
    if prefer_online:
        try:
            import requests
            r = requests.get(CELESTRAK_URL, timeout=15)
            if r.status_code == 200 and len(r.text.strip()) > 100:
                text = r.text
                tles = _parse_tle_text(text)
                if len(tles) >= 5:
                    with open(CACHE_FILE, 'w') as f:
                        f.write(text)
                    with open(CACHE_TS_FILE, 'w') as f:
                        f.write(str(time.time()))
                    dt = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                    return tles, f"CelesTrak, fetched {dt}"
        except Exception:
            pass

        # Fallback: try active group with filtering
        try:
            import requests
            url2 = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
            r2 = requests.get(url2, timeout=30)
            if r2.status_code == 200:
                all_tles = _parse_tle_text(r2.text)
                keywords = ['FLOCK', 'DOVE', 'SKYSAT', 'PELICAN']
                filtered = [t for t in all_tles if any(k in t[0].upper() for k in keywords)]
                if len(filtered) >= 5:
                    lines_out = []
                    for name, l1, l2 in filtered[:60]:
                        lines_out.extend([name, l1, l2])
                    text = '\n'.join(lines_out)
                    with open(CACHE_FILE, 'w') as f:
                        f.write(text)
                    with open(CACHE_TS_FILE, 'w') as f:
                        f.write(str(time.time()))
                    dt = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                    return filtered[:60], f"CelesTrak (active, filtered), fetched {dt}"
        except Exception:
            pass

    # Stale cache fallback
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            text = f.read()
        tles = _parse_tle_text(text)
        if tles:
            ts = os.path.getmtime(CACHE_FILE)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            return tles, f"CelesTrak (cached), fetched {dt}"

    # Final fallback: bundled sample
    if os.path.exists(SAMPLE_FILE):
        with open(SAMPLE_FILE, 'r') as f:
            text = f.read()
        tles = _parse_tle_text(text)
        if tles:
            return tles, "bundled sample file"

    return [], "no TLE data available"


def load_stations() -> pd.DataFrame:
    """Load ground station catalog."""
    return pd.read_csv(STATIONS_FILE)


def _cache_key(tles, station_names, horizon_min, start_date_str):
    if not isinstance(tles, list): raise ValueError("tles must be a list")
    if not isinstance(station_names, list): raise ValueError("station_names must be a list")
    if not isinstance(horizon_min, int) or horizon_min <= 0: raise ValueError("horizon_min must be positive int")
    if not isinstance(start_date_str, str): raise ValueError("start_date_str must be a string")
    h = hashlib.md5()
    for name, l1, l2 in tles:
        h.update(l1.encode())
    h.update(','.join(sorted(station_names)).encode())
    h.update(str(horizon_min).encode())
    h.update(start_date_str.encode())
    return h.hexdigest()[:12]


def compute_passes(tles: list, stations_df: pd.DataFrame,
                   start_utc: datetime, horizon_min: int = 720,
                   step_s: int = 30) -> pd.DataFrame:
    if not isinstance(tles, list): raise ValueError("tles must be a list")
    if not isinstance(start_utc, datetime): raise ValueError("start_utc must be a datetime")
    if not isinstance(horizon_min, int) or horizon_min <= 0: raise ValueError("horizon_min must be positive int")
    """
    Compute satellite passes over ground stations using Skyfield.
    Returns DataFrame with: satellite, station, start_min, end_min, max_elevation_deg
    """
    if not HAS_SKYFIELD:
        raise RuntimeError("Skyfield is not installed")

    station_names = list(stations_df['name'])
    start_str = start_utc.strftime('%Y%m%d%H')
    cache_key = _cache_key(tles, station_names, horizon_min, start_str)
    cache_path = os.path.join(DATA_DIR, f'pass_cache_{cache_key}.csv')

    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)

    ts = sf_load.timescale()
    t0 = ts.from_datetime(start_utc.replace(tzinfo=timezone.utc) if start_utc.tzinfo is None else start_utc)
    t1 = ts.from_datetime((start_utc.replace(tzinfo=timezone.utc) if start_utc.tzinfo is None else start_utc) + timedelta(minutes=horizon_min))

    passes = []

    for name, l1, l2 in tles:
        try:
            sat = EarthSatellite(l1, l2, name, ts)
        except Exception:
            continue

        for _, stn_row in stations_df.iterrows():
            stn_name = stn_row['name']
            stn_loc = wgs84.latlon(stn_row['lat'], stn_row['lon'], stn_row['alt_m'])
            min_elev = stn_row['min_elevation_deg']

            try:
                t_events, events = sat.find_events(stn_loc, t0, t1, altitude_degrees=min_elev)
            except Exception:
                continue

            if len(t_events) == 0:
                continue

            # Parse events: 0=rise, 1=culminate, 2=set
            i = 0
            while i < len(events):
                # Find a rise event
                if events[i] == 0:
                    rise_t = t_events[i]
                    max_elev = min_elev
                    set_t = None

                    j = i + 1
                    while j < len(events):
                        if events[j] == 1:
                            # Culmination - get max elevation
                            diff = sat - stn_loc
                            topocentric = diff.at(t_events[j])
                            alt_deg, _, _ = topocentric.altaz()
                            max_elev = alt_deg.degrees
                        elif events[j] == 2:
                            set_t = t_events[j]
                            break
                        j += 1

                    if set_t is not None:
                        start_min_val = (rise_t.utc_datetime() - (start_utc.replace(tzinfo=timezone.utc) if start_utc.tzinfo is None else start_utc)).total_seconds() / 60.0
                        end_min_val = (set_t.utc_datetime() - (start_utc.replace(tzinfo=timezone.utc) if start_utc.tzinfo is None else start_utc)).total_seconds() / 60.0

                        # Clip to horizon
                        start_min_val = max(0, start_min_val)
                        end_min_val = min(horizon_min, end_min_val)

                        duration = end_min_val - start_min_val
                        if duration >= 2.0:
                            passes.append({
                                'satellite': name.strip(),
                                'station': stn_name,
                                'start_min': round(start_min_val, 1),
                                'end_min': round(end_min_val, 1),
                                'max_elevation_deg': round(max_elev, 1)
                            })
                    i = j + 1 if set_t is not None else i + 1
                else:
                    i += 1

    df = pd.DataFrame(passes) if passes else pd.DataFrame(
        columns=['satellite', 'station', 'start_min', 'end_min', 'max_elevation_deg'])

    # Cache
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(cache_path, index=False)

    return df


def compute_ground_tracks(tles: list, start_utc: datetime, horizon_min: int,
                          step_s: int = 60, max_sats: int = 25) -> dict:
    if not isinstance(tles, list): raise ValueError("tles must be a list")
    if not isinstance(start_utc, datetime): raise ValueError("start_utc must be a datetime")
    if not isinstance(horizon_min, int) or horizon_min <= 0: raise ValueError("horizon_min must be positive int")
    """
    Compute sub-satellite lat/lon at each timestep.
    Returns dict: {sat_name: [(time_min, lat, lon), ...]}
    """
    if not HAS_SKYFIELD:
        return {}

    cache_key = _cache_key(tles[:max_sats], [], horizon_min, start_utc.strftime('%Y%m%d%H'))
    cache_path = os.path.join(DATA_DIR, f'track_cache_{cache_key}.csv')

    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path)
        tracks = {}
        for name, grp in df.groupby('satellite'):
            tracks[name] = list(zip(grp['time_min'], grp['lat'], grp['lon']))
        return tracks

    ts = sf_load.timescale()
    start_dt = start_utc.replace(tzinfo=timezone.utc) if start_utc.tzinfo is None else start_utc
    n_steps = int(horizon_min * 60 / step_s) + 1
    times = ts.from_datetimes([start_dt + timedelta(seconds=i * step_s) for i in range(n_steps)])
    time_mins = [i * step_s / 60.0 for i in range(n_steps)]

    tracks = {}
    rows = []
    for name, l1, l2 in tles[:max_sats]:
        try:
            sat = EarthSatellite(l1, l2, name.strip(), ts)
            geocentric = sat.at(times)
            subpoint = wgs84.subpoint(geocentric)
            lats = subpoint.latitude.degrees
            lons = subpoint.longitude.degrees
            track = list(zip(time_mins, lats, lons))
            tracks[name.strip()] = track
            for t_m, lat, lon in track:
                rows.append({'satellite': name.strip(), 'time_min': round(t_m, 2),
                             'lat': round(lat, 4), 'lon': round(lon, 4)})
        except Exception:
            continue

    if rows:
        pd.DataFrame(rows).to_csv(cache_path, index=False)

    return tracks


def enrich_orbital_passes(df_passes: pd.DataFrame, missions_df: pd.DataFrame,
                          class_shares: list, seed: int) -> pd.DataFrame:
    """
    Assign mission class, data volume, rate, arrival, deadline to orbital passes.
    Orbits are real; priorities and data volumes are simulated.
    """
    rng = np.random.default_rng(seed)
    n = len(df_passes)
    if n == 0:
        for col in ['pass_id', 'mission_class', 'base_priority', 'data_gb',
                     'rate_gb_per_min', 'downlinked_gb', 'arrival_min', 'deadline_min']:
            df_passes[col] = []
        return df_passes

    df = df_passes.copy()

    # Assign pass_id
    df['pass_id'] = [f"P-{i+1:04d}" for i in range(n)]

    # Assign mission class by share
    classes = list(missions_df['class'])
    shares = [float(s) for s in class_shares]
    total = sum(shares)
    probs = [s / total for s in shares]
    df['mission_class'] = rng.choice(classes, size=n, p=probs)

    # Map base_priority and deadline from missions table
    class_to_pri = dict(zip(missions_df['class'], missions_df['base_priority']))
    class_to_dead = dict(zip(missions_df['class'], missions_df['deadline_min']))
    df['base_priority'] = df['mission_class'].map(class_to_pri).astype(int)
    df['deadline_min'] = df['mission_class'].map(class_to_dead).astype(int)

    # Data and rate - rate scales with max elevation if available
    df['data_gb'] = rng.uniform(3, 30, size=n).round(2)
    if 'max_elevation_deg' in df.columns:
        elev_norm = (df['max_elevation_deg'].clip(10, 90) - 10) / 80.0
        df['rate_gb_per_min'] = (0.8 + elev_norm * 1.7).round(2)
    else:
        df['rate_gb_per_min'] = rng.uniform(0.8, 2.5, size=n).round(2)

    duration = df['end_min'] - df['start_min']
    df['downlinked_gb'] = np.minimum(df['data_gb'], df['rate_gb_per_min'] * duration).round(2)

    # Arrival: random, before start, can be negative
    df['arrival_min'] = (df['start_min'] - rng.uniform(0, 120, size=n)).round(1)

    # Integer start/end for scheduling
    df['start_min'] = df['start_min'].apply(lambda x: int(round(x)))
    df['end_min'] = df['end_min'].apply(lambda x: int(round(x)))

    return df
