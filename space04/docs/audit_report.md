# VyomSetu Audit Report

## 1. Root Cause of the Original Crash
**Symptom:** `TypeError: 'NoneType' object is not subscriptable` at `orbits.py:248` via `app.py:361`.
**Root Cause:** The `Ground Tracks` section conditionally executed if the `pass_source` UI control was set to `Orbital (TLE)`, but it read the actual `tles` and `start_utc` data from the cached `st.session_state.results` (`res`). If the user changed the UI dropdown from `Synthetic` to `Orbital (TLE)` but hadn't yet run the scheduler, `res` still contained the Synthetic run data (where `tles=None` and `start_utc=None`). The ground tracks function was then called with `None` values, leading to a crash.
**Fix:** 
1. `app.py` was updated to store the source string inside the generated `results` state dictionary as `res['source']`. 
2. The UI sections (like Ground Tracks) now selectively render based on `res['source']` (the actual data source) rather than `pass_source` (the UI dropdown state).
3. We wrapped the Ground Tracks section in a strict `if not tles or not start_utc:` check that renders a muted fallback message instead of attempting computation.

## 2. Full Audit Findings & Fixes

| File | Symptom | Cause | Fix |
| :--- | :--- | :--- | :--- |
| `app.py` | UI mismatch and crashes (including Ground Tracks crash). | Section rendering was tied to the transient UI `selectbox` rather than the committed backend scenario data. | Added `source` to `st.session_state.results` and guarded sections using `res_source = res.get('source', 'Synthetic')`. |
| `app.py` | "Ground Tracks" tab generated when data wasn't available. | Section rendering loops didn't check for missing orbital data before injecting tabs. | Guarded the entire Ground Tracks chunk (including heading and map) inside `if res_source == "Orbital (TLE)"` and added data presence checks. |
| `orbits.py` | Missing type checks before expensive computation. | Passing `None` or invalid data directly caused cryptic exceptions deep in `hashlib` or `skyfield` layers. | Injected explicit `isinstance()` checks and `ValueError` raises at the top of `compute_ground_tracks`, `compute_passes`, and `_cache_key`. |
| `app.py` | Unhandled exceptions in arbitrary rendering logic crashing the entire page. | Minor data or key errors could halt rendering entirely, showing a raw traceback. | Created a global `@contextmanager` named `section_wrapper(section_name)` that catches exceptions, prints a clean muted fallback string, and dumps the traceback into a collapsed details expander. Injected this wrapper securely around all 9 major UI sections. |
| `app.py` | Potential crash on missing data in `get_tracks`. | Inline `get_tracks` lacked validation. | Added strong type guards directly into the cached wrapper inside `app.py`. |

## 3. Combinations Tested

We used Streamlit's headless `AppTest` API to simulate matrix interactions:
- **Pass:** `Dashboard` + `Synthetic` + `Default 1 (Synthetic, 20x3)`
- **Pass:** `Dashboard` + `Orbital (TLE)` + `Default 3 (Orbital, 10x4)`
- **Pass:** `Presenter` + `Synthetic` + `Default 1`
- **Pass:** `Method` + `Synthetic` + `Custom`
- **Pass:** `Dashboard` + `Synthetic` + `Custom` (Run button pressed)
- **Pass:** `Dashboard` + `Orbital (TLE)` + `Custom` (Run button pressed)
- **Pass:** `Dashboard` + `Synthetic` + `Stress 1 (Synthetic, 60x6)`
- **Pass:** `Dashboard` + `Orbital (TLE)` + `Stress 2 (Orbital, 30x5)`

**Assertions Passed:**
- No raw exceptions or `st.exception`.
- No raw HTML leakage.
- `wrapper_triggered` array remained empty across all matrix runs, proving the root fixes were sufficient and the safety net was never invoked.

## 4. Final Test Suite Output
The comprehensive test suite (including Exact, Scheduler, Header components, V2/V4 logic, HTML compacting, and the new headless AppTest Smoke matrix) executed successfully.
- **Passed:** 31 tests
- **Failed:** 0
- **Skipped:** 0
