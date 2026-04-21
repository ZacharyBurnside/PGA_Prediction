import time
import requests
import pandas as pd
import os 

GQL_URL = "https://orchestrator.pgatour.com/graphql"
HEADERS = {"User-Agent": "Mozilla/5.0",
           "X-Api-Key" : "da2-gsrx5bibzbb4njvhl7t37wqyl4"}

PAYLOAD_TEMPLATE = {
    "operationName": "StatDetails",
    "query": """query StatDetails($tourCode: TourCode!, $statId: String!, $year: Int, $eventQuery: StatDetailEventQuery) {
      statDetails(tourCode: $tourCode statId: $statId year: $year eventQuery: $eventQuery) {
        tourCode year displaySeason statId statType statTitle tourAvg lastProcessed statHeaders
        rows {
          ... on StatDetailsPlayer {
            playerId playerName country rank rankDiff rankChangeTendency
            stats { statName statValue color }
          }
          ... on StatDetailTourAvg {
            displayName value
          }
        }
      }
    }""",
    "variables": {"tourCode": "R", "statId": "120", "year": 2024, "eventQuery": None},
}

def fetch_pgatour_stat_df(stat_id: str, year: int, tour_code: str = "R", tournament_id: str = None) -> pd.DataFrame:
    headers = dict(HEADERS)
    x_api_key = os.getenv("PGATOUR_X_API_KEY")  # set this if needed
    if x_api_key:
        headers["x-api-key"] = x_api_key

    payload = dict(PAYLOAD_TEMPLATE)
    payload["variables"] = {
        "tourCode": tour_code,
        "statId": str(stat_id),
        "year": int(year),  # StatDetails uses YYYY (not YYYY0)
        "eventQuery": ({"tournamentId": tournament_id} if tournament_id else None),
    }

    r = requests.post(GQL_URL, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    j = r.json()

    sd = (j.get("data") or {}).get("statDetails")
    if not sd:
        return pd.DataFrame()

    rows = []
    for row in sd.get("rows") or []:
        # skip the tour average row (it doesn't have playerId)
        if not row.get("playerId"):
            continue

        stat_map = {s.get("statName"): s.get("statValue") for s in (row.get("stats") or [])}
        rows.append({
            "year": year,
            "stat_id": str(stat_id),
            "stat_title": sd.get("statTitle"),
            "tour_code": tour_code,
            "tournament_id": tournament_id,
            "player_id": row.get("playerId"),
            "player_name": row.get("playerName"),
            "country": row.get("country"),
            "rank": row.get("rank"),
            **stat_map,
        })

    return pd.DataFrame(rows)

def fetch_stat_details_2010_2025(stat_id: str, tournament_id: str = None, sleep: float = 0.2) -> pd.DataFrame:
    """
    Loop StatDetails from 2010–2025 and return one DataFrame.
    Uses YYYY (not YYYY0).
    """
    dfs = []

    for year in range(2010, 2026):
        print(f"Fetching stat_id={stat_id}, year={year}, tournament_id={tournament_id}")

        try:
            df = fetch_pgatour_stat_df(
                stat_id=stat_id,
                year=year,
                tournament_id=tournament_id
            )
            if not df.empty:
                dfs.append(df)
        except Exception as e:
            print(f"  failed for year={year}: {e}")

        time.sleep(sleep)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

df = fetch_stat_details_2010_2025(stat_id="120")

df
