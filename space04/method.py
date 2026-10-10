import streamlit as st
import pandas as pd
import json
import os
import optimizer
import missions

import components
import html_utils

def render_method_page():
    components.render_masthead("Method")

    st.markdown(html_utils.compact("""
    <div style="max-width: 820px; font-family: 'IBM Plex Sans', sans-serif; font-size: 16px; line-height: 1.6; color: #1C1F22; margin-bottom: 24px; font-size: 13px;">
      <a href="#1-problem" style="color: #6B6A63; text-decoration: none;">1. Problem</a> | 
      <a href="#2-inputs-and-what-is-real" style="color: #6B6A63; text-decoration: none;">2. Inputs</a> | 
      <a href="#3-objective-and-constraints" style="color: #6B6A63; text-decoration: none;">3. Constraints</a> | 
      <a href="#4-priority-model" style="color: #6B6A63; text-decoration: none;">4. Priority</a> | 
      <a href="#5-algorithms" style="color: #6B6A63; text-decoration: none;">5. Algorithms</a> | 
      <a href="#6-validation" style="color: #6B6A63; text-decoration: none;">6. Validation</a> | 
      <a href="#7-known-limitations" style="color: #6B6A63; text-decoration: none;">7. Limitations</a> | 
      <a href="#8-what-we-changed-from-the-reference-paper" style="color: #6B6A63; text-decoration: none;">8. Reference</a>
    </div>
    """), unsafe_allow_html=True)
    
    cfg = st.session_state.get('preset_cfg', {})
    try:
        temp_df = pd.read_csv("data/stations.csv")
        mask = int(temp_df['min_elevation_deg'].iloc[0])
    except:
        mask = 10
            
    gap = cfg.get("turnaround_gap", 2)
    alpha_default = cfg.get("alpha", 0.5)
    tabu_len = optimizer.TABU_LENGTH

    st.markdown(html_utils.compact(f"""
    <div style="max-width: 820px; font-family: 'IBM Plex Sans', sans-serif; font-size: 16px; line-height: 1.6; color: #1C1F22;">
    <h3 id="1-problem" style="font-weight: 600;">1. Problem</h3>
    <p>Many satellites share a few ground stations. A satellite can talk to a station only while it passes overhead, usually 5 to 12 minutes. A station serves one satellite at a time, and a satellite uses one station at a time. Data differs in priority and size, so the question is which passes to use so that the most valuable data reaches the ground. The number of combinations grows very quickly with satellites and stations, and ground station scheduling is known to be NP-hard (Liu et al., 2022).</p>
    <hr style="border: 0; border-top: 1px solid #D8D3C5; margin: 24px 0;">
    
    <h3 id="2-inputs-and-what-is-real" style="font-weight: 600;">2. Inputs and what is real</h3>
    <p>Two pass sources are supported.</p>
    <ul>
      <li><strong>Orbital:</strong> pass windows are computed with Skyfield from public TLE data (CelesTrak, or the bundled sample file when offline), with an elevation mask of <code style="font-family: 'IBM Plex Mono', monospace;">{mask}</code> degrees. Ground stations are illustrative sites, not any company's official network.</li>
      <li><strong>Synthetic:</strong> random passes with a fixed seed, used for tests and benchmarks.</li>
    </ul>
    <p>Always simulated, in both sources: mission class, priority, data volume, link rate, data arrival time and deadline. Orbits are real; priorities and data volumes are simulated.</p>
    <hr style="border: 0; border-top: 1px solid #D8D3C5; margin: 24px 0;">
    
    <h3 id="3-objective-and-constraints" style="font-weight: 600;">3. Objective and constraints</h3>
    <p>Maximize the sum over scheduled passes of <code style="font-family: 'IBM Plex Mono', monospace;">effective_priority * downlinked_gb</code> where <code style="font-family: 'IBM Plex Mono', monospace;">downlinked_gb = min(data_gb, rate_gb_per_min * pass_duration_min)</code>.</p>
    <p>Constraints (checked by a validator on every schedule shown):</p>
    <ul>
      <li>one satellite per station at a time</li>
      <li>one station per satellite at a time</li>
      <li>a downlink happens inside its own pass window</li>
      <li>minimum turnaround gap of <code style="font-family: 'IBM Plex Mono', monospace;">{gap}</code> minutes (default) between consecutive passes on a station, and between consecutive passes of a satellite on different stations (antenna repointing)</li>
      <li>a pass is accepted or skipped as a whole (no partial downlink)</li>
    </ul>
    <hr style="border: 0; border-top: 1px solid #D8D3C5; margin: 24px 0;">
    
    <h3 id="4-priority-model" style="font-weight: 600;">4. Priority model</h3>
    <p>Each pass belongs to a mission class with a base priority and a deadline:</p>
    """), unsafe_allow_html=True)
    
    # Render table
    st.dataframe(pd.DataFrame(missions.DEFAULT_CLASSES)[["class", "base_priority", "deadline_min"]], hide_index=True)
    
    st.markdown(html_utils.compact(f"""
    <div style="max-width: 820px; font-family: 'IBM Plex Sans', sans-serif; font-size: 16px; line-height: 1.6; color: #1C1F22;">
    <p>Waiting data gains priority:</p>
    <p style="font-family: 'IBM Plex Mono', monospace;">effective_priority = base_priority * (1 + alpha * min(wait / deadline, 2.0))</p>
    <p>where <code style="font-family: 'IBM Plex Mono', monospace;">wait = max(0, pass_start - data_arrival)</code> and alpha defaults to <code style="font-family: 'IBM Plex Mono', monospace;">{alpha_default}</code>. With alpha = 0 priority is static. Priority itself is an input set by the operator; the scheduler uses it, it does not decide it.</p>
    <hr style="border: 0; border-top: 1px solid #D8D3C5; margin: 24px 0;">
    
    <h3 id="5-algorithms" style="font-weight: 600;">5. Algorithms</h3>
    <p><strong>Baseline, FCFS:</strong> passes sorted by start time; a pass is accepted if its station and its satellite are free (including the turnaround gap), otherwise rejected. It ignores priority and data size.</p>
    <p><strong>Optimized, two stages plus repair</strong> (adapted from Liu et al., 2022):</p>
    <ul>
      <li><strong>Stage 1, Simulated Annealing with a Tabu list</strong> (length <code style="font-family: 'IBM Plex Mono', monospace;">{tabu_len}</code>): the search state is a mask of allowed passes. Worse moves are accepted with probability exp(delta / T) under geometric cooling, the tabu list blocks recently flipped passes.</li>
      <li><strong>Stage 2, Dynamic Programming:</strong> for each station, weighted interval scheduling picks the best non-overlapping subset of the allowed passes. This step is exact for one station.</li>
      <li><strong>Repair:</strong> if one satellite is chosen on two stations at overlapping times, the lower value pass is dropped.</li>
    </ul>
    <p>The overall result is a heuristic and is not guaranteed to be optimal.</p>
    <p><strong>Live replanning:</strong> when an urgent request arrives at time t, passes that start before t are frozen, and only later passes are re-optimized, starting from the previous plan.</p>
    <hr style="border: 0; border-top: 1px solid #D8D3C5; margin: 24px 0;">
    
    <h3 id="6-validation" style="font-weight: 600;">6. Validation</h3>
    <p>Three layers.</p>
    <ul>
      <li><strong>Constraint validator:</strong> every schedule (FCFS, optimized, exact, replanned) is checked against all constraints.</li>
      <li><strong>Exact solver:</strong> OR-Tools CP-SAT solves the same model. The optimality gap is (exact - heuristic) / exact, per instance. When the time limit is reached the solver returns an upper bound instead of a proven optimum, and the page labels it as a bound.</li>
      <li><strong>Tests and benchmark:</strong> unit tests cover the formulas and constraints; the benchmark runs many random scenarios per size and reports mean and standard deviation.</li>
    </ul>
    </div>
    """), unsafe_allow_html=True)
    
    if os.path.exists('results/benchmark_summary.json'):
        try:
            with open('results/benchmark_summary.json', 'r') as f:
                bench_data = json.load(f)
            if bench_data:
                bench_df = pd.DataFrame(bench_data)
                bench_df.columns = ["Satellites", "Stations", "Mean Improvement vs FCFS (%)", "Mean Gap to Optimum (%)", "Solved to Optimality (%)"]
                for col in ["Mean Improvement vs FCFS (%)", "Mean Gap to Optimum (%)", "Solved to Optimality (%)"]:
                    bench_df[col] = bench_df[col].apply(lambda x: f"{x:.1f}")
                
                st.markdown('<p style="font-family: \'IBM Plex Sans\', sans-serif; font-size: 16px; color: #1C1F22;"><strong>Benchmark snapshot:</strong></p>', unsafe_allow_html=True)
                st.dataframe(bench_df, hide_index=True)
                st.markdown('<p style="font-family: \'IBM Plex Sans\', sans-serif; font-size: 13px; color: #6B6A63; margin-top: -12px;">Synthetic scenarios; larger sizes report bounds when the exact solver hits its time limit.</p>', unsafe_allow_html=True)
        except Exception as e:
            pass

    st.markdown(html_utils.compact("""
    <div style="max-width: 820px; font-family: 'IBM Plex Sans', sans-serif; font-size: 16px; line-height: 1.6; color: #1C1F22;">
    <hr style="border: 0; border-top: 1px solid #D8D3C5; margin: 24px 0;">
    
    <h3 id="7-known-limitations" style="font-weight: 600;">7. Known limitations</h3>
    <ul>
      <li>Priorities, data volumes, deadlines and link rates are simulated</li>
      <li>Whole-pass downlink only, no partial downlink</li>
      <li>Antenna repointing is a fixed gap, not a slew model</li>
      <li>No onboard storage, power, weather or link-quality model</li>
      <li>Ground station sites are illustrative</li>
      <li>The optimized schedule is a heuristic; DP is exact per station only</li>
      <li>Results on synthetic data do not predict real-network gains</li>
    </ul>
    <hr style="border: 0; border-top: 1px solid #D8D3C5; margin: 24px 0;">
    
    <h3 id="8-what-we-changed-from-the-reference-paper" style="font-weight: 600;">8. What we changed from the reference paper</h3>
    <p>Reference: Y. Liu, S. Zhang and H. Hu, "A Simulated Annealing Algorithm with Tabu List for the Multi-Satellite Downlink Schedule Problem Considering Waiting Time", Aerospace 2022, 9, 235.</p>
    <p>The paper minimizes task waiting time, treats each task as a duration only, and fixes start times with greedy first-come and shortest-job rules. We keep the two-stage idea (simulated annealing with a tabu list for assignment) and change: the objective to priority-weighted data downlinked, add data volume and link rate, add priority aging, replace the greedy start-time stage with exact dynamic programming per station, add a turnaround gap and live replanning, and validate against an exact CP-SAT model.</p>
    </div>
    """), unsafe_allow_html=True)
