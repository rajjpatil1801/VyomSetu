import streamlit as st
import pandas as pd
import styles
import charts
import generator
import baseline
import optimizer
import metrics
import missions
import priority
import replan
import exact
import demo
import orbits
import mapview
import time
import os
import json
import datetime

st.set_page_config(page_title="VyomSetu", layout="wide", initial_sidebar_state="expanded")
styles.inject_styles()

nav = st.sidebar.radio("Navigation", ["Dashboard", "Method"], label_visibility="collapsed")

if nav == "Method":
    st.markdown('<div class="app-header">VyomSetu Method</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="max-width: 820px; font-family: 'IBM Plex Sans', sans-serif; font-size: 16px; line-height: 1.6; color: #1C1F22;">
    <h3>Problem</h3>
    <p>The Multi-Satellite Downlink Schedule Problem (MSDSP) requires assigning ground stations to satellite passes such that data downlink is maximized, while respecting visibility windows and physical constraints (no overlapping passes on the same station or satellite).</p>
    
    <h3>Objective</h3>
    <p style="font-family: 'IBM Plex Mono', monospace;">Maximize Σ (effective_priority_i * downlinked_gb_i * x_i)</p>
    
    <h3>Priority model</h3>
    <p>Passes are generated based on a mission class table defining base priorities and deadlines. Aging is applied dynamically based on how long data has waited: <code>effective_priority = base_priority * (1 + alpha * min(wait / deadline, 2.0))</code>.</p>
    
    <h3>Algorithm</h3>
    <p>A two-stage metaheuristic combining Simulated Annealing (SA), a Tabu list, and Dynamic Programming (DP). The SA searches the space of binary assignment masks, while the DP exactly solves the weighted interval scheduling problem for each station given a subset of candidate passes. Tabu memory prevents cycling on recently flipped candidates.</p>
    
    <h3>Validation</h3>
    <p>Schedules are formally verified against an exact constraint programming model (OR-Tools CP-SAT). This computes the true optimality gap, proving the heuristic's near-optimal performance.</p>
    
    <h3>Physical constraints</h3>
    <p>Supports real orbital passes computed from TLEs via Skyfield, ground track rendering, and antenna turnaround time gaps to prevent back-to-back scheduling on the same hardware without slewing time.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Presenter mode toggle
presenter_mode = st.sidebar.checkbox("Presenter mode", value=False)
if presenter_mode:
    st.markdown("""
    <style>
    /* Hide the top right Streamlit elements */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    /* Make sidebar thinner and less prominent */
    [data-testid="stSidebar"] {width: 250px !important; opacity: 0.8;}
    /* Increase base font size slightly */
    html, body, [class*="st-"] {font-size: 18px !important;}
    </style>
    """, unsafe_allow_html=True)

# Sidebar - Demo Presets
st.sidebar.markdown('<div class="app-header">VyomSetu Controls</div>', unsafe_allow_html=True)
preset_names = ["Custom"] + list(demo.PRESETS.keys())
selected_preset = st.sidebar.selectbox("Scenario preset", preset_names)

# Populate session state from preset if changed
if selected_preset != "Custom" and st.session_state.get('last_preset') != selected_preset:
    st.session_state.preset_cfg = demo.PRESETS[selected_preset]
    st.session_state.last_preset = selected_preset
    st.session_state.results = None # force re-run
elif selected_preset == "Custom":
    st.session_state.last_preset = "Custom"

cfg = st.session_state.get('preset_cfg', {}) if selected_preset != "Custom" else {}

# Pass source
pass_source = st.sidebar.radio("Pass source", ["Synthetic", "Orbital (TLE)"], index=0 if cfg.get("source", "Synthetic") == "Synthetic" else 1)

# TLE/Orbit controls
if pass_source == "Orbital (TLE)":
    all_stations_df = pd.read_csv("data/stations.csv")
    default_stns = cfg.get("stations", ["Svalbard", "Fairbanks", "Troll", "Inuvik", "Kiruna"])
    stn_sel = st.sidebar.multiselect("Active stations", all_stations_df['name'].tolist(), default=default_stns)
    n_sat_orb = st.sidebar.slider("Satellites (from TLE file)", 5, 30, cfg.get("n_sat", 20))
    horizon_h = st.sidebar.slider("Horizon (hours)", 2, 24, cfg.get("horizon_h", 6))
    horizon_min = horizon_h * 60
    
    n_sat = n_sat_orb
    n_stn = len(stn_sel)
else:
    n_sat = st.sidebar.slider("Satellites", min_value=5, max_value=120, value=cfg.get("n_sat", 20))
    n_stn = st.sidebar.slider("Ground stations", min_value=2, max_value=20, value=cfg.get("n_stn", 3))
    horizon_min = cfg.get("horizon_min", 360)

sa_iter = st.sidebar.slider("SA iterations", min_value=500, max_value=10000, value=cfg.get("sa_iter", 1000), step=100)
seed = st.sidebar.number_input("Random seed", value=cfg.get("seed", 42), step=1)
turnaround_gap = st.sidebar.slider("Turnaround gap (min)", min_value=0, max_value=10, value=cfg.get("turnaround_gap", 2), step=1)

st.sidebar.markdown('<div style="margin-top: 16px; margin-bottom: -8px; font-weight: 500; font-size: 14px;">Mission classes</div>', unsafe_allow_html=True)
with st.sidebar.expander("EDIT MISSION CLASSES", expanded=False):
    if 'mission_classes_df' not in st.session_state:
        st.session_state.mission_classes_df = pd.DataFrame(missions.DEFAULT_CLASSES)
    
    edited_classes = st.data_editor(
        st.session_state.mission_classes_df,
        disabled=["class", "share_in_generator"],
        hide_index=True,
        column_config={
            "class": "Class",
            "base_priority": st.column_config.NumberColumn("Base Priority", min_value=1, max_value=5, step=1),
            "deadline_min": st.column_config.NumberColumn("Deadline (min)", min_value=30, max_value=360, step=1),
            "share_in_generator": st.column_config.NumberColumn("Share", format="%.2f")
        },
        use_container_width=True
    )
    st.session_state.mission_classes_df = edited_classes

mix_options = ["Mostly routine", "Balanced", "Mostly urgent"]
mix_idx = mix_options.index(cfg.get("class_mix", "Balanced"))
class_mix = st.sidebar.selectbox("Class mix", mix_options, index=mix_idx)
class_shares = missions.get_class_shares(class_mix, st.session_state.mission_classes_df)

alpha = st.sidebar.slider("Aging strength (alpha)", min_value=0.0, max_value=2.0, value=cfg.get("alpha", 0.5), step=0.1)

run_button = st.sidebar.button("Run scheduler")

if 'results' not in st.session_state:
    st.session_state.results = None

@st.cache_data(show_spinner=False)
def generate_orbital_scenario(n_sat_orb, stn_names, horizon_h, seed, class_shares_tuple, alpha):
    stns = pd.read_csv("data/stations.csv")
    stns = stns[stns['name'].isin(stn_names)].copy()
    
    tles, _ = orbits.load_tles(prefer_online=False)
    if n_sat_orb < len(tles):
        import random
        random.seed(seed)
        tles = random.sample(tles, n_sat_orb)
        
    start_utc = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    
    passes_df = orbits.compute_passes(tles, stns, start_utc, horizon_min=horizon_h * 60)
    passes_df = orbits.enrich_orbital_passes(passes_df, pd.DataFrame(missions.DEFAULT_CLASSES), list(class_shares_tuple), seed)
    passes_df = priority.apply_aging(passes_df, alpha)
    
    return passes_df, stns, tles, start_utc

if run_button or st.session_state.results is None:
    # We use a progress container
    with st.status("Building scenario and scheduling...", expanded=True) as status:
        if pass_source == "Synthetic":
            st.write("Generating synthetic passes...")
            df_passes = generator.generate_passes(n_sat, n_stn, seed, st.session_state.mission_classes_df, class_shares)
            df_passes = priority.apply_aging(df_passes, alpha)
            stns = None
            tles = None
            start_utc = None
            stn_list = [f"STN-{i:02d}" for i in range(1, n_stn + 1)]
        else:
            st.write("Computing orbital passes via Skyfield...")
            # We convert class_shares to tuple for st.cache_data hashing
            df_passes, stns, tles, start_utc = generate_orbital_scenario(n_sat_orb, stn_sel, horizon_h, seed, tuple(class_shares), alpha)
            stn_list = stn_sel
            
        st.write("Running FCFS baseline...")
        t0 = time.time()
        df_fcfs = baseline.schedule_fcfs(df_passes, gap=turnaround_gap)
        t_fcfs = time.time() - t0
        
        st.write("Running SA+Tabu optimizer...")
        t0 = time.time()
        df_opt = optimizer.schedule_optimized(df_passes, iterations=sa_iter, gap=turnaround_gap)
        t_opt = time.time() - t0
        
        st.write("Validating schedules against constraints...")
        optimizer.validate_schedule(df_fcfs, df_passes, gap=turnaround_gap)
        optimizer.validate_schedule(df_opt, df_passes, gap=turnaround_gap)
        status.update(label="Scheduling complete!", state="complete", expanded=False)
        
    scenario_str = f"{n_sat} satellites, {n_stn} stations, {len(df_passes)} passes"
    if pass_source == "Orbital (TLE)":
        scenario_str += f", {horizon_h}h horizon"
        
    st.session_state.results = {
        'scenario': scenario_str,
        'df_passes': df_passes,
        'df_fcfs': df_fcfs,
        'df_opt': df_opt,
        'n_stn': n_stn,
        'all_stations': stn_list,
        't_fcfs': t_fcfs,
        't_opt': t_opt,
        'stns_df': stns,
        'tles': tles,
        'start_utc': start_utc
    }
    st.session_state.current_plan = df_opt.copy()
    st.session_state.replan_events = []
    st.session_state.exact_results = {}

res = st.session_state.results
df_passes = res['df_passes']
df_fcfs = res['df_fcfs']
df_opt = res['df_opt']
all_stations = res['all_stations']
current_plan = st.session_state.current_plan
stns_df = res.get('stns_df')
tles = res.get('tles')
start_utc = res.get('start_utc')

# Export sidebar
st.sidebar.markdown('<div style="margin-top: 16px; margin-bottom: 8px; font-weight: 500; font-size: 14px;">Export</div>', unsafe_allow_html=True)
csv_data = current_plan.to_csv(index=False)
st.sidebar.download_button("Schedule (CSV)", csv_data, "schedule.csv", "text/csv")
st.sidebar.download_button("Timetable (HTML)", charts.create_gantt(current_plan, all_stations, gap=turnaround_gap, start_utc=start_utc).to_html(), "timetable.html", "text/html")

# Header
try:
    with open("assets/logo.svg", "r") as f:
        svg_content = f.read()
except:
    svg_content = ""

st.markdown(f'''
    <div class="header-container">
        <div>{svg_content}</div>
        <div class="header-title-container">
            <div class="header-title">VyomSetu</div>
            <div class="header-desc">Autonomous ground station scheduler for multi-satellite downlink.</div>
            <div class="header-scenario">{res["scenario"]} | source: {pass_source}</div>
        </div>
    </div>
''', unsafe_allow_html=True)

if selected_preset != "Custom":
    with st.expander("GUIDED DEMO SCRIPT", expanded=True):
        st.markdown(f"**Scenario:** {selected_preset}")
        for step in demo.DEMO_SCRIPT:
            st.markdown(step)

st.markdown("""
<div style="display: flex; gap: 16px; margin-bottom: 24px; font-size: 13px; border-bottom: 1px solid #D8D3C5; padding-bottom: 8px;">
  <a href="#kpis" style="color: #6B6A63; text-decoration: none;">KPIs</a> | 
  <a href="#timetable" style="color: #6B6A63; text-decoration: none;">Timetable</a> | 
  <a href="#ground-tracks" style="color: #6B6A63; text-decoration: none;">Ground Tracks</a> | 
  <a href="#live-replanning" style="color: #6B6A63; text-decoration: none;">Live Replanning</a> | 
  <a href="#optimality-check" style="color: #6B6A63; text-decoration: none;">Optimality Check</a> | 
  <a href="#search-progress" style="color: #6B6A63; text-decoration: none;">Search Progress</a> | 
  <a href="#benchmark" style="color: #6B6A63; text-decoration: none;">Benchmark</a> | 
  <a href="#data-by-priority" style="color: #6B6A63; text-decoration: none;">Data by Priority</a>
</div>
""", unsafe_allow_html=True)

st.header("", anchor="kpis")
kpis = metrics.calculate_kpis(df_fcfs, current_plan)
col1, col2, col3, col4, col5 = st.columns(5)
with col1: styles.render_kpi("FCFS SCORE", "Baseline model", f"{kpis['fcfs_score']:.1f}")
with col2: styles.render_kpi("OPTIMIZED SCORE", "SA + Tabu", f"{kpis['opt_score']:.1f}")
with col3:
    pct = kpis['improvement_pct']
    sign = "+" if pct >= 0 else ""
    diff = kpis['opt_score'] - kpis['fcfs_score']
    styles.render_kpi("IMPROVEMENT", "vs Baseline", f"{sign}{pct:.1f}%", f"{sign}{diff:.1f} points", is_accent=True)
with col4: styles.render_kpi("DATA DOWNLINKED (GB)", "FCFS \u2192 Optimized", f"{kpis['fcfs_data_gb']:.1f}", f"\u2192 {kpis['opt_data_gb']:.1f}")
with col5: styles.render_kpi("PASSES SCHEDULED", "FCFS \u2192 Optimized", f"{kpis['fcfs_passes']}", f"\u2192 {kpis['opt_passes']}")
if kpis['opt_passes'] < kpis['fcfs_passes']:
    styles.render_caption("Optimized schedules fewer but higher-value passes.")

util_df = metrics.get_station_utilization(df_fcfs, current_plan, all_stations, horizon_min=horizon_min)
f_util = util_df[util_df['Scheduler'] == 'FCFS']['Utilization (%)'].mean()
o_util = util_df[util_df['Scheduler'] == 'Optimized']['Utilization (%)'].mean()
conflicts = metrics.count_conflicts(df_passes)
f_dh = metrics.get_deadline_hits(df_fcfs)
o_dh = metrics.get_deadline_hits(current_plan)

st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: styles.render_kpi("UTILIZATION (AVG)", "FCFS \u2192 Optimized", f"{f_util:.1f}%", f"\u2192 {o_util:.1f}%")
with c2: styles.render_kpi("CONFLICTS RESOLVED", "Detected before scheduling", f"{conflicts}", "\u2192 0 remaining")
with c3: styles.render_kpi("DEADLINE HITS", "FCFS \u2192 Optimized", f"{f_dh:.1f}%", f"\u2192 {o_dh:.1f}%")

st.header("", anchor="timetable")
styles.render_section_label("Timetable")
st.markdown('''
<div class="priority-legend">
    <div class="legend-item"><div class="legend-box" style="background-color: #CFC3A0;"></div>Base priority P1</div>
    <div class="legend-item"><div class="legend-box" style="background-color: #D4A65E;"></div>Base priority P2</div>
    <div class="legend-item"><div class="legend-box" style="background-color: #C07A2E;"></div>Base priority P3</div>
    <div class="legend-item"><div class="legend-box" style="background-color: #A04A1A;"></div>Base priority P4</div>
    <div class="legend-item"><div class="legend-box" style="background-color: #6B2210;"></div>Base priority P5</div>
    <div class="legend-item" style="margin-left: 8px;"><div class="legend-outlined-box"></div>gained vs FCFS</div>
</div>
<div style="font-size: 11px; color: #6B6A63; margin-bottom: 16px;">Hover shows effective priority after aging. Bar label = satellite number.</div>
''', unsafe_allow_html=True)

if turnaround_gap > 0:
    styles.render_caption(f"Hatched areas indicate {turnaround_gap}m hardware turnaround gap required between passes.")

if pass_source == "Orbital (TLE)":
    # Let users zoom in chunks of horizon
    zoom_options = ["Full"] + [f"{h}-{h+2}h" for h in range(0, int(horizon_h), 2)]
else:
    zoom_options = ["Full 6h", "0-2h", "2-4h", "4-6h"]
    
zoom_mode = st.radio("Time range", zoom_options, horizontal=True, label_visibility="collapsed", key="zoom_main")

if zoom_mode.startswith("Full"):
    x_range = [0, horizon_min]
else:
    parts = zoom_mode.replace("h", "").split("-")
    x_range = [int(parts[0]) * 60, int(parts[1]) * 60]

gained_ids = set(current_plan['pass_id']) - set(df_fcfs['pass_id'])

st.markdown(f'''
<div class="chart-header">
    <div class="chart-header-title">FCFS</div>
    <div class="chart-header-stats">score {kpis['fcfs_score']:.1f} &nbsp;|&nbsp; {kpis['fcfs_passes']} passes &nbsp;|&nbsp; {kpis['fcfs_data_gb']:.1f} GB</div>
</div>
''', unsafe_allow_html=True)
fig_fcfs = charts.create_gantt(df_fcfs, all_stations, x_range=x_range, gained_ids=None, gap=turnaround_gap, start_utc=start_utc)
st.plotly_chart(fig_fcfs, use_container_width=True, config={'displayModeBar': False})

st.markdown(f'''
<div class="chart-header">
    <div class="chart-header-title">OPTIMIZED</div>
    <div class="chart-header-stats">score {kpis['opt_score']:.1f} &nbsp;|&nbsp; {kpis['opt_passes']} passes &nbsp;|&nbsp; {kpis['opt_data_gb']:.1f} GB</div>
</div>
''', unsafe_allow_html=True)
fig_opt = charts.create_gantt(current_plan, all_stations, x_range=x_range, gained_ids=gained_ids, gap=turnaround_gap, start_utc=start_utc)
st.plotly_chart(fig_opt, use_container_width=True, config={'displayModeBar': False})

st.header("", anchor="ground-tracks")
styles.render_section_label("Ground Tracks and Stations")
if pass_source == "Orbital (TLE)":
    map_t = st.slider("Map Time (minutes from start)", 0, int(horizon_min), 0, key="map_t")
    
    with st.spinner("Computing ground tracks..."):
        # Use cache for tracks
        @st.cache_data(show_spinner=False)
        def get_tracks(tles_list, s_utc, h_min):
            return orbits.compute_ground_tracks(tles_list, s_utc, h_min)
            
        sat_tracks = get_tracks(tles, start_utc, horizon_min)
        fig_map = mapview.create_ground_map(stns_df, sat_tracks, current_plan, map_t, start_utc)
        st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False})
        styles.render_caption("Vermilion lines indicate active downlinks at the selected time based on the Optimized schedule.")
