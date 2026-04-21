import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from dash import dash_table
import re
import unicodedata

# ----------------------------
# LOAD DATA/NORMALIZE DATA - change to database later
# ----------------------------
df = pd.read_csv("/home/zburnside/pga_prediction_model/historical_tournament_results.csv")
sg = pd.read_csv("/home/zburnside/pga_prediction_model/sg_tee_to_green.csv")

def normalize_tournament_name(name: str) -> str:
    if name is None:
        return ""

    s = str(name)

    # unicode normalize + fix common smart punctuation
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'")  # curly apostrophes
    s = s.replace("\u2013", "-").replace("\u2014", "-")  # en/em dash

    # remove trailing (YYYY) like "(2020)" "(2021)"
    s = re.sub(r"\s*\(\s*\d{4}\s*\)\s*$", "", s)

    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # lowercase
    s = s.lower()

    # drop leading "the " (critical for Masters)
    s = re.sub(r"^the\s+", "", s)

    return s

# ---------------------------- WEIGHTS ----------------------------
WEIGHT_PROFILES = {
    "birdie_fest":   dict(finish=0.35, cut=0.15, early=0.35, sunday=0.15),
    "positional":    dict(finish=0.45, cut=0.25, early=0.20, sunday=0.10),
    "grinder":       dict(finish=0.45, cut=0.30, early=0.10, sunday=0.15),
    "major":         dict(finish=0.40, cut=0.30, early=0.10, sunday=0.20),
    "bomber":        dict(finish=0.40, cut=0.20, early=0.20, sunday=0.20),
    "volatile":      dict(finish=0.30, cut=0.20, early=0.30, sunday=0.20),
}

DEFAULT_WEIGHTS = dict(finish=0.45, cut=0.25, early=0.20, sunday=0.10)

TOURNAMENT_WEIGHTS = {
    # BIRDIE FESTS
    "Sony Open in Hawaii": WEIGHT_PROFILES["birdie_fest"],
    "The American Express": WEIGHT_PROFILES["birdie_fest"],
    "John Deere Classic": WEIGHT_PROFILES["birdie_fest"],
    "Rocket Mortgage Classic": WEIGHT_PROFILES["birdie_fest"],
    "3M Open": WEIGHT_PROFILES["birdie_fest"],
    "Shriners Children’s Open": WEIGHT_PROFILES["birdie_fest"],
    "Sanderson Farms Championship": WEIGHT_PROFILES["birdie_fest"],
    "Wyndham Championship": WEIGHT_PROFILES["birdie_fest"],
    "Barracuda Championship": WEIGHT_PROFILES["birdie_fest"],

    # POSITIONAL / ACCURACY
    "RBC Heritage": WEIGHT_PROFILES["positional"],
    "Charles Schwab Challenge": WEIGHT_PROFILES["positional"],
    "Valspar Championship": WEIGHT_PROFILES["positional"],
    "Zurich Classic of New Orleans": WEIGHT_PROFILES["positional"],
    "Travelers Championship": WEIGHT_PROFILES["positional"],
    "FedEx St. Jude Championship": WEIGHT_PROFILES["positional"],
    "BMW Championship": WEIGHT_PROFILES["positional"],

    # GRINDERS
    "Arnold Palmer Invitational presented by Mastercard": WEIGHT_PROFILES["grinder"],
    "Genesis Invitational": WEIGHT_PROFILES["grinder"],
    "Memorial Tournament presented by Workday": WEIGHT_PROFILES["grinder"],
    "Farmers Insurance Open": WEIGHT_PROFILES["grinder"],
    "Mexico Open at Vidanta": WEIGHT_PROFILES["grinder"],
    "Puerto Rico Open": WEIGHT_PROFILES["grinder"],

    # BOMBER
    "The Players Championship": WEIGHT_PROFILES["bomber"],
    "Wells Fargo Championship": WEIGHT_PROFILES["bomber"],
    "Genesis Scottish Open": WEIGHT_PROFILES["bomber"],
    "Zozo Championship": WEIGHT_PROFILES["bomber"],

    # VOLATILE
    "Open Championship": WEIGHT_PROFILES["volatile"],
    "RSM Classic": WEIGHT_PROFILES["volatile"],
    "Butterfield Bermuda Championship": WEIGHT_PROFILES["volatile"],

    # MAJORS
    "Masters Tournament": WEIGHT_PROFILES["major"],
    "PGA Championship": WEIGHT_PROFILES["major"],
    "U.S. Open": WEIGHT_PROFILES["major"],

    # PLAYOFF / ELITE
    "Tour Championship": WEIGHT_PROFILES["major"],
    "FedEx St. Jude Championship": WEIGHT_PROFILES["major"],
    "BMW Championship": WEIGHT_PROFILES["major"],
}

