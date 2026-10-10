# VyomSetu

VyomSetu is an autonomous ground station scheduler for multi-satellite downlink. It produces a schedule that maximizes priority-weighted data downlinked, presented in a flight-operations style dashboard.

Version 4 includes real orbital pass generation via Skyfield/SGP4 from TLEs, exact ground track rendering, live horizon replanning, hardware turnaround gaps, and a rigorous CP-SAT exact validation model.

## Setup
1. Ensure you have Python 3.11+ installed.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

## Run
To start the dashboard locally:
```bash
streamlit run app.py
```

## Docker
To build and run with Docker:
```bash
docker build -t vyomsetu .
docker run -p 8501:8501 vyomsetu
```

## Algorithm Summary
The scheduler uses a two-stage optimization strategy inspired by SATLD (Liu et al. 2022). 
First, Simulated Annealing with a Tabu List explores subsets of passes to allow. 
Second, for any given subset, dynamic programming efficiently selects the optimal non-overlapping intervals per ground station, respecting turnaround gaps.
A final repair step resolves any conflicting overlaps for a single satellite across different stations, ensuring strict constraints are met.

## Validation
The built-in `exact.py` module uses Google OR-Tools CP-SAT to mathematically prove the optimality gap of the heuristic solver, typically showing the SA+DP solver reaches within 0-2% of the exact global optimum in a fraction of the time.

## Tests
Run the test suite using pytest:
```bash
python -m pytest tests/
```
