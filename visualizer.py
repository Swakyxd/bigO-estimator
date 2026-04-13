"""
Complexity Visualization — generates a Plotly figure of theoretical Big-O
growth curves and highlights where the analyzed code falls.
"""

import math
import plotly.graph_objects as go

# ── Curve definitions ──────────────────────────────────────────────────────────

N_MAX = 50          # x-axis upper bound
N_POINTS = 200      # number of sample points
CAP = 1e6           # clip extremely large values so the chart stays readable

_CURVES = [
    # (label, color, dash, fn)
    ("O(1)",        "#94a3b8", "dot",       lambda n: 1),
    ("O(log N)",    "#22d3ee", "dashdot",   lambda n: math.log2(n)),
    ("O(N)",        "#4ade80", "solid",     lambda n: n),
    ("O(N log N)",  "#facc15", "solid",     lambda n: n * math.log2(n)),
    ("O(N²)",       "#fb923c", "solid",     lambda n: n ** 2),
    ("O(2^N)",      "#f87171", "dash",      lambda n: min(2 ** n, CAP)),
    ("O(N!)",       "#e879f9", "dash",      lambda n: min(math.factorial(int(n)), CAP)
                                             if n <= 12 else CAP),
]

# Map common LLM output strings → canonical labels used above
_LABEL_MAP = {
    "o(1)":         "O(1)",
    "o(log n)":     "O(log N)",
    "o(log n)":     "O(log N)",
    "o(n)":         "O(N)",
    "o(n log n)":   "O(N log N)",
    "o(n log n)":   "O(N log N)",
    "o(n^2)":       "O(N²)",
    "o(n²)":        "O(N²)",
    "o(n2)":        "O(N²)",
    "o(n**2)":      "O(N²)",
    "o(2^n)":       "O(2^N)",
    "o(2**n)":      "O(2^N)",
    "o(n!)":        "O(N!)",
}


def _normalize(label: str) -> str | None:
    """Map an LLM complexity string to a canonical chart label."""
    key = label.strip().lower().replace(" ", "")
    return _LABEL_MAP.get(key)


def build_complexity_chart(analyzed_complexity: str) -> go.Figure:
    """
    Build a Plotly figure with all theoretical Big-O growth curves.
    The curve matching `analyzed_complexity` is highlighted.

    Args:
        analyzed_complexity: e.g. "O(N²)" or "O(n^2)" from the parser.

    Returns:
        go.Figure ready for st.plotly_chart()
    """
    import numpy as np

    xs = list(np.linspace(1, N_MAX, N_POINTS))
    highlighted = _normalize(analyzed_complexity)

    fig = go.Figure()

    for label, color, dash, fn in _CURVES:
        is_hit = (label == highlighted)
        ys = []
        for x in xs:
            try:
                ys.append(fn(x))
            except Exception:
                ys.append(CAP)

        # Scale the y-axis by showing values relative to N_MAX
        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            name=label,
            mode="lines",
            line=dict(
                color=color,
                width=3.5 if is_hit else 1.5,
                dash="solid" if is_hit else dash,
            ),
            opacity=1.0 if is_hit else 0.35,
            hovertemplate=f"<b>{label}</b><br>N=%{{x:.0f}}<br>ops≈%{{y:.1f}}<extra></extra>",
        ))

        # Add a highlighted marker at N=20 for the matched curve
        if is_hit:
            try:
                y_marker = fn(20)
            except Exception:
                y_marker = CAP
            fig.add_trace(go.Scatter(
                x=[20],
                y=[min(y_marker, CAP)],
                mode="markers+text",
                marker=dict(color=color, size=14, symbol="circle",
                            line=dict(color="white", width=2)),
                text=[f"← Your code\n{label}"],
                textposition="middle right",
                textfont=dict(color=color, size=12, family="JetBrains Mono"),
                showlegend=False,
                hoverinfo="skip",
            ))

    fig.update_layout(
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
        title=dict(
            text=f"Complexity Growth Curves"
                 + (f" · <span style='color:#00ADB5'>{highlighted} highlighted</span>"
                    if highlighted else ""),
            font=dict(size=14, color="#E2E8F0"),
            x=0,
        ),
        legend=dict(
            bgcolor="rgba(15,23,42,0.8)",
            bordercolor="rgba(255,255,255,0.06)",
            borderwidth=1,
            font=dict(family="JetBrains Mono", size=11),
            orientation="v",
            x=1.01, y=1,
        ),
        xaxis=dict(
            title="N (input size)",
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.08)",
            tickfont=dict(family="JetBrains Mono"),
            title_font=dict(color="#64748b"),
        ),
        yaxis=dict(
            title="Operations (relative)",
            gridcolor="rgba(255,255,255,0.04)",
            zerolinecolor="rgba(255,255,255,0.08)",
            tickfont=dict(family="JetBrains Mono"),
            title_font=dict(color="#64748b"),
            range=[0, min(N_MAX ** 2 * 0.4, CAP)],
        ),
        margin=dict(l=60, r=160, t=50, b=50),
        hovermode="x unified",
    )

    return fig