TOURNAMENT_WEIGHTS_CANON = {
    normalize_tournament_name(k): v for k, v in TOURNAMENT_WEIGHTS.items()
}


PROFILE_DEFS = {
    "birdie_fest": [
        "Low-scoring, wedge + putting emphasis",
        "Fast starts matter more (R1/R2)",
        "Cut-rate matters less (usually easier cuts)"
    ],
    "positional": [
        "Accuracy/positioning > raw distance",
        "Repeatable course skill shows up over time",
        "Balanced weighting across signals"
    ],
    "grinder": [
        "Hard scoring environment",
        "Cut survival + avoiding blow-ups matter",
        "Closing performance matters more"
    ],
    "major": [
        "Strong field + difficult setup",
        "Cut-rate + Sunday pressure matter more",
        "Less weight on early spikes"
    ],
    "bomber": [
        "Distance advantage / long approach environment",
        "Less reliant on early scoring",
        "More separation on elite skill"
    ],
    "volatile": [
        "Wind/links/chaos increases variance",
        "Emphasize Sunday + early volatility handling",
        "Less reliance on historical finish alone"
    ],
}

WEIGHTS_TO_PROFILE = {
    tuple(sorted(v.items())): k for k, v in WEIGHT_PROFILES.items()
}

# HELPER FUNCTIONS and NORMALIZATION

for c in ["season_year", "playerId"]:
    sg[c] = pd.to_numeric(sg[c], errors="coerce")

for c in ["avg", "sg_ott", "sg_apr", "sg_arg", "measured_rounds"]:
    if c in sg.columns:
        sg[c] = pd.to_numeric(sg[c], errors="coerce")

if "tournament_norm" not in df.columns:
    df["tournament_norm"] = df["tournament_key"].map(normalize_tournament_name)
else:
    df["tournament_norm"] = df["tournament_norm"].map(normalize_tournament_name)

if "tournament_canon" in df.columns:
    df["tournament_canon"] = df["tournament_canon"].map(normalize_tournament_name)
else:
    # canon = normalized base name (best for grouping course history)
    df["tournament_canon"] = df["tournament_key"].map(normalize_tournament_name)

# sg: make sure SG is keyed the same way so merges work
if "tournament_norm" not in sg.columns:
    sg["tournament_norm"] = sg["tournament_name"].map(normalize_tournament_name)
else:
    sg["tournament_norm"] = sg["tournament_norm"].map(normalize_tournament_name)

if "tournament_canon" in sg.columns:
    sg["tournament_canon"] = sg["tournament_canon"].map(normalize_tournament_name)
else:
    sg["tournament_canon"] = sg["tournament_name"].map(normalize_tournament_name)


def get_tournament_profile_name(tournament_name: str) -> str:
    tcanon = normalize_tournament_name(tournament_name)
    w = TOURNAMENT_WEIGHTS_CANON.get(tcanon)
    if not w:
        return "default"
    return WEIGHTS_TO_PROFILE.get(tuple(sorted(w.items())), "custom")

def format_profile_block(profile_name: str) -> str:
    if profile_name == "default":
        defs = ["Uses default weights (no tournament override)."]
    else:
        defs = PROFILE_DEFS.get(profile_name, ["No definition available."])

    lines = [f"Profile: {profile_name}", ""]
    lines += [f"• {d}" for d in defs]
    return "\n".join(lines)

