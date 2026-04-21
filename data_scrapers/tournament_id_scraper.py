import re
import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    )
}

# PGA Tour tournament URL patterns usually contain a tournament "past results id" like R2023464
# Example: https://www.pgatour.com/tournaments/2023/fortinet-championship/R2023464/past-results
TOURNEY_URL_RE = re.compile(
    r"^https?://www\.pgatour\.com/tournaments/(?P<year>\d{4})/(?P<slug>[^/]+)/(?P<tournament_id>[A-Z]\d+)/?.*$"
)

def fetch_text(url: str, retries: int = 3, backoff: float = 1.7) -> str:
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(backoff ** attempt)
            else:
                raise last

def parse_sitemap(xml_text: str):
    
    root = ET.fromstring(xml_text)

    # namespace handling (common in sitemaps)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    if root.tag.endswith("sitemapindex"):
        entries = []
        for sm in root.findall(f"{ns}sitemap"):
            loc = sm.findtext(f"{ns}loc")
            lastmod = sm.findtext(f"{ns}lastmod")
            if loc:
                entries.append({"loc": loc, "lastmod": lastmod})
        return "sitemapindex", entries

    if root.tag.endswith("urlset"):
        entries = []
        for u in root.findall(f"{ns}url"):
            loc = u.findtext(f"{ns}loc")
            lastmod = u.findtext(f"{ns}lastmod")
            if loc:
                entries.append({"loc": loc, "lastmod": lastmod})
        return "urlset", entries

    return "unknown", []

def collect_all_sitemap_urls(start_url: str, sleep: float = 0.2, max_sitemaps: int = 5000) -> pd.DataFrame:
    
    to_visit = [start_url]
    visited = set()
    rows = []

    while to_visit:
        sm_url = to_visit.pop()
        if sm_url in visited:
            continue
        visited.add(sm_url)

        if len(visited) > max_sitemaps:
            raise RuntimeError(f"Exceeded max_sitemaps={max_sitemaps}. Something is looping.")

        xml_text = fetch_text(sm_url)
        kind, entries = parse_sitemap(xml_text)

        if kind == "sitemapindex":
            # enqueue children
            for e in entries:
                to_visit.append(e["loc"])
        elif kind == "urlset":
            for e in entries:
                rows.append({
                    "url": e["loc"],
                    "lastmod": e.get("lastmod"),
                    "source_sitemap": sm_url
                })
        else:
            # ignore unknown
            pass

        time.sleep(sleep)

    return pd.DataFrame(rows)

def enrich_tournament_url_fields(df_urls: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts year/slug/tournament_id (like R2023464) from URLs where possible.
    """
    years, slugs, tids = [], [], []
    for u in df_urls["url"].astype(str):
        m = TOURNEY_URL_RE.match(u)
        if m:
            years.append(int(m.group("year")))
            slugs.append(m.group("slug"))
            tids.append(m.group("tournament_id"))
        else:
            years.append(None)
            slugs.append(None)
            tids.append(None)

    out = df_urls.copy()
    out["year"] = years
    out["slug"] = slugs
    out["tournament_past_results_id"] = tids
    return out

sitemap_url = "https://www.pgatour.com/tournament_sitemap.xml"

df_urls = collect_all_sitemap_urls(sitemap_url)
df_tournaments = enrich_tournament_url_fields(df_urls)

df_tournaments