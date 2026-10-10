# VyomSetu

VyomSetu is an autonomous ground station scheduler for multi-satellite downlink. It produces a schedule that maximizes priority-weighted data downlinked, presented in a flight-operations style dashboard.

## Setup
1. Ensure you have Python 3.11 installed.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

## Run
To start the dashboard locally:
```bash
streamlit run app.py
```

## Algorithm Summary
The scheduler uses a two-stage optimization strategy inspired by SATLD (Liu et al. 2022). 
First, Simulated Annealing with a Tabu List explores subsets of passes to allow. 
Second, for any given subset, dynamic programming efficiently selects the optimal non-overlapping intervals per ground station. 
A final repair step resolves any conflicting overlaps for a single satellite across different stations, ensuring strict constraints are met.

## Known Limitations
- Data is generated synthetically; real TLE data is not currently supported.
- Scheduling operates on a whole-pass basis (no partial downlink).
- No integration with user login or mission class constraints in Version 1.
