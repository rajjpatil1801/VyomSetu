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
import time
import os
import json

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
    
    <h3>Known limitations</h3>
    <p>The current version relies on synthetic pass generation rather than real TLE/Skyfield ephemerides. It assumes whole-pass downlink (no partial scheduling), ignores antenna slew time between passes, and does not model weather disruptions.</p>
    
    <h3>Reference</h3>
    <p>Liu, Zhang and Hu, "A Simulated Annealing Algorithm with Tabu List for the Multi-Satellite Downlink Schedule Problem Considering Waiting Time", Aerospace 2022, 9, 235. We modified the objective to integrate data volume directly, replaced the allocation step with an exact DP stage, and added rigorous CP-SAT validation.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Sidebar
st.sidebar.markdown('<div class="app-header">VyomSetu Controls</div>', unsafe_allow_html=True)
st.sidebar.markdown('<hr style="margin-top: 5px; margin-bottom: 15px; border: 0; border-top: 1px solid #D8D3C5;">', unsafe_allow_html=True)

n_sat = st.sidebar.slider("Satellites", min_value=5, max_value=120, value=20)
n_stn = st.sidebar.slider("Ground stations", min_value=2, max_value=20, value=3)
sa_iter = st.sidebar.slider("SA iterations", min_value=500, max_value=10000, value=1000, step=100)
seed = st.sidebar.number_input("Random seed", value=42, step=1)

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

class_mix = st.sidebar.selectbox("Class mix", ["Mostly routine", "Balanced", "Mostly urgent"], index=1)
class_shares = missions.get_class_shares(class_mix, st.session_state.mission_classes_df)

alpha = st.sidebar.slider("Aging strength (alpha)", min_value=0.0, max_value=2.0, value=0.5, step=0.1)
st.sidebar.markdown('<div style="font-size: 11px; color: #6B6A63; margin-top: -12px; margin-bottom: 16px; line-height: 1.3;">0 = priority never changes.<br>Higher = waiting data climbs faster.</div>', unsafe_allow_html=True)

run_button = st.sidebar.button("Run scheduler")

if 'results' not in st.session_state:
    st.session_state.results = None

