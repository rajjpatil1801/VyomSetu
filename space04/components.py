import streamlit as st
import html_utils

def render_masthead(view_mode, res=None, pass_source=None, is_presenter=False):
    # SVG logo
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="72" height="72" fill="none">
      <line x1="5" y1="38" x2="43" y2="38" stroke="#F3F0E8" stroke-width="2.5" stroke-linecap="square"/>
      <path d="M6 38 Q24 2 42 38" stroke="#F3F0E8" stroke-width="2.5" fill="none"/>
      <line x1="15" y1="24.5" x2="15" y2="38" stroke="#F3F0E8" stroke-width="1.25"/>
      <line x1="24" y1="20" x2="24" y2="38" stroke="#F3F0E8" stroke-width="1.25"/>
      <line x1="33" y1="24.5" x2="33" y2="38" stroke="#F3F0E8" stroke-width="1.25"/>
      <circle cx="24" cy="20" r="4" fill="#C8421B"/>
    </svg>
    """
    
    title_size = "56px" if is_presenter else "48px"
    value_size = "26px" if is_presenter else "22px"
    
    if view_mode == "Method":
        readout_html = f'''
        <div class="readout-cell">
            <div class="readout-label">PAGE</div>
            <div class="readout-value" style="font-size: {value_size};">METHOD</div>
        </div>
        '''
    else:
        # Extract from res
        if res is not None:
            n_sat = res.get('df_passes', {}).get('satellite', set())
            n_sat = len(set(n_sat)) if isinstance(n_sat, set) else len(res['df_passes']['satellite'].unique()) if 'satellite' in res['df_passes'] else "0"
            n_stn = res.get('n_stn', 0)
            n_passes = len(res.get('df_passes', []))
            
            # Try to figure out horizon
            scenario = res.get('scenario', '')
            horizon = ""
            if "h horizon" in scenario:
                horizon = scenario.split(",")[-1].strip().replace(" horizon", "")
            else:
                horizon = "6 h"
        else:
            n_sat = "0"
            n_stn = "0"
            n_passes = "0"
            horizon = "0"

        cells = []
        cells.append(f'<div class="readout-cell"><div class="readout-label">SATELLITES</div><div class="readout-value" style="font-size: {value_size};">{n_sat}</div></div>')
        cells.append(f'<div class="readout-cell"><div class="readout-label">STATIONS</div><div class="readout-value" style="font-size: {value_size};">{n_stn}</div></div>')
        cells.append(f'<div class="readout-cell"><div class="readout-label">PASSES</div><div class="readout-value" style="font-size: {value_size};">{n_passes}</div></div>')
        cells.append(f'<div class="readout-cell"><div class="readout-label">HORIZON</div><div class="readout-value" style="font-size: {value_size};">{horizon}</div></div>')
        cells.append(f'<div class="readout-cell"><div class="readout-label">SOURCE</div><div class="readout-value" style="font-size: {value_size};">{pass_source if pass_source else "Synthetic"}</div></div>')
        readout_html = "".join(cells)
        
    masthead_html = f'''
    <div class="masthead">
        <div class="masthead-left">
            <div>{svg}</div>
            <div class="masthead-text">
                <div class="masthead-title" style="font-size: {title_size};">VyomSetu</div>
                <div class="masthead-tagline">SKY BRIDGE <span style="color:#C8421B">/</span> DOWNLINK SCHEDULER</div>
                <div class="masthead-desc">Autonomous ground station scheduler for multi-satellite downlink.</div>
            </div>
        </div>
        <div class="masthead-right">
            {readout_html}
        </div>
    </div>
    '''
    st.markdown(html_utils.compact(masthead_html), unsafe_allow_html=True)


def render_tabs(sections):
    tabs_html = '<div class="tab-strip">'
    for i, (sec_id, label) in enumerate(sections):
        index_str = f"{(i+1):02d}"
        tabs_html += f'<a href="#{sec_id}" class="tab-item" data-id="{sec_id}"><span class="tab-index">{index_str}</span><span class="tab-label">{label}</span></a>'
    tabs_html += '</div>'
    st.markdown(html_utils.compact(tabs_html), unsafe_allow_html=True)
    
    # Scroll spy
    import streamlit.components.v1 as components
    spy_js = """
    <script>
    setTimeout(function() {
        const doc = window.parent.document;
        const tabs = doc.querySelectorAll('.tab-item');
        if (!tabs.length) return;
        
        const sections = Array.from(tabs).map(tab => {
            const id = tab.getAttribute('data-id');
            return doc.getElementById(id);
        }).filter(Boolean);
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    tabs.forEach(tab => tab.classList.remove('active'));
                    const activeTab = doc.querySelector(`.tab-item[data-id="${entry.target.id}"]`);
                    if (activeTab) activeTab.classList.add('active');
                }
            });
        }, { rootMargin: '-60px 0px -60% 0px' });
        
        sections.forEach(sec => observer.observe(sec));
    }, 1000);
    </script>
    """
    components.html(html_utils.compact(spy_js), height=0)


def render_section_heading(index_str, title, anchor_id, caption=""):
    html = f'''
    <div id="{anchor_id}" class="section-heading" style="scroll-margin-top: 60px;">
        <div style="display: flex; align-items: baseline; gap: 8px;">
            <span style="font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: #C8421B;">{index_str}</span>
            <span style="font-family: 'IBM Plex Sans', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; color: #1C1F22; font-weight: 600;">{title}</span>
            <div style="flex-grow: 1; height: 1px; background-color: #D8D3C5; margin-left: 8px; position: relative; top: -4px;"></div>
        </div>
        {f'<div style="font-size: 12px; color: #6B6A63; margin-top: 4px; margin-bottom: 16px;">{caption}</div>' if caption else '<div style="margin-bottom: 16px;"></div>'}
    </div>
    '''
    st.markdown(html_utils.compact(html), unsafe_allow_html=True)
