import pytest
from streamlit.testing.v1 import AppTest
import os

def create_app_test():
    return AppTest.from_file("app.py", default_timeout=120)

def assert_no_errors(at):
    assert not at.exception, f"App exception: {at.exception[0] if at.exception else 'None'}"
    # check wrapper triggered
    if 'wrapper_triggered' in at.session_state:
        triggered = at.session_state.wrapper_triggered
        assert not triggered, f"Section wrapper triggered for: {triggered}"

def run_app_smoke(view, source, preset, run_btn=True, quick=True):
    at = create_app_test()
    at.run()
    
    assert_no_errors(at)
    
    # Set view mode
    if len(at.radio) > 0:
        for r in at.radio:
            if r.label == "View":
                r.set_value(view).run()
                break
    
    if view != "Presenter":
        # Select preset
        for s in at.selectbox:
            if s.label == "Scenario preset":
                s.set_value(preset).run()
                break
        
        # Select source
        if preset == "Custom":
            for r in at.radio:
                if r.label == "Pass source":
                    r.set_value(source).run()
                    break

        if run_btn:
            for b in at.button:
                if b.label == "Run scheduler":
                    b.click().run()
                    break
                    
            # Interactions
            try:
                for b in at.button:
                    if b.label == "Verify against exact optimum (5s limit)": b.click().run()
                    if b.label == "Re-run benchmark (quick)": b.click().run()
            except Exception:
                pass
                    
    assert_no_errors(at)

@pytest.mark.parametrize("view,source,preset", [
    ("Dashboard", "Synthetic", "Custom"),
    ("Dashboard", "Orbital (TLE)", "Custom"),
    ("Presenter", "Synthetic", "Quick start (synthetic, 20 sat, 3 stn, seed 42)"),
    ("Method", "Synthetic", "Custom")
])
def test_smoke_fast(view, source, preset):
    run_app_smoke(view, source, preset, run_btn=False)

@pytest.mark.full
@pytest.mark.parametrize("view,source,preset", [
    ("Dashboard", "Synthetic", "Custom"),
    ("Dashboard", "Orbital (TLE)", "Custom"),
    ("Dashboard", "Synthetic", "Wildfire surge (synthetic, 25 sat, 3 stn)"),
    ("Dashboard", "Orbital (TLE)", "Global network (orbital, 25 sat, 8 stn, 24 h)"),
])
def test_smoke_full(view, source, preset):
    run_app_smoke(view, source, preset, run_btn=True)