if run_button or st.session_state.results is None:
    df_passes = generator.generate_passes(n_sat, n_stn, seed, st.session_state.mission_classes_df, class_shares)
    df_passes = priority.apply_aging(df_passes, alpha)
    
    t0 = time.time()
    df_fcfs = baseline.schedule_fcfs(df_passes)
    t_fcfs = time.time() - t0
    
    t0 = time.time()
    df_opt = optimizer.schedule_optimized(df_passes, iterations=sa_iter)
    t_opt = time.time() - t0
    
    optimizer.validate_schedule(df_fcfs, df_passes)
    optimizer.validate_schedule(df_opt, df_passes)
    
    st.session_state.results = {
        'scenario': f"{n_sat} satellites, {n_stn} stations, {len(df_passes)} passes, seed {seed}",
        'df_passes': df_passes,
        'df_fcfs': df_fcfs,
        'df_opt': df_opt,
        'n_stn': n_stn,
        'all_stations': [f"STN-{i:02d}" for i in range(1, n_stn + 1)],
        't_fcfs': t_fcfs,
        't_opt': t_opt
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

# Export sidebar
st.sidebar.markdown('<div style="margin-top: 16px; margin-bottom: 8px; font-weight: 500; font-size: 14px;">Export</div>', unsafe_allow_html=True)
csv_data = current_plan.to_csv(index=False)
st.sidebar.download_button("Schedule (CSV)", csv_data, "schedule.csv", "text/csv")
st.sidebar.download_button("Timetable (HTML)", charts.create_gantt(current_plan, all_stations).to_html(), "timetable.html", "text/html")
md_summary = f"""# VyomSetu Summary
Scenario: {res['scenario']}
Score: {current_plan['value'].sum():.1f}
Passes Scheduled: {len(current_plan)}

Algorithm: Simulated Annealing + Tabu List + DP.
Limitations: Synthetic data, whole-pass downlink.
"""
st.sidebar.download_button("Summary (Markdown)", md_summary, "summary.md", "text/markdown")

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
            <div class="header-scenario">{res["scenario"]}</div>
        </div>
    </div>
''', unsafe_allow_html=True)

st.markdown("""
<div style="display: flex; gap: 16px; margin-bottom: 24px; font-size: 13px; border-bottom: 1px solid #D8D3C5; padding-bottom: 8px;">
  <a href="#kpis" style="color: #6B6A63; text-decoration: none;">KPIs</a> | 
  <a href="#timetable" style="color: #6B6A63; text-decoration: none;">Timetable</a> | 
  <a href="#live-replanning" style="color: #6B6A63; text-decoration: none;">Live Replanning</a> | 
  <a href="#optimality-check" style="color: #6B6A63; text-decoration: none;">Optimality Check</a> | 
  <a href="#search-progress" style="color: #6B6A63; text-decoration: none;">Search Progress</a> | 
  <a href="#benchmark" style="color: #6B6A63; text-decoration: none;">Benchmark</a> | 
  <a href="#data-by-priority" style="color: #6B6A63; text-decoration: none;">Data by Priority</a> | 
  <a href="#pass-details" style="color: #6B6A63; text-decoration: none;">Pass Details</a>
</div>
""", unsafe_allow_html=True)

st.header("", anchor="kpis")
# KPIs Row 1
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

# KPIs Row 2
util_df = metrics.get_station_utilization(df_fcfs, current_plan, all_stations)
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

zoom_mode = st.radio("Time range", ["Full 6h", "0-2h", "2-4h", "4-6h"], horizontal=True, label_visibility="collapsed", key="zoom_main")
x_range = [0, 360]
if zoom_mode == "0-2h": x_range = [0, 120]
elif zoom_mode == "2-4h": x_range = [120, 240]
elif zoom_mode == "4-6h": x_range = [240, 360]

gained_ids = set(current_plan['pass_id']) - set(df_fcfs['pass_id'])

st.markdown(f'''
<div class="chart-header">
    <div class="chart-header-title">FCFS</div>
    <div class="chart-header-stats">score {kpis['fcfs_score']:.1f} &nbsp;|&nbsp; {kpis['fcfs_passes']} passes &nbsp;|&nbsp; {kpis['fcfs_data_gb']:.1f} GB</div>
</div>
''', unsafe_allow_html=True)
fig_fcfs = charts.create_gantt(df_fcfs, all_stations, x_range=x_range, gained_ids=None)
st.plotly_chart(fig_fcfs, use_container_width=True, config={'displayModeBar': False})

st.markdown(f'''
<div class="chart-header">
    <div class="chart-header-title">OPTIMIZED</div>
    <div class="chart-header-stats">score {kpis['opt_score']:.1f} &nbsp;|&nbsp; {kpis['opt_passes']} passes &nbsp;|&nbsp; {kpis['opt_data_gb']:.1f} GB</div>
</div>
''', unsafe_allow_html=True)
fig_opt = charts.create_gantt(current_plan, all_stations, x_range=x_range, gained_ids=gained_ids)
st.plotly_chart(fig_opt, use_container_width=True, config={'displayModeBar': False})

st.header("", anchor="live-replanning")
styles.render_section_label("Live Replanning")
styles.render_caption("Past passes are committed. Only future passes are re-optimized.")

rc1, rc2, rc3, rc4, rc5 = st.columns([2, 2, 2, 2, 2])
with rc1: current_t = st.slider("Current time", 0, 360, 0)
with rc2: target_sat = st.selectbox("Satellite", sorted(df_passes['satellite'].unique()))
with rc3: urgent_size = st.slider("Urgent data (GB)", 5, 40, 20)
with rc4: 
    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
    if st.button("Inject urgent request"):
        new_all_passes, frozen_passes, new_plan, event, old_score, new_score, added, dropped, msg = replan.replan(
            st.session_state.current_plan, df_passes, current_t, target_sat, urgent_size, st.session_state.mission_classes_df, alpha, sa_iter
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
    fig_before = charts.create_gantt(before_plan, all_stations, x_range=x_range, gained_ids=None, current_t=r_t, dropped_passes=dropped_passes)
    st.plotly_chart(fig_before, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown('<div class="chart-header"><div class="chart-header-title">AFTER (replanned)</div></div>', unsafe_allow_html=True)
    fig_after = charts.create_gantt(after_plan, all_stations, x_range=x_range, gained_ids=a_gained_ids, current_t=r_t)
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

if n_sat > 40:
    st.markdown('<div style="font-size: 11px; color: #6B6A63;">Exact solving can be slow above 40 satellites; it will stop at the time limit and report a bound.</div>', unsafe_allow_html=True)

exact_key = f"{res['scenario']}_{alpha}_{hash(str(class_shares))}"
if verify_btn:
    exact_res = exact.solve_exact(df_passes, exact_limit)
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
        gap = 0.0
    else:
        gap = ((denom - opt_score) / denom * 100) if denom > 0 else 0.0
        
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: styles.render_kpi("FCFS SCORE", "Baseline model", f"{kpis['fcfs_score']:.1f}")
    with col2: styles.render_kpi("OPTIMIZED SCORE", "SA + Tabu", f"{opt_score:.1f}")
    with col3: styles.render_kpi("EXACT OPTIMUM", f"Status: {e_stat}", f"{e_obj:.1f}")
    with col4: styles.render_kpi(label, f"from {denom:.1f}", f"{gap:.1f}%", is_accent=True)
    with col5: styles.render_kpi("SOLVER TIME", "Heuristic \u2192 Exact", f"{res['t_opt']:.1f} s", f"\u2192 {e_time:.1f} s")
    
    if res['t_opt'] < e_time:
        speed_factor = e_time / res['t_opt'] if res['t_opt'] > 0 else 0
        speed_txt = f" while running {speed_factor:.0f}x faster than the exact solver."
    else:
        speed_txt = "."
        
    if gap <= 0:
        st.markdown(f'<div class="mono-text" style="font-size: 13px; margin-top: 8px;">Optimized schedule matches the exact optimum{speed_txt}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="mono-text" style="font-size: 13px; margin-top: 8px;">Optimized schedule reaches {100-gap:.1f}% of the exact optimum{speed_txt}</div>', unsafe_allow_html=True)
        
    with st.expander("VIEW EXACT OPTIMUM TIMETABLE"):
        e_plan = e_res['schedule']
        e_gained = set(e_plan['pass_id']) - set(current_plan['pass_id'])
        fig_exact = charts.create_gantt(e_plan, all_stations, gained_ids=e_gained)
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
    from datetime import datetime
    tstr = datetime.fromtimestamp(tstamp).strftime('%Y-%m-%d %H:%M:%S')
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
