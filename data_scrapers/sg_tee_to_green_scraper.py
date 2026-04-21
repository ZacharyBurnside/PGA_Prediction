import re, time, requests, pandas as pd

GQL_URL = "https://orchestrator.pgatour.com/graphql"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Api-Key": "da2-gsrx5bibzbb4njvhl7t37wqyl4",
    "Content-Type": "application/json",
}

STATDETAILS_QUERY = """
query StatDetails($tourCode: TourCode!, $statId: String!, $year: Int, $eventQuery: StatDetailEventQuery) {
  statDetails(tourCode: $tourCode, statId: $statId, year: $year, eventQuery: $eventQuery) {
    statTitle
    rows {
      ... on StatDetailsPlayer {
        playerId
        playerName
        rank
        stats { statName statValue }
      }
    }
  }
}
"""

def fetch_schedule(year_start=2010, year_end=2025) -> pd.DataFrame:
    rows = []
    for y in range(year_start, year_end + 1):
        payload = requests.get(f"https://data-api.pgatour.com/schedule/R/{y}?sort=ASC", timeout=30).json()
        for t in payload.get("tournaments", []):
            rows.append({"season_year": y, "tournamentId": t.get("tournamentId"), "name": t.get("name")})
    return pd.DataFrame(rows).dropna(subset=["tournamentId"])

def _col_safe(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s

def fetch_statdetails_all_events(stat_id: str, year_start=2010, year_end=2025, sleep=0.12) -> pd.DataFrame:
    sched = fetch_schedule(year_start, year_end)
    pairs = sched[["season_year", "tournamentId", "name"]].drop_duplicates().values.tolist()

    out = []
    for season_year, tid, tname in pairs:
        variables = {
            "tourCode": "R",
            "statId": str(stat_id),
            "year": int(season_year),  # StatDetails uses normal year like 2025
            "eventQuery": {"queryType": "THROUGH_EVENT", "tournamentId": str(tid)},
        }
        resp = requests.post(GQL_URL, headers=HEADERS, json={
            "query": STATDETAILS_QUERY,
            "variables": variables,
            "operationName": "StatDetails",
        }, timeout=45).json()

        rows = resp.get("data", {}).get("statDetails", {}).get("rows", []) or []
        stat_title = resp.get("data", {}).get("statDetails", {}).get("statTitle")

        for r in rows:
            row = {
                "season_year": season_year,
                "tournamentId": tid,
                "tournament_name": tname,
                "statId": stat_id,
                "statTitle": stat_title,
                "playerId": r.get("playerId"),
                "playerName": r.get("playerName"),
                "rank": r.get("rank"),
            }
            for s in r.get("stats", []) or []:
                row[_col_safe(s.get("statName"))] = s.get("statValue")
            out.append(row)

        print(f"Done {season_year} {tid} | players={len(rows)}")
        time.sleep(sleep)

    return pd.DataFrame(out)

# Example:
df_stats = fetch_statdetails_all_events(stat_id="02674", year_start=2010, year_end=2025)
df_stats.to_csv('/home/zburnside/pga_prediction_model/sg_tee_to_green.csv')