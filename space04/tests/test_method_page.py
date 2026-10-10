import pytest
from unittest.mock import MagicMock, patch
import method
import optimizer
import pandas as pd

def test_method_page_content():
    # Mock streamlit
    with patch('method.st') as mock_st:
        # Mock session state for config
        mock_st.session_state.get.return_value = {
            "alpha": 0.5,
            "turnaround_gap": 2
        }
        
        # Call the method
        method.render_method_page()
        
        # Collect all markdown text
        full_text = ""
        for call in mock_st.markdown.call_args_list:
            args, kwargs = call
            full_text += args[0] + "\n"
            
        # 1. Contains required words
        required_words = [
            "FCFS", "Skyfield", "CP-SAT", "turnaround", "Tabu", 
            "Dynamic Programming", "replanning", "Known limitations", "Liu"
        ]
        for w in required_words:
            assert w in full_text, f"Missing required word: {w}"
            
        # 2. Contains required sentence
        assert "Orbits are real; priorities and data volumes are simulated." in full_text
        
        # 3. Does NOT contain forbidden words
        forbidden_words = ["MSDSP", "proving", "formally verified"]
        for w in forbidden_words:
            assert w not in full_text, f"Found forbidden word: {w}"
            
        # 4. Check constants
        assert str(optimizer.TABU_LENGTH) in full_text
        assert "0.5" in full_text # alpha
        assert "2" in full_text # turnaround
        assert "10" in full_text # elevation mask
