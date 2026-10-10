import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Stronger priority palette
PRIORITY_COLORS = {
    1: '#CFC3A0',
    2: '#D4A65E',
    3: '#C07A2E',
    4: '#A04A1A',
    5: '#6B2210'
}

PRIORITY_TEXT_COLORS = {
    1: '#1C1F22',
    2: '#1C1F22',
    3: '#1C1F22',
    4: '#FBF9F4',
    5: '#FBF9F4'
}

def create_gantt(df: pd.DataFrame, all_stations: list, x_range: list = [0, 360], gained_ids: set = None, current_t: int = None, dropped_passes: list = None, gap: int = 0, start_utc = None):
    fig = go.Figure()
    
    all_stations = sorted(list(set(all_stations)), reverse=True)
    horizon = int(x_range[1] - x_range[0])
    
    # Background banding
    for i, stn in enumerate(all_stations):
        bg_color = '#F3F0E8' if i % 2 == 0 else '#EFEBE0'
        fig.add_shape(
            type="rect",
            x0=x_range[0], x1=x_range[1],
            y0=i - 0.5, y1=i + 0.5,
            fillcolor=bg_color,
            layer="below",
            line_width=0
        )
        
    if current_t is not None:
        fig.add_shape(type="rect", x0=x_range[0], x1=current_t, y0=-0.5, y1=len(all_stations)-0.5, fillcolor="rgba(0,0,0,0.05)", line_width=0, layer="above")
        fig.add_vline(x=current_t, line_color="#C8421B", line_width=2, line_dash="solid", layer="above")
        
    if dropped_passes:
        for p in dropped_passes:
            if p['station'] in all_stations:
                y_idx = all_stations.index(p['station'])
                fig.add_shape(
                    type="rect",
                    x0=p['start_min'],
                    x1=p['end_min'],
                    y0=y_idx - 0.35,
                    y1=y_idx + 0.35,
                    line=dict(color="#C8421B", width=2, dash="dash"),
                    fillcolor="rgba(0,0,0,0)",
                    layer="above"
                )
    
    if len(df) > 0:
        for p in [1, 2, 3, 4, 5]:
            df_p = df[df['base_priority'] == p].copy()
            if len(df_p) > 0:
                # Draw turnaround gap hatch
                if gap > 0:
                    for idx, row in df_p.iterrows():
                        if row['station'] in all_stations and row['end_min'] - row['start_min'] > 1:
                            y_idx = all_stations.index(row['station'])
                            fig.add_shape(
                                type="rect",
                                x0=row['end_min'],
                                x1=row['end_min'] + gap,
                                y0=y_idx - 0.35,
                                y1=y_idx + 0.35,
                                fillcolor="#E6E1D3",
                                line_width=0,
                                layer="below"
                            )

                # Text formatting based on duration
                durations = df_p['end_min'] - df_p['start_min']
                texts = []
                for idx, row in df_p.iterrows():
                    dur = row['end_min'] - row['start_min']
                    sat = row['satellite']
                    if dur > 8:
                        texts.append(sat)
                    elif dur > 4:
                        texts.append(sat.split('-')[-1])
                    else:
                        texts.append("")
                        
                hover_texts = []
                for _, row in df_p.iterrows():
                    wait = max(0, row['start_min'] - row['arrival_min'])
                    hover = (
                        f"Satellite: {row['satellite']}<br>"
                        f"Station: {row['station']}<br>"
                        f"Window: {row['start_min']} - {row['end_min']}<br>"
                        f"Class: {row['mission_class']}<br>"
                        f"Base P: {row['base_priority']}<br>"
                        f"Effective P: {row['effective_priority']:.1f}<br>"
                        f"Arrival: {row['arrival_min']}<br>"
                        f"Wait: {wait}<br>"
                        f"Deadline: {row['deadline_min']}<br>"
                        f"Data: {row['downlinked_gb']:.2f} GB<br>"
                        f"Value: {row['value']:.2f}"
                    )
                    hover_texts.append(hover)
                
                line_colors = []
                line_widths = []
                for pid in df_p['pass_id']:
                    if gained_ids and pid in gained_ids:
                        line_colors.append('#C8421B')
                        line_widths.append(2)
                    else:
                        line_colors.append('#FBF9F4')
                        line_widths.append(1)
                
                fig.add_trace(go.Bar(
                    x=durations,
                    y=df_p['station'],
                    base=df_p['start_min'],
                    orientation='h',
                    marker_color=PRIORITY_COLORS[p],
                    marker_line=dict(width=line_widths, color=line_colors),
                    name=f'P{p}',
                    text=texts,
                    textposition='inside',
                    insidetextanchor='middle',
                    textangle=0,
                    hoverinfo='text',
                    hovertext=hover_texts,
                    textfont=dict(family="IBM Plex Mono", size=11, color=PRIORITY_TEXT_COLORS[p])
                ))

    # Dynamic tick spacing based on horizon
    if horizon <= 360:
        dtick = 30
    elif horizon <= 720:
        dtick = 60
    else:
        dtick = 120

    # Gridlines
    for m in range(0, int(x_range[1]) + 1, dtick):
        fig.add_vline(x=m, line_width=1, line_color='#D8D3C5', layer='below')

    # X-axis configuration with optional UTC labels
    tickvals = list(range(0, int(x_range[1]) + 1, dtick))
    if start_utc is not None:
        import datetime
        ticktext = []
        for v in tickvals:
            t_utc = start_utc + datetime.timedelta(minutes=v)
            ticktext.append(f"{v}<br>{t_utc.strftime('%H:%M')}")
    else:
        ticktext = [str(v) for v in tickvals]

    fig.update_layout(
        barmode='overlay',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=30),
        height=60 + len(all_stations) * 64,
        showlegend=False,
        bargap=0.3,
        uniformtext=dict(minsize=10, mode='hide'),
        yaxis=dict(
            categoryarray=all_stations,
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=False,
            zeroline=False
        ),
        xaxis=dict(
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=True,
            gridcolor='#E6E1D3',
            tickvals=tickvals,
            ticktext=ticktext,
            zeroline=False,
            range=x_range
        )
    )
    return fig

