import requests, time, pandas as pd

GQL_URL = "https://orchestrator.pgatour.com/graphql"
HEADERS = {"User-Agent":"Mozilla/5.0",
           "X-Api-Key":"da2-gsrx5bibzbb4njvhl7t37wqyl4",
           "Content-Type":"application/json"}

QUERY = """
query TournamentPastResults($tournamentPastResultsId: ID!, $year: Int) {
  tournamentPastResults(id: $tournamentPastResultsId, year: $year) {
    players {
      position
      total
      parRelativeScore
      player { id displayName }
      rounds { score parRelativeScore }
    }
  }
}
"""

def fetch_tournament_info_historical():
    all_tournaments = []
    for year in range(2010, 2026):
        payload = requests.get(f"https://data-api.pgatour.com/schedule/R/{year}?sort=ASC", timeout=30).json()
        for t in payload.get("tournaments", []):
            t["season_year"] = year
            all_tournaments.append(t)
    return pd.DataFrame(all_tournaments)

def fetch_tournament_results_historical():
    info_df = fetch_tournament_info_historical()

    name_map = (info_df[["tournamentId", "name"]]
                .dropna().drop_duplicates("tournamentId")
                .set_index("tournamentId")["name"].to_dict())

    tids = info_df["tournamentId"].dropna().drop_duplicates().astype(str).tolist()

    rows = []
    for tid in tids:
        yr_from_id = int(tid[1:5])
        year_param = int(f"{yr_from_id}0")   # 20250

        resp = requests.post(
        GQL_URL,
        headers=HEADERS,
        json={
            "query": QUERY,
            "operationName": "TournamentPastResults",
            "variables": {"tournamentPastResultsId": tid, "year": year_param},
        },
    ).json()

        if resp.get("errors"):
            print(f"ERROR: {tid} ({yr_from_id}) -> {resp['errors'][0].get('message')}")
            continue

        players = resp.get("data", {}).get("tournamentPastResults", {}).get("players", []) or []
        tname = name_map.get(tid)

        for p in players:
            player = p.get("player") or {}
            row = {
                "tournamentId": tid,
                "season_year": yr_from_id,
                "tournament_key": tname,
                "position": p.get("position"),
                "total": p.get("total"),
                "parRelativeScore": p.get("parRelativeScore"),
                "playerId": player.get("id"),
                "playerName": player.get("displayName"),
            }
            for i, rd in enumerate(p.get("rounds") or [], 1):
                row[f"r{i}_score"] = rd.get("score")
                row[f"r{i}_par"] = rd.get("parRelativeScore")
            rows.append(row)

        print(f"Done: {tid} ({yr_from_id}) {tname} players={len(players)}")
        time.sleep(0.15)

    return pd.DataFrame(rows)

df = fetch_tournament_results_historical()

import re

def normalize_tournament_name(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)                 # collapse whitespace
    s = re.sub(r"\(\d{4}\)$", "", s).strip()   # remove trailing "(2020)"
    s = s.lower()
    return s


ALIAS = {
    # PLAYERS
    "the players championship": [
        "the players championship", "the players"
    ],

    # SENTRY TOC
    "sentry tournament of champions": [
        "hyundai tournament of champions", "sbs tournament of champions",
        "sentry tournament of champions", "the sentry", "the sentry tournament of champions"
    ],

    # GENESIS @ riviera
    "the genesis invitational": [
        "northern trust open", "genesis open", "the genesis invitational"
    ],

    # MEMORIAL
    "the memorial tournament": [
        "the memorial tournament presented by nationwide insurance",
        "the memorial tournament presented by nationwide",
        "the memorial tournament presented by workday",
        "the memorial tournament"
    ],

    # TOUR CHAMP
    "tour championship": [
        "tour championship", "tour championship by coca-cola", "tour championship by coca cola"
    ],

    # CJ CUP
    "the cj cup": [
        "the cj cup @ nine bridges", "the cj cup @ shadow creek",
        "the cj cup @ summit", "the cj cup in south carolina",
        "the cj cup byron nelson", "the cj cup"
    ],

    # FORTINET / SAFEWAY
    "fortinet championship": [
        "safeway open", "fortinet championship", "procore championship"
    ],
}

ALIAS_REV = {}
for canon, variants in ALIAS.items():
    for v in variants:
        ALIAS_REV[normalize_tournament_name(v)] = canon


df["tournament_norm"] = df["tournament_key"].apply(normalize_tournament_name)
df["tournament_canon"] = df["tournament_norm"].map(ALIAS_REV).fillna(df["tournament_norm"])


df.to_csv('/home/zburnside/pga_prediction_model/historical_tournament_results.csv')