def format_weights_dict_line(w: dict) -> str:
    # compact dict-like string
    return f"{{'finish': {w['finish']}, 'cut': {w['cut']}, 'early': {w['early']}, 'sunday': {w['sunday']}}}"

def format_profile_defs(profile_name: str) -> str:
    defs = PROFILE_DEFS.get(profile_name, ["Uses default weights (no override)."])
    return "\n".join([f"• {d}" for d in defs])

# ----------------------------
# CORE FUNCTION
# ----------------------------
def tournament_sg_profile(sg_df: pd.DataFrame, tournament_name: str, lookback_years: int = 8) -> pd.DataFrame:
    tcanon = normalize_tournament_name(tournament_name)
    sdf = sg_df[sg_df["tournament_canon"].eq(tcanon)].copy()
    if sdf.empty:
        return pd.DataFrame(columns=["playerId", "sg_t2g_course_avg", "sg_t2g_course_recent", "sg_measured_rounds"])

    max_year = int(sdf["season_year"].max())
    sdf = sdf[sdf["season_year"] >= (max_year - lookback_years + 1)]

    g = sdf.groupby("playerId").agg(
        sg_t2g_course_avg=("avg", "mean"),
        sg_t2g_course_recent=("avg", lambda x: x.tail(3).mean()),   # last ~3 appearances
        sg_measured_rounds=("measured_rounds", "sum"),
        playerName=("playerName", "last"),
    ).reset_index()

    return g

def tournament_course_history(
    df: pd.DataFrame,
    tournament_name: str,
    weights_map=None,
    default_weights=None,
    min_starts: int = 2
):
    weights_map = weights_map or TOURNAMENT_WEIGHTS_CANON
    w = (default_weights or DEFAULT_WEIGHTS).copy()

    tcanon = normalize_tournament_name(tournament_name)

    # apply tournament-specific weights by CANON key
    w.update(weights_map.get(tcanon, {}))

    # filter on CANON column
    tdf = df[df["tournament_canon"].eq(tcanon)].copy()
    if tdf.empty:
        return pd.DataFrame(), w

    pos_raw = tdf["position"].astype(str).str.upper().str.strip()
    tdf["finish_pos"] = pos_raw.str.replace(r"[^0-9]", "", regex=True).replace("", pd.NA)
    tdf["finish_pos"] = pd.to_numeric(tdf["finish_pos"], errors="coerce")
    tdf["made_cut"] = ~pos_raw.isin(["CUT", "WD", "DQ", "DNS"])

    for c in ["total", "r1_score", "r2_score", "r3_score", "r4_score"]:
        if c in tdf.columns:
            tdf[c] = pd.to_numeric(tdf[c], errors="coerce")

    player_hist = (
        tdf.groupby("playerId", dropna=False)
        .agg(
            playerName=("playerName", "last"),
            starts=("position", "count"),
            cut_rate=("made_cut", "mean"),
            avg_finish=("finish_pos", "mean"),
            avg_r1=("r1_score", "mean"),
            avg_r2=("r2_score", "mean"),
            avg_r4=("r4_score", "mean"),
        )
        .reset_index()
    )

    player_hist["early_round_avg"] = player_hist[["avg_r1", "avg_r2"]].mean(axis=1)
    player_hist["sunday_delta"] = player_hist["avg_r4"] - player_hist["avg_r1"]

    player_hist["course_fit_score"] = (
        (100 - player_hist["avg_finish"]) * w["finish"]
        + (player_hist["cut_rate"] * 100) * w["cut"]
        + (70 - player_hist["early_round_avg"]) * w["early"]
        + (5 - player_hist["sunday_delta"]) * w["sunday"]
    )

    out = (
        player_hist[player_hist["starts"] >= min_starts]
        .sort_values("course_fit_score", ascending=False)
        .reset_index(drop=True)
    )
    return out, w


# ----------------------------
# DASH APP
# ----------------------------

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

tournament_options = sorted(df["tournament_canon"].dropna().unique().tolist())

