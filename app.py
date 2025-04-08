import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Load data
df = pd.read_csv("cleaned_security_incidents.csv")
df["date"] = pd.to_datetime(df["date"])
df["year"] = df["date"].dt.year
df["Region"] = df["Region"].fillna("Unknown")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.Img(src="/assets/RISK MAP.png", style={"height": "80px"}), width=2),
        dbc.Col(html.H1("The Risk Map Dashboard", className="display-5 text-gradient"), width=8),
        dbc.Col(html.Div(id="narration", className="text-end text-light fst-italic"), width=2),
    ], className="align-items-center my-3"),

    dbc.Row([
        dbc.Col(dcc.Dropdown(
            id="region-filter",
            options=[{"label": r, "value": r} for r in sorted(df["Region"].unique())],
            placeholder="Select Region...",
            multi=False,
            value=None,
            style={"color": "black"}
        ), width=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="sunburst-chart"), width=6),
        dbc.Col(dcc.Graph(id="treemap-chart"), width=6)
    ]),

    dbc.Row([
        dbc.Col(dcc.Graph(id="heatmap", config={"displayModeBar": False}), width=6),
        dbc.Col(dcc.Graph(id="trend", config={"displayModeBar": False}), width=6),
    ]),

    dbc.Row([
        dbc.Col(dcc.Graph(id="animated-trend"), width=12)
    ], className="mt-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="actor-profile"), width=6),
        dbc.Col(html.Button("📄 Export Report (Coming Soon)", className="btn btn-outline-light w-100", disabled=True), width=6)
    ], className="mt-3"),

    html.Footer("© 2025 The Risk Map | Designed with ❤️ using Dash & Plotly", className="text-center text-muted mt-4")
], fluid=True, className="purple-bg")

@app.callback(
    Output("sunburst-chart", "figure"),
    Output("treemap-chart", "figure"),
    Output("heatmap", "figure"),
    Output("trend", "figure"),
    Output("animated-trend", "figure"),
    Output("actor-profile", "figure"),
    Output("narration", "children"),
    Input("region-filter", "value")
)
def update_visuals(region):
    dff = df.copy()
    if region:
        dff = dff[dff["Region"] == region]

    sb_data = dff[dff["total_casualties"] > 0].copy()
    max_cas = sb_data["total_casualties"].max()
    bins = [0, 1, 5, 10, 20, 50, 100, 200, 500, 1000]
    bins = [b for b in bins if b <= max_cas]
    if bins and bins[-1] < max_cas:
        bins.append(max_cas + 1)
    labels = ["1", "2–5", "6–10", "11–20", "21–50", "51–100", "101–200", "201–500", "501–1000", "1000+"]
    labels = labels[:len(bins)-1]
    sb_data["casualty_range"] = pd.cut(sb_data["total_casualties"], bins=bins, labels=labels, include_lowest=True)
    sb_grouped = sb_data.groupby(["casualty_range", "Region"]).size().reset_index(name="count")
    fig_sb = px.sunburst(sb_grouped, path=["casualty_range", "Region"], values="count",
                         color="casualty_range", color_discrete_sequence=px.colors.sequential.OrRd,
                         title="⚠️ Casualty Distribution")
    fig_sb.update_layout(template="plotly_dark", title_x=0.5)

    treedata = dff[dff["Means of attack"].notna() & dff["Attack context"].notna()]
    tree_grouped = treedata.groupby(["Means of attack", "Attack context"]).size().reset_index(name="count")
    fig_tree = px.treemap(tree_grouped, path=["Means of attack", "Attack context"], values="count",
                          color="count", color_continuous_scale="Reds", title="🎯 Attack Method vs. Context")
    fig_tree.update_layout(template="plotly_dark", title_x=0.5)

    heatdata = dff.groupby("Country").size().reset_index(name="count")
    fig_map = px.choropleth(heatdata, locations="Country", locationmode="country names",
                            color="count", color_continuous_scale="Plasma", title="🌍 Global Incidents")
    fig_map.update_layout(template="plotly_dark", title_x=0.5)

    trend = dff.groupby(dff["date"].dt.to_period("M")).agg({
        "Incident ID": "count",
        "total_casualties": "sum"
    }).reset_index()
    trend["date"] = trend["date"].dt.to_timestamp()
    fig_trend = go.Figure([
        go.Scatter(x=trend["date"], y=trend["Incident ID"], name="Incidents", mode="lines+markers", line=dict(color="royalblue")),
        go.Scatter(x=trend["date"], y=trend["total_casualties"], name="Casualties", mode="lines+markers", line=dict(color="firebrick"))
    ])
    fig_trend.update_layout(template="plotly_dark", title="📈 Monthly Trends", title_x=0.5, hovermode="x unified")

    yearwise = dff.groupby(["year", "Region"]).agg({"Incident ID": "count"}).reset_index()
    fig_anim = px.bar(yearwise, x="Region", y="Incident ID", color="Region", animation_frame="year",
                      title="📊 Incident Frequency Animation by Region", template="plotly_dark")
    fig_anim.update_layout(title_x=0.5)

    actor = dff.groupby("Actor type").agg({
        "Total affected": "sum",
        "Incident ID": "count"
    }).reset_index()
    fig_actor = px.scatter(actor, x="Incident ID", y="Total affected", size="Total affected",
                           text="Actor type", color="Actor type", title="🧠 Personal Insight: Attacker Persona Analysis",
                           template="plotly_dark")
    fig_actor.update_traces(textposition='top center')
    fig_actor.update_layout(title_x=0.5)

    top_country = heatdata.sort_values(by="count", ascending=False).iloc[0]["Country"]
    narration = f"🧠 Personal Insight: {top_country} currently ranks highest in reported incidents."

    return fig_sb, fig_tree, fig_map, fig_trend, fig_anim, fig_actor, narration

if __name__ == "__main__":
    app.run_server(debug=True)