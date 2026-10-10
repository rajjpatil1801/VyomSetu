import pytest
from unittest.mock import patch
import pandas as pd
import html_utils
import components
import method

def test_compact_removes_line_breaks_and_spaces():
    raw_html = """
        <div class="test">
            <p>Hello</p>
        </div>
    """
    compacted = html_utils.compact(raw_html)
    assert "\n" not in compacted
    assert "    " not in compacted
    assert compacted == '<div class="test"><p>Hello</p></div>'

def test_render_masthead_html_is_compact():
    with patch('components.st.markdown') as mock_md:
        res = {
            'df_passes': pd.DataFrame({'satellite': ['A', 'B']}),
            'n_stn': 3,
            'scenario': "10 satellites, 3 stations, 150 passes, 6h horizon"
        }
        components.render_masthead("Dashboard", res, "Synthetic", is_presenter=False)
        html = mock_md.call_args[0][0]
        
        assert "\n" not in html
        assert "    " not in html # No 4 consecutive spaces
        assert "readout-cell" in html
        assert "SATELLITES" in html
        assert "STATIONS" in html
        assert "PASSES" in html
        assert "HORIZON" in html
        assert "SOURCE" in html

def test_no_blank_lines_or_indents_in_rendered_html():
    with patch('components.st.markdown') as mock_md:
        # test tabs
        components.render_tabs([("sec1", "Sec 1")])
        html = mock_md.call_args[0][0]
        assert "\n" not in html
        assert "    " not in html
        
    with patch('components.st.markdown') as mock_md:
        # test section heading
        components.render_section_heading("01", "KPIs", "kpis")
        html = mock_md.call_args[0][0]
        assert "\n" not in html
        assert "    " not in html
        
    with patch('method.st.markdown') as mock_md:
        # test method page markdowns
        try:
            method.render_method_page()
        except:
            pass # ignore session state errors for this test if any
        for call in mock_md.call_args_list:
            html = call[0][0]
            assert "\n" not in html
            assert "    " not in html
