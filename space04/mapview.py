"""
mapview.py - Ground track map using Plotly scattergeo.
No Streamlit imports.
"""
import plotly.graph_objects as go
import pandas as pd


def create_ground_map(stations_df: pd.DataFrame, tracks: dict,
                      scheduled_passes: pd.DataFrame, current_time_min: float,
                      horizon_min: int, optimized_stations: set = None,
                      tail_minutes: float = 30.0) -> go.Figure:
    """
    Create an equirectangular map showing ground stations and satellite positions.
    
    stations_df: DataFrame with name, lat, lon columns
    tracks: dict {sat_name: [(time_min, lat, lon), ...]}
    scheduled_passes: the Optimized schedule DataFrame
    current_time_min: current time on the slider
    horizon_min: total horizon
    optimized_stations: set of station names used in the optimized schedule
    tail_minutes: length of ground track tail in minutes
    """
    if optimized_stations is None:
        optimized_stations = set()

    fig = go.Figure()

    # Station markers
    for _, row in stations_df.iterrows():
        is_active = row['name'] in optimized_stations
        fig.add_trace(go.Scattergeo(
            lat=[row['lat']],
            lon=[row['lon']],
            mode='markers+text',
            marker=dict(
                size=8,
                symbol='square',
                color='#1C1F22',
                line=dict(width=2, color='#C8421B' if is_active else '#1C1F22')
            ),
            text=[row['name']],
            textposition='top center',
            textfont=dict(family='IBM Plex Mono', size=11, color='#1C1F22'),
            showlegend=False,
            hoverinfo='text',
            hovertext=f"{row['name']}<br>Lat: {row['lat']:.2f}, Lon: {row['lon']:.2f}"
        ))

    # Find which satellites are currently downlinking in the optimized schedule
    active_downlinks = {}
    if len(scheduled_passes) > 0:
        for _, p in scheduled_passes.iterrows():
            if p['start_min'] <= current_time_min < p['end_min']:
                active_downlinks[p['satellite']] = p['station']

    # Satellite positions and tails
    for sat_name, track in tracks.items():
        if not track:
            continue

        # Find position at current time
        current_pos = None
        for i, (t_m, lat, lon) in enumerate(track):
            if t_m >= current_time_min:
                current_pos = (lat, lon)
                break
        if current_pos is None and track:
            current_pos = (track[-1][1], track[-1][2])

        # Draw tail (previous tail_minutes)
        tail_lats = []
        tail_lons = []
        for t_m, lat, lon in track:
            if current_time_min - tail_minutes <= t_m <= current_time_min:
                tail_lats.append(lat)
                tail_lons.append(lon)

        is_downlinking = sat_name in active_downlinks
        line_color = '#C8421B' if is_downlinking else '#1C1F22'

        # Tail line (break at dateline crossings to avoid wrapping artifacts)
        if len(tail_lats) > 1:
            seg_lats = [tail_lats[0]]
            seg_lons = [tail_lons[0]]
            for k in range(1, len(tail_lats)):
                if abs(tail_lons[k] - tail_lons[k - 1]) > 180:
                    # Dateline crossing, break segment
                    fig.add_trace(go.Scattergeo(
                        lat=seg_lats, lon=seg_lons,
                        mode='lines',
                        line=dict(width=1, color=line_color),
                        showlegend=False, hoverinfo='skip'
                    ))
                    seg_lats = [tail_lats[k]]
                    seg_lons = [tail_lons[k]]
                else:
                    seg_lats.append(tail_lats[k])
                    seg_lons.append(tail_lons[k])
            if len(seg_lats) > 1:
                fig.add_trace(go.Scattergeo(
                    lat=seg_lats, lon=seg_lons,
                    mode='lines',
                    line=dict(width=1, color=line_color),
                    showlegend=False, hoverinfo='skip'
                ))

        # Current position dot
        if current_pos:
            fig.add_trace(go.Scattergeo(
                lat=[current_pos[0]],
                lon=[current_pos[1]],
                mode='markers',
                marker=dict(size=6, color=line_color),
                showlegend=False,
                hoverinfo='text',
                hovertext=f"{sat_name}<br>{'DOWNLINKING to ' + active_downlinks[sat_name] if is_downlinking else 'Idle'}"
            ))

            # Downlink line to station
            if is_downlinking:
                stn_name = active_downlinks[sat_name]
                stn_row = stations_df[stations_df['name'] == stn_name]
                if len(stn_row) > 0:
                    s = stn_row.iloc[0]
                    fig.add_trace(go.Scattergeo(
                        lat=[current_pos[0], s['lat']],
                        lon=[current_pos[1], s['lon']],
                        mode='lines',
                        line=dict(width=1.5, color='#C8421B'),
                        showlegend=False, hoverinfo='skip'
                    ))

    fig.update_geos(
        projection_type='equirectangular',
        showland=True, landcolor='#E9E4D6',
        showocean=True, oceancolor='#FBF9F4',
        showcoastlines=True, coastlinecolor='#B9B3A2', coastlinewidth=1,
        showlakes=False,
        showcountries=False,
        showframe=False,
        lonaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='#E6E1D3', dtick=30),
        lataxis=dict(showgrid=True, gridwidth=0.5, gridcolor='#E6E1D3', dtick=30),
    )

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=400,
        geo=dict(bgcolor='rgba(0,0,0,0)')
    )

    return fig
