# PoliTracker AU

A basic Australian federal politician tracker that scrapes public sources (APH Register of Members' Interests and Hansard), stores data in SQLite, and flags potential investment/policy correlations.

## Features
- Scrape disclosures from APH Register PDFs using PyPDF2.
- Scrape Hansard pages for policy/vote references.
- Weekly automated pipeline with APScheduler.
- Simple correlation logic for potential gains.
- Public-facing site with no login.
- Prominent legal/ethical disclaimer on every page.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FLASK_APP=app.py
flask init-db
flask fetch-politicians
flask seed-politicians
flask run
```

## Scheduled Jobs
By default, the scheduler runs weekly in-process. You can disable it with:

```bash
export SCHEDULER_ENABLED=0
```

To run the pipeline manually:

```bash
flask run-scrape-once
```

## Data Sources
- APH Register of Members' Interests (House and Senate)
- APH Hansard
- Free market data APIs (Yahoo Finance or Alpha Vantage)

You can override the APH URLs and API key via environment variables:

- `APH_REGISTER_HOUSE_PDF`
- `APH_REGISTER_SENATE_PDF`
- `APH_HANSARD_BASE`
- `ALPHA_VANTAGE_API_KEY`

## Deployment Notes
- For Heroku, use `Procfile` and set environment variables.
- For AWS, run `gunicorn wsgi:app` and a separate scheduler process if desired.
- Logs are written to `logs/scrape.log`.

## CSV Format for Politicians
`data/politicians.csv` should include:

```
name,party,electorate,chamber,aph_id
```

Use `flask fetch-politicians` to download the current list of Members and Senators.