def create_priority_chart(df_breakdown: pd.DataFrame):
    fig = px.bar(
        df_breakdown,
        x='Priority',
        y='Data (GB)',
        color='Scheduler',
        barmode='group',
        color_discrete_map={
            'FCFS': '#1C1F22',
            'Optimized': '#C8421B'
        }
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        height=280,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title_text='',
            font=dict(family="IBM Plex Sans", size=11, color="#6B6A63")
        ),
        xaxis=dict(
            title='',
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            title='',
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=True,
            gridcolor='#D8D3C5',
            zeroline=False
        )
    )
    
    return fig

def create_utilization_chart(df_util: pd.DataFrame):
    fig = px.bar(
        df_util,
        x='Utilization (%)',
        y='Station',
        color='Scheduler',
        barmode='group',
        orientation='h',
        color_discrete_map={
            'FCFS': '#1C1F22',
            'Optimized': '#C8421B'
        }
    )
    
def create_convergence_chart(history: list, fcfs_score: float, exact_score: float = None):
    df_hist = pd.DataFrame(history)
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_hist['iteration'], y=df_hist['current_score'],
        mode='lines', line=dict(color='#1C1F22', width=1),
        name='Current Score'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_hist['iteration'], y=df_hist['best_score'],
        mode='lines', line=dict(color='#C8421B', width=2),
        name='Best Score'
    ))
    
    fig.add_hline(y=fcfs_score, line_dash="dash", line_color="#6B6A63", annotation_text="FCFS")
    if exact_score is not None and exact_score > 0:
        fig.add_hline(y=exact_score, line_dash="dash", line_color="#C8421B", annotation_text="Exact Optimum")
        
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        height=180,
        showlegend=False,
        xaxis=dict(
            title='Iteration',
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            titlefont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=True, gridcolor='#E6E1D3', zeroline=False
        ),
        yaxis=dict(
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=True, gridcolor='#E6E1D3', zeroline=False
        )
    )
    return fig

def create_runtime_chart(df_bench: pd.DataFrame):
    df_agg = df_bench.groupby('n_passes').agg(
        t_fcfs_mean=('t_fcfs', 'mean'), t_fcfs_std=('t_fcfs', 'std'),
        t_opt_mean=('t_opt', 'mean'), t_opt_std=('t_opt', 'std'),
        t_exact_mean=('t_exact', 'mean'), t_exact_std=('t_exact', 'std')
    ).reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_agg['n_passes'], y=df_agg['t_fcfs_mean'],
        error_y=dict(type='data', array=df_agg['t_fcfs_std'], visible=True),
        mode='lines+markers', line=dict(color='#1C1F22', width=1),
        name='FCFS'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_agg['n_passes'], y=df_agg['t_opt_mean'],
        error_y=dict(type='data', array=df_agg['t_opt_std'], visible=True),
        mode='lines+markers', line=dict(color='#C8421B', width=2),
        name='Optimized'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_agg['n_passes'], y=df_agg['t_exact_mean'],
        error_y=dict(type='data', array=df_agg['t_exact_std'], visible=True),
        mode='lines+markers', line=dict(color='#1C1F22', width=2, dash='dash'),
        name='Exact solver'
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0),
        height=280,
        title=dict(text="RUNTIME VS SIZE", font=dict(family="IBM Plex Sans", size=12, color="#6B6A63")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(family="IBM Plex Sans", size=11, color="#6B6A63")),
        xaxis=dict(
            title='Number of passes',
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            titlefont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=True, gridcolor='#E6E1D3', zeroline=False
        ),
        yaxis=dict(
            title='Runtime (s)', type='log',
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            titlefont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=True, gridcolor='#E6E1D3', zeroline=False
        )
    )
    return fig

def create_quality_chart(df_bench: pd.DataFrame):
    df_agg = df_bench.groupby('n_passes').agg(
        opt_gap=('gap_pct', 'mean'), opt_gap_std=('gap_pct', 'std'),
        fcfs_score=('fcfs_score', 'mean'), opt_score=('opt_score', 'mean'),
        exact_score=('exact_score', 'mean')
    ).reset_index()
    
    # Calculate % of exact optimum
    df_agg['fcfs_pct'] = (df_agg['fcfs_score'] / df_agg['exact_score'] * 100).fillna(0)
    df_agg['opt_pct'] = (df_agg['opt_score'] / df_agg['exact_score'] * 100).fillna(0)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_agg['n_passes'], y=df_agg['fcfs_pct'],
        mode='lines+markers', line=dict(color='#1C1F22', width=2),
        name='FCFS'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_agg['n_passes'], y=df_agg['opt_pct'],
        mode='lines+markers', line=dict(color='#C8421B', width=2),
        name='Optimized'
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0),
        height=280,
        title=dict(text="QUALITY VS SIZE", font=dict(family="IBM Plex Sans", size=12, color="#6B6A63")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(family="IBM Plex Sans", size=11, color="#6B6A63")),
        xaxis=dict(
            title='Number of passes',
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            titlefont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=True, gridcolor='#E6E1D3', zeroline=False
        ),
        yaxis=dict(
            title='% of Exact Optimum', range=[60, 100],
            tickfont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            titlefont=dict(family="IBM Plex Mono", size=11, color="#6B6A63"),
            showgrid=True, gridcolor='#E6E1D3', zeroline=False
        )
    )
    return fig