else:
    st.info("Ground track map is only available when using Orbital (TLE) pass source.")

st.header("", anchor="live-replanning")
styles.render_section_label("Live Replanning")
styles.render_caption("Past passes are committed. Only future passes are re-optimized.")

rc1, rc2, rc3, rc4, rc5 = st.columns([2, 2, 2, 2, 2])
with rc1: current_t = st.slider("Current time", 0, int(horizon_min), 0)
with rc2: target_sat = st.selectbox("Satellite", sorted(df_passes['satellite'].unique()))
with rc3: urgent_size = st.slider("Urgent data (GB)", 5, 40, 20)
with rc4: 
    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
    if st.button("Inject urgent request"):
        new_all_passes, frozen_passes, new_plan, event, old_score, new_score, added, dropped, msg = replan.replan(
            st.session_state.current_plan, df_passes, current_t, target_sat, urgent_size, st.session_state.mission_classes_df, alpha, sa_iter, gap=turnaround_gap
        )
        if new_plan is not None:
            st.session_state.replan_events.insert(0, event)
            st.session_state.replan_msg = msg
            st.session_state.replan_before = st.session_state.current_plan.copy()
            st.session_state.replan_after = new_plan.copy()
            st.session_state.replan_t = current_t
            st.session_state.current_plan = new_plan
        else:
            st.session_state.replan_msg = msg
