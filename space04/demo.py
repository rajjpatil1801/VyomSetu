"""
demo.py - Guided demo mode with preset scenarios.
No Streamlit imports.
"""

PRESETS = {
    "Quick start (synthetic, 20 sat, 3 stn, seed 42)": {
        "source": "Synthetic",
        "n_sat": 20,
        "n_stn": 3,
        "seed": 42,
        "class_mix": "Balanced",
        "alpha": 0.5,
        "sa_iter": 1000,
        "turnaround_gap": 2,
        "horizon_min": 360,
    },
    "Wildfire surge (synthetic, 25 sat, 3 stn)": {
        "source": "Synthetic",
        "n_sat": 25,
        "n_stn": 3,
        "seed": 99,
        "class_mix": "Mostly urgent",
        "alpha": 1.0,
        "sa_iter": 1000,
        "turnaround_gap": 2,
        "horizon_min": 360,
    },
    "Polar network (orbital, 20 sat, 5 stn, 12 h)": {
        "source": "Orbital (TLE)",
        "n_sat": 20,
        "stations": ["Svalbard", "Fairbanks", "Troll", "Inuvik", "Kiruna"],
        "horizon_h": 12,
        "seed": 42,
        "class_mix": "Balanced",
        "alpha": 0.5,
        "sa_iter": 1000,
        "turnaround_gap": 2,
        "fixed_demo_time": True,
    },
    "Global network (orbital, 25 sat, 8 stn, 24 h)": {
        "source": "Orbital (TLE)",
        "n_sat": 25,
        "stations": ["Svalbard", "Fairbanks", "Troll", "Punta Arenas",
                      "Hartebeesthoek", "Bengaluru", "Perth", "Kiruna"],
        "horizon_h": 24,
        "seed": 42,
        "class_mix": "Balanced",
        "alpha": 0.5,
        "sa_iter": 1000,
        "turnaround_gap": 2,
        "fixed_demo_time": True,
    },
}

DEMO_SCRIPT = [
    "1. Select a scenario preset from the sidebar and click 'Run scheduler'. Review the TIMETABLE Gantt charts showing FCFS vs Optimized schedules.",
    "2. Read the KPI row: compare FCFS SCORE vs OPTIMIZED SCORE. Note the improvement percentage and the number of passes scheduled.",
    "3. In the LIVE REPLANNING section, set 'Current time' to 120 min, select a satellite, and click 'Inject urgent request'. Compare the BEFORE and AFTER Gantt charts.",
    "4. Scroll to OPTIMALITY CHECK and click 'Verify against exact optimum'. Confirm the gap to the exact solution is small (typically under 2%).",
    "5. Open the BENCHMARK section to review pre-computed runtime and quality charts across different problem sizes.",
    "6. For orbital scenarios, scroll to GROUND TRACKS AND STATIONS. Move the time slider to see satellites move and vermilion downlink lines appear during active passes.",
]
