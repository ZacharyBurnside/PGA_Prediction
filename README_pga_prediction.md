# PGA Prediction Model

A machine learning pipeline that predicts PGA Tour tournament outcomes using historical strokes gained data, player scoring trends, and tournament-specific performance. Built to power smarter picks for fantasy golf and pool games.

---

## What It Does

1. **Scrapes** historical PGA Tour data via the PGA Tour GraphQL API — player stats, strokes gained, and tournament results from 2010–2025
2. **Processes** and normalizes 15 years of tournament data across 500+ events and 1,000+ players
3. **Models** player performance using strokes gained metrics as predictive features
4. **Surfaces** picks via an interactive Dash dashboard

---

## Data Sources

| Source | What It Collects |
|---|---|
| PGA Tour GraphQL API | Player scoring stats (stat_id 120), strokes gained tee-to-green (stat_id 02674) |
| PGA Tour Schedule API | All tournament IDs and names from 2010–2025 |
| PGA Tour Sitemap | Tournament past-results IDs for historical data |
| Tournament Past Results | Final positions, scores, par-relative scores by round |

---

## Tech Stack

- **Python** — data pipeline and modeling
- **Requests** — PGA Tour GraphQL API queries
- **Pandas** — data processing and feature engineering
- **Plotly Dash** — interactive picks dashboard
- **Scikit-learn** — prediction model
- **SQLite / CSV** — data storage

---

## File Structure

```
pga_prediction_model/
├── dashboard.py                        # Dash picks dashboard
├── player_scoring_scraper.py           # Player scoring stats (2010–2025)
├── sg_tee_to_green_scraper.py          # Strokes gained tee-to-green by tournament
├── tournament_results_scraper.py       # Historical finishing positions and scores
├── tournament_id_scraper.py            # Tournament IDs via PGA Tour sitemap
├── Model_Test.ipynb                    # Model development and evaluation
├── PGA_Picker_Test.ipynb               # Pick recommendations and testing
├── historical_tournament_results.csv   # Processed tournament results (2010–2025)
├── sg_tee_to_green.csv                 # Strokes gained dataset
└── tournament_data.csv                 # Tournament metadata
```

---

## Data Pipeline

```
tournament_id_scraper.py
    → All tournament IDs from PGA Tour sitemap (2010–2025)
            ↓
tournament_results_scraper.py
    → Historical finishing positions, scores, par-relative scores
            ↓
sg_tee_to_green_scraper.py
    → Strokes gained tee-to-green per player per tournament
            ↓
player_scoring_scraper.py
    → Aggregate player scoring stats by season
            ↓
Model_Test.ipynb
    → Feature engineering, model training, evaluation
            ↓
PGA_Picker_Test.ipynb + dashboard.py
    → Pick recommendations for upcoming tournaments
```

---

## Key Features

- **15 years of data** — 2010 through 2025 PGA Tour seasons
- **Tournament normalization** — handles renamed tournaments (e.g. Safeway Open → Fortinet Championship → Procore Championship) via alias mapping
- **Strokes gained** — uses SG:Tee-to-Green as primary predictive feature, the most course-independent measure of player skill
- **Per-event granularity** — stats pulled at the tournament level, not just season averages, to capture course-fit signals

---

## Running the Scrapers

```bash
pip install requests pandas plotly dash

# Collect tournament results
python tournament_results_scraper.py

# Collect strokes gained data
python sg_tee_to_green_scraper.py

# Collect player scoring stats
python player_scoring_scraper.py

# Run dashboard
python dashboard.py
```

Then open `http://localhost:8050` to view pick recommendations.