with rc5:
    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
    if st.button("Reset plan", type="secondary"):
        st.session_state.current_plan = res['df_opt'].copy()
        st.session_state.replan_events = []
        if 'replan_msg' in st.session_state: del st.session_state.replan_msg
        if 'replan_before' in st.session_state: del st.session_state.replan_before
        if 'replan_after' in st.session_state: del st.session_state.replan_after
        st.rerun()

if 'replan_msg' in st.session_state:
    st.markdown(f'<div class="mono-text" style="font-size: 13px; color: #C8421B; margin-top: 8px;">{st.session_state.replan_msg}</div>', unsafe_allow_html=True)
    
if 'replan_before' in st.session_state and 'replan_after' in st.session_state:
    before_plan = st.session_state.replan_before
    after_plan = st.session_state.replan_after
    r_t = st.session_state.replan_t
    
    a_gained_ids = set(after_plan['pass_id']) - set(before_plan['pass_id'])
    dropped_ids = set(before_plan['pass_id']) - set(after_plan['pass_id'])
    dropped_passes = before_plan[before_plan['pass_id'].isin(dropped_ids)].to_dict('records')
    
    st.markdown('<div class="chart-header"><div class="chart-header-title">BEFORE (previous plan)</div></div>', unsafe_allow_html=True)
    fig_before = charts.create_gantt(before_plan, all_stations, x_range=x_range, gained_ids=None, current_t=r_t, dropped_passes=dropped_passes, gap=turnaround_gap, start_utc=start_utc)
    st.plotly_chart(fig_before, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown('<div class="chart-header"><div class="chart-header-title">AFTER (replanned)</div></div>', unsafe_allow_html=True)
    fig_after = charts.create_gantt(after_plan, all_stations, x_range=x_range, gained_ids=a_gained_ids, current_t=r_t, gap=turnaround_gap, start_utc=start_utc)
    st.plotly_chart(fig_after, use_container_width=True, config={'displayModeBar': False})
    
if st.session_state.get('replan_events'):
    with st.expander("EVENT LOG"):
        st.dataframe(pd.DataFrame(st.session_state.replan_events), use_container_width=True, hide_index=True)

st.header("", anchor="optimality-check")
styles.render_section_label("Optimality Check")
oc1, oc2 = st.columns([1, 4])
with oc1: exact_limit = st.number_input("Solver time limit (s)", 5, 120, 20)
with oc2: 
    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
    verify_btn = st.button("Verify against exact optimum", type="secondary")

if len(df_passes) > 200:
    st.markdown('<div style="font-size: 11px; color: #6B6A63;">Exact solving will likely timeout on problems with >200 passes; it will report an upper bound.</div>', unsafe_allow_html=True)

exact_key = f"{res['scenario']}_{alpha}_{hash(str(class_shares))}_{turnaround_gap}"
if verify_btn:
    with st.spinner("Running exact CP-SAT solver..."):
        exact_res = exact.solve_exact(df_passes, exact_limit, gap=turnaround_gap)
        st.session_state.exact_results[exact_key] = exact_res

if exact_key in st.session_state.exact_results:
    e_res = st.session_state.exact_results[exact_key]
    e_obj = e_res['objective']
    e_bound = e_res['best_bound']
    e_stat = e_res['status']
    e_time = e_res['solve_time_s']
    opt_score = current_plan['value'].sum() if len(current_plan) > 0 else 0
    
    if e_stat == 'OPTIMAL':
        denom = e_obj
        label = "GAP TO OPTIMUM"
    elif e_stat == 'FEASIBLE':
        denom = e_bound
        label = "GAP TO UPPER BOUND"
    else:
        denom = e_obj
        label = "GAP"
        
    if opt_score > denom and e_stat in ['OPTIMAL', 'FEASIBLE']:
        gap_pct = 0.0
    else:
        gap_pct = ((denom - opt_score) / denom * 100) if denom > 0 else 0.0
        
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: styles.render_kpi("FCFS SCORE", "Baseline model", f"{kpis['fcfs_score']:.1f}")
    with col2: styles.render_kpi("OPTIMIZED SCORE", "SA + Tabu", f"{opt_score:.1f}")
    with col3: styles.render_kpi("EXACT OPTIMUM", f"Status: {e_stat}", f"{e_obj:.1f}")
    with col4: styles.render_kpi(label, f"from {denom:.1f}", f"{gap_pct:.1f}%", is_accent=True)
    with col5: styles.render_kpi("SOLVER TIME", "Heuristic \u2192 Exact", f"{res['t_opt']:.1f} s", f"\u2192 {e_time:.1f} s")
    
    if res['t_opt'] < e_time:
        speed_factor = e_time / res['t_opt'] if res['t_opt'] > 0 else 0
        speed_txt = f" while running {speed_factor:.0f}x faster than the exact solver."
    else:
        speed_txt = "."
        
    if gap_pct <= 0:
        st.markdown(f'<div class="mono-text" style="font-size: 13px; margin-top: 8px;">Optimized schedule matches the exact optimum{speed_txt}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="mono-text" style="font-size: 13px; margin-top: 8px;">Optimized schedule reaches {100-gap_pct:.1f}% of the exact optimum{speed_txt}</div>', unsafe_allow_html=True)
        
    with st.expander("VIEW EXACT OPTIMUM TIMETABLE"):
        e_plan = e_res['schedule']
        e_gained = set(e_plan['pass_id']) - set(current_plan['pass_id'])
        fig_exact = charts.create_gantt(e_plan, all_stations, gained_ids=e_gained, gap=turnaround_gap, start_utc=start_utc, x_range=[0, horizon_min])
        st.plotly_chart(fig_exact, use_container_width=True, config={'displayModeBar': False})

st.header("", anchor="search-progress")
styles.render_section_label("Search Progress")
if hasattr(current_plan, 'attrs') and 'history' in current_plan.attrs and len(current_plan.attrs['history']) > 0:
    history = current_plan.attrs['history']
    e_score = st.session_state.exact_results[exact_key]['objective'] if exact_key in st.session_state.exact_results else None
    fig_conv = charts.create_convergence_chart(history, kpis['fcfs_score'], e_score)
    st.plotly_chart(fig_conv, use_container_width=True, config={'displayModeBar': False})
    styles.render_caption("The search accepts some worse moves early on, then settles.")

st.header("", anchor="benchmark")
styles.render_section_label("Benchmark")

if st.button("Re-run benchmark (quick)"):
    with st.spinner("Running quick benchmark... (~1 minute)"):
        import benchmark
        sizes = [(10,2), (20,3), (30,4)]
        seeds = [42, 43, 44, 45, 46]
        df_new = benchmark.run_benchmark(sizes, seeds, alpha=0.5, iters=500, exact_limit_s=10)
        df_new.to_csv("results/benchmark.csv", index=False)
        st.success("Benchmark updated.")

if os.path.exists("results/benchmark.csv"):
    df_bench = pd.read_csv("results/benchmark.csv")
    tstamp = os.path.getmtime("results/benchmark.csv")
    tstr = datetime.datetime.fromtimestamp(tstamp).strftime('%Y-%m-%d %H:%M:%S')
    st.markdown(f'<div style="font-family: \'IBM Plex Mono\', monospace; font-size: 11px; color: #6B6A63; margin-bottom: 8px;">Loaded results/benchmark.csv ({tstr})</div>', unsafe_allow_html=True)
    
    # render benchmark contents
    summary_rows = []
    for (n_sat, n_stn), group in df_bench.groupby(['n_sat', 'n_stn']):
        imp_m = group['improvement_pct'].mean()
        imp_s = group['improvement_pct'].std() if len(group) > 1 else 0.0
        gap_m = group['gap_pct'].mean()
        gap_s = group['gap_pct'].std() if len(group) > 1 else 0.0
        t_opt_m = group['t_opt'].mean()
        t_ex_m = group['t_exact'].mean()
        opt_share = (group['exact_status'] == 'OPTIMAL').mean() * 100.0
        
        summary_rows.append({
            'Sat': n_sat, 'Stn': n_stn,
            'Improvement (%)': f"{imp_m:.1f} +/- {imp_s:.1f}",
            'Gap to Opt (%)': f"{gap_m:.1f} +/- {gap_s:.1f}",
            't Heuristic (s)': f"{t_opt_m:.2f}",
            't Exact (s)': f"{t_ex_m:.2f}",
            'Solved to Opt (%)': f"{opt_share:.0f}%"
        })
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    fig_rt = charts.create_runtime_chart(df_bench)
    fig_qual = charts.create_quality_chart(df_bench)
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(fig_rt, use_container_width=True, config={'displayModeBar': False})
    with c2: st.plotly_chart(fig_qual, use_container_width=True, config={'displayModeBar': False})
    styles.render_caption("Each point is the mean of N random scenarios. Error bars show one standard deviation.<br>Exact solver results at larger sizes are bounds when the time limit is reached.")
    
    with st.expander("SENSITIVITY (Run on demand)"):
        if st.button("Run Sensitivity Analysis", key="sens_btn"):
            with st.spinner("Running sensitivity analysis..."):
                import benchmark
                sens_iters = [500, 1000, 2000, 5000, 10000]
                sens_alphas = [0.0, 0.5, 1.0, 1.5, 2.0]
                
                # Run for iterations
                res_iter = []
                for it in sens_iters:
                    df = benchmark.run_benchmark([(n_sat, n_stn)], seeds=[42, 43, 44, 45, 46], alpha=alpha, iters=it, exact_limit_s=10)
                    res_iter.append({'iterations': it, 'gap': df['gap_pct'].mean()})
                df_sens_iter = pd.DataFrame(res_iter)
                
                # Run for alpha
                res_alpha = []
                for a in sens_alphas:
                    df = benchmark.run_benchmark([(n_sat, n_stn)], seeds=[42, 43, 44, 45, 46], alpha=a, iters=sa_iter, exact_limit_s=10)
                    res_alpha.append({'alpha': a, 'improvement': df['improvement_pct'].mean()})
                df_sens_alpha = pd.DataFrame(res_alpha)
                
                st.session_state.sens_results = {'iter': df_sens_iter, 'alpha': df_sens_alpha}
                
        if 'sens_results' in st.session_state:
            import plotly.graph_objects as go
            df_i = st.session_state.sens_results['iter']
            df_a = st.session_state.sens_results['alpha']
            
            sc1, sc2 = st.columns(2)
            with sc1:
                fi = go.Figure()
                fi.add_trace(go.Scatter(x=df_i['iterations'], y=df_i['gap'], mode='lines+markers', line=dict(color='#C8421B', width=2)))
                fi.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=30, b=0), height=200, title=dict(text="GAP VS ITERATIONS", font=dict(family="IBM Plex Sans", size=12, color="#6B6A63")), xaxis=dict(tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63")), yaxis=dict(tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63")))
                st.plotly_chart(fi, use_container_width=True, config={'displayModeBar': False})
            with sc2:
                fa = go.Figure()
                fa.add_trace(go.Scatter(x=df_a['alpha'], y=df_a['improvement'], mode='lines+markers', line=dict(color='#1C1F22', width=2)))
                fa.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=30, b=0), height=200, title=dict(text="IMPROVEMENT VS ALPHA", font=dict(family="IBM Plex Sans", size=12, color="#6B6A63")), xaxis=dict(tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63")), yaxis=dict(tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63")))
                st.plotly_chart(fa, use_container_width=True, config={'displayModeBar': False})

