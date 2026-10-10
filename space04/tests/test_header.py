import pytest
from unittest.mock import patch
import pandas as pd
import components

def test_masthead_and_tabs():
    with patch('components.st.markdown') as mock_md:
        res = {
            'df_passes': pd.DataFrame({'satellite': ['A', 'B']}),
            'n_stn': 3,
            'scenario': "10 satellites, 3 stations, 150 passes, 6h horizon"
        }
        components.render_masthead("Dashboard", res, "Synthetic", is_presenter=False)
        html = mock_md.call_args[0][0]
        
        assert "VyomSetu" in html
        assert "SATELLITES" in html
        assert "STATIONS" in html
        assert "PASSES" in html
        assert "HORIZON" in html
        assert "SOURCE" in html
        
        assert "2" in html
        assert "3" in html
        assert "2" in html # len of df_passes
        assert "6h" in html
        assert "Synthetic" in html
        
    with patch('components.st.markdown') as mock_md:
        sections = [("sec1", "Sec 1"), ("sec2", "Sec 2")]
        components.render_tabs(sections)
        
        tabs_html = mock_md.call_args[0][0]
        assert "Sec 1" in tabs_html
        assert "Sec 2" in tabs_html
        assert "|" not in tabs_html
        
        assert tabs_html.count('data-id="sec1"') == 1
        assert tabs_html.count('data-id="sec2"') == 1