app.layout = dbc.Container(
    [
        # --- HERO / HEADER ---
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div(
                                    [
                                        html.H2(
                                            "PGA Course-Fit Rankings",
                                            className="mb-1",
                                            style={"fontWeight": 800, "letterSpacing": "-0.5px"},
                                        ),
                                        html.Div(
                                            "Tournament-specific rankings built from historical finishes, cut-rate, fast starts, and Sunday performance.",
                                            className="text-muted",
                                            style={"fontSize": "0.95rem"},
                                        ),
                                    ],
                                    style={"padding": "6px 2px"},
                                ),
                            ]
                        ),
                        className="shadow-sm border-0",
                    ),
                    md=12,
                ),
            ],
            className="mt-3",
        ),

        # --- CONTROLS BAR ---
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                html.Label("Tournament", className="text-muted", style={"fontSize": "0.85rem"}),
                                                dcc.Dropdown(
                                                    id="tournament_dd",
                                                    options=[{"label": t, "value": t} for t in tournament_options],
                                                    value=tournament_options[0] if tournament_options else None,
                                                    clearable=False,
                                                    placeholder="Select a tournament...",
                                                ),
                                            ],
                                            md=7,
                                        ),
                                        dbc.Col(
                                            [
                                                html.Label("Min starts", className="text-muted", style={"fontSize": "0.85rem"}),
                                                dcc.Slider(
                                                    id="min_starts",
                                                    min=1, max=10, step=1,
                                                    value=2,
                                                    marks={i: str(i) for i in range(1, 11)},
                                                    tooltip={"placement": "bottom", "always_visible": False},
                                                ),
                                            ],
                                            md=5,
                                        ),
                                    ],
                                    className="g-3",
                                ),
                            ]
                        ),
                        className="mt-3 shadow-sm border-0",
                    ),
                    md=12,
                ),
            ]
        ),

        # --- KPI CARDS ---
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("Players (after filter)", className="text-muted", style={"fontSize": "0.85rem"}),
                                html.H3(id="kpi_players", className="mb-0", style={"fontWeight": 800}),
                            ]
                        ),
                        className="mt-3 shadow-sm border-0",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("Top course-fit score", className="text-muted", style={"fontSize": "0.85rem"}),
                                html.H3(id="kpi_top_score", className="mb-0", style={"fontWeight": 800}),
                            ]
                        ),
                        className="mt-3 shadow-sm border-0",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("Top player", className="text-muted", style={"fontSize": "0.85rem"}),
                                html.H5(id="kpi_top_player", className="mb-0", style={"fontWeight": 800}),
                            ]
                        ),
                        className="mt-3 shadow-sm border-0",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("Weights profile", className="text-muted", style={"fontSize": "0.85rem"}),
                                html.H6(id="kpi_weights_profile", className="mb-0"),
                            ]
                        ),
                        className="mt-3 shadow-sm border-0",
                    ),
                    md=3,
                ),
            ],
            className="g-3",
        ),

        # --- MAIN CONTENT: TABLE + WEIGHTS PANEL ---
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            html.Div(
                                                [
                                                    html.H5("Ranked Players", className="mb-1", style={"fontWeight": 800}),
                                                    html.Div(
                                                        "Sort, filter, and export. Course-fit score is computed using the tournament weights shown at right.",
                                                        className="text-muted",
                                                        style={"fontSize": "0.9rem"},
                                                    ),
                                                ]
                                            ),
                                            md=8,
                                        ),
                                        dbc.Col(
                                            dbc.Button(
                                                "Export CSV (current view)",
                                                id="btn_export",
                                                color="primary",
                                                className="float-md-end mt-2 mt-md-0",
                                                n_clicks=0,
                                            ),
                                            md=4,
                                        ),
                                    ],
                                    className="mb-3",
                                ),

                                dcc.Download(id="download_csv"),

                                dash_table.DataTable(
                                    id="rank_table",
                                    page_size=25,
                                    sort_action="native",
                                    filter_action="native",
                                    style_table={"overflowX": "auto"},
                                    style_cell={
                                        "fontFamily": "Arial",
                                        "fontSize": 13,
                                        "padding": "8px",
                                        "whiteSpace": "nowrap",
                                        "maxWidth": "260px",
                                        "overflow": "hidden",
                                        "textOverflow": "ellipsis",
                                    },
                                    style_header={
                                        "fontWeight": "bold",
                                        "border": "0px",
                                    },
                                    style_data_conditional=[
                                        # subtle zebra striping
                                        {"if": {"row_index": "odd"}, "filter_query": "{playerName} != ''", "opacity": 0.98},
                                        # highlight top 10
                                        {"if": {"row_index": 0}, "fontWeight": "bold"},
                                        {"if": {"row_index": 1}, "fontWeight": "bold"},
                                        {"if": {"row_index": 2}, "fontWeight": "bold"},
                                    ],
                                    tooltip_delay=0,
                                    tooltip_duration=None,
                                ),
                            ]
                        ),
                        className="mt-3 shadow-sm border-0",
                    ),
                    md=8,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div(
                                    [
                                        html.H5("Weights Used", className="mb-2", style={"fontWeight": 800}),
                                        html.Div(
                                            "These weights control how the course-fit score is computed.",
                                            className="text-muted",
                                            style={"fontSize": "0.9rem"},
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                dbc.Alert(
                                    [
                                        html.Div(id="weights_badge"),
                                    ],
                                    color="info",
                                    className="py-2",
                                ),
                                html.Pre(
                                    id="weights_box",
                                    style={
                                        "marginBottom": 0,
                                        "padding": "12px",
                                        "borderRadius": "10px",
                                        "backgroundColor": "#f8f9fa",
                                        "border": "1px solid #e9ecef",
                                        "fontSize": "0.9rem",
                                    },
                                ),
                                html.Hr(className="my-3"),
                                html.Div(
                                    [
                                        html.H6("How to Read the Weight", className="mb-1", style={"fontWeight": 700}),
                                        html.Ul(
                                            [
                                                html.Li("finish: historical finishing position signal"),
                                                html.Li("cut: course cut survival rate"),
                                                html.Li("early: R1/R2 fast-start bias"),
                                                html.Li("sunday: closing / pressure bias"),
                                            ],
                                            className="text-muted",
                                            style={"fontSize": "0.9rem"},
                                        ),
                                    ]
                                ),
                            ]
                        ),
                        className="mt-3 shadow-sm border-0",
                    ),
                    md=4,
                ),
            ],
            className="g-3",
        ),
        # --- FOR DUMMIES / EXPLANATION ---
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H5(
                                    "For Dummies (AI Generated)",
                                    className="mb-2",
                                    style={"fontWeight": 800},
                                ),
                                html.P(
                                    "The course-fit score ranks players based on how closely their historical performance "
                                    "matches the demands of the selected tournament. Each event is assigned a weight profile "
                                    "that emphasizes factors such as finishing position, cut consistency, fast starts, and "
                                    "Sunday performance. Player results at the same tournament and comparable courses are "
                                    "normalized and combined using these weights to produce a single score that reflects how "
                                    "well a player’s game fits this course. This is called final_score. This is a simple combination"
                                    "of course_fit_score (players historical course performaance) with sg_t2g_course_avg (Avg of "
                                    "SG Putting, Approach, Off Tee). ",
                                    className="text-muted",
                                    style={"fontSize": "0.95rem", "marginBottom": 0},
                                ),
                            ]
                        ),
                        className="mt-3 shadow-sm border-0",
                    ),
                    md=12,
                ),
            ]
        ),

        # --- FOOTER ---
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        "Tip: use filters like \"starts >= 4\" and sort by course_fit_score to find reliable course horses.",
                        className="text-muted",
                        style={"fontSize": "0.9rem", "padding": "18px 4px"},
                    ),
                    md=12,
                )
            ]
        ),
    ],
    fluid=True,
    style={"maxWidth": "1400px"},
)