st.header("", anchor="data-by-priority")
styles.render_section_label("Data by Priority")
df_breakdown = metrics.get_priority_breakdown(df_fcfs, current_plan)
fig_breakdown = charts.create_priority_chart(df_breakdown)
st.plotly_chart(fig_breakdown, use_container_width=True, config={'displayModeBar': False})

st.header("", anchor="pass-details")
styles.render_section_label("Pass Details")
with st.expander("VIEW ALL PASSES"):
    df_status = metrics.get_passes_status_table(df_passes, df_fcfs, current_plan)
    stn_filter = st.selectbox("Filter by station", ["All"] + all_stations, index=0)
    if stn_filter != "All":
        df_status = df_status[df_status['station'] == stn_filter]
        
    st.dataframe(
        df_status,
        use_container_width=True,
        hide_index=True,
        column_order=["pass_id", "satellite", "station", "start_min", "end_min", "mission_class", "base_priority", "effective_priority", "arrival_min", "deadline_min", "data_gb", "rate_gb_per_min", "downlinked_gb", "value", "deadline_hit", "Status"],
        column_config={
            "pass_id": "Pass ID",
            "satellite": "Satellite",
            "station": "Station",
            "start_min": st.column_config.NumberColumn("Start", format="%d"),
            "end_min": st.column_config.NumberColumn("End", format="%d"),
            "mission_class": "Class",
            "base_priority": "Base P",
            "effective_priority": st.column_config.NumberColumn("Eff P", format="%.1f"),
            "arrival_min": st.column_config.NumberColumn("Arr", format="%d"),
            "deadline_min": st.column_config.NumberColumn("Deadln", format="%d"),
            "deadline_hit": "Hit",
            "data_gb": st.column_config.NumberColumn("Data (GB)", format="%.2f"),
            "rate_gb_per_min": st.column_config.NumberColumn("Rate", format="%.2f"),
            "downlinked_gb": st.column_config.NumberColumn("D/L (GB)", format="%.2f"),
            "value": st.column_config.NumberColumn("Value", format="%.2f"),
            "Status": "Status"
        }
    )
