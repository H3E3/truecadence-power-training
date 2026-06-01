from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_power_curve(best_powers, ftp):
    """Power duration curve."""
    dur_labels = ['5s', '30s', '1min', '5min', '20min', '40min', '60min', '2h', '3h']
    dur_seconds = [5, 30, 60, 300, 1200, 2400, 3600, 7200, 10800]
    values = [best_powers.get(d, 0) or None for d in dur_labels]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dur_seconds, y=values, mode='lines+markers',
        line=dict(color='#FF6B35', width=3),
        marker=dict(size=10),
        name='Best Power',
    ))
    if ftp:
        fig.add_hline(y=ftp, line_dash="dash", line_color="#4ECDC4",
                      annotation_text=f"FTP: {ftp}W")
    fig.update_xaxes(type="log", title="Duration", tickvals=dur_seconds, ticktext=dur_labels)
    fig.update_yaxes(title="Watts")
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20),
                      template="plotly_dark")
    return fig


def plot_pmc(rides, compute_daily_pmc_func):
    """PMC chart: CTL/ATL/TSB over natural calendar days."""
    if not rides:
        return go.Figure()

    df = compute_daily_pmc_func(rides)
    if df.empty:
        return go.Figure()

    hovertpl = '<b>%{x}</b><br>%{y:,.0f}<extra></extra>'

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df['date'], y=df['ctl'], name='体能CTL', hovertemplate=hovertpl, line=dict(color='#4ECDC4', width=3)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['atl'], name='疲劳ATL', hovertemplate=hovertpl, line=dict(color='#FF6B35', width=3)))
    fig.add_trace(go.Bar(x=df['date'], y=df['tsb'], name='状态TSB', hovertemplate=hovertpl, marker_color='#45B7D1', opacity=0.7, showlegend=True), secondary_y=True)

    fig.update_layout(
        height=400, margin=dict(l=30, r=30, t=30, b=30),
        template="plotly_dark",
        hovermode='x unified',
        hoverlabel=dict(font_size=16, font_family="Arial"),
    )
    fig.update_yaxes(title_text="CTL / ATL", secondary_y=False)
    fig.update_yaxes(title_text="TSB", secondary_y=True)
    return fig