@app.callback(
    Output("rank_table", "data"),
    Output("rank_table", "columns"),
    Output("weights_box", "children"),
    Output("kpi_players", "children"),
    Output("kpi_top_score", "children"),
    Output("kpi_top_player", "children"),
    Output("kpi_weights_profile", "children"),
    Output("weights_badge", "children"),
    Input("tournament_dd", "value"),
    Input("min_starts", "value"),
)

def update_table(tournament_name, min_starts):
    if not tournament_name:
        return [], [], "", "0", "-", "-", "-", ""

    tkey = str(tournament_name).strip()  # normalized already; just be safe

    out, w = tournament_course_history(
        df=df,
        tournament_name=tkey,
        weights_map=TOURNAMENT_WEIGHTS_CANON,
        default_weights=DEFAULT_WEIGHTS,
        min_starts=int(min_starts or 2),
    )


    if out.empty:
        return [], [], "", "0", "-", "-", "-", ""

    # ---- SG:T2G course history ----
    sg_prof = tournament_sg_profile(sg, tkey, lookback_years=8)

    # ensure join keys match dtype
    out["playerId"] = pd.to_numeric(out["playerId"], errors="coerce")
    sg_prof["playerId"] = pd.to_numeric(sg_prof["playerId"], errors="coerce")

    view = out.merge(
        sg_prof[["playerId","sg_t2g_course_avg","sg_t2g_course_recent","sg_measured_rounds"]],
        on="playerId",
        how="left"
    )


    # Normalize SG into 0–100 scale
    view["sg_score"] = (
        (pd.to_numeric(view["sg_t2g_course_avg"], errors="coerce")
         .clip(-2.5, 2.5) + 2.5) / 5.0 * 100
    )

    # Blend: 70% course history / 30% SG:T2G
    course_w, sg_w = 0.7, 0.3
    view["final_score"] = view["course_fit_score"] * course_w + view["sg_score"] * sg_w

    # ---- display cols ----
    cols = [
        "playerName","final_score","course_fit_score","sg_t2g_course_avg",
        "starts","cut_rate","avg_finish","early_round_avg","sunday_delta"
    ]
    cols = [c for c in cols if c in view.columns]
    view = view[cols].copy()

    for c in view.columns:
        if c != "playerName":
            view[c] = pd.to_numeric(view[c], errors="coerce").round(3)

    view = view.sort_values("final_score", ascending=False)

    data = view.to_dict("records")
    columns = [{"name": c, "id": c} for c in view.columns]

    n_players = len(view)
    top_player = str(view.iloc[0]["playerName"]) if n_players else "-"
    top_score = f"{view.iloc[0]['final_score']:.3f}" if n_players else "-"

    profile_name = get_tournament_profile_name(tkey)  # 'birdie_fest', 'positional', etc.
    weights_profile = profile_name
    badge = format_weights_dict_line(w)
    weights_text = format_profile_defs(profile_name)

    return data, columns, weights_text, str(n_players), top_score, top_player, weights_profile, badge

@app.callback(
    Output("download_csv", "data"),
    Input("btn_export", "n_clicks"),
    State("tournament_dd", "value"),
    State("min_starts", "value"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, tournament_name, min_starts):
    if not n_clicks:
        return None

    out, _ = tournament_course_history(
        df=df,
        tournament_name=tournament_name,
        weights_map=TOURNAMENT_WEIGHTS,
        default_weights=DEFAULT_WEIGHTS,
        min_starts=int(min_starts or 2),
    )

    cols = ["playerName", "course_fit_score", "starts", "cut_rate", "avg_finish", "early_round_avg", "sunday_delta"]
    cols = [c for c in cols if c in out.columns]
    view = out[cols].copy()

    for c in ["course_fit_score", "cut_rate", "avg_finish", "early_round_avg", "sunday_delta"]:
        if c in view.columns:
            view[c] = pd.to_numeric(view[c], errors="coerce").round(3)

    fname = f"{tournament_name.replace(' ', '_').replace('/', '-')}_course_fit.csv"
    return dcc.send_data_frame(view.to_csv, fname, index=False)

if __name__ == "__main__":
    app.run_server(debug=True)

