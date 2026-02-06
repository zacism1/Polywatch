# Polywatch

A public, static website that helps explore Australian federal politicians, their disclosures, and possible policy-investment correlations using public records.

## Static Site (GitHub Pages)
The live site can be hosted for free using GitHub Pages from the `docs/` folder.

### Build the data files
Update `data/politicians.csv`, then generate the JSON used by the static site:

```bash
python scripts/build_static.py
```

This writes:
- `docs/data/politicians.json`
- `docs/data/profiles.json`

These files are what the static site reads. Commit them to keep the site fully static.

## Automatic Updates (GitHub Actions)
This repo includes a scheduled workflow that:
- Fetches the current APH parliamentarian list
- Rebuilds the static JSON data
- Commits changes back to the repo

Workflow file: `.github/workflows/update-data.yml`

You can also run it manually from the GitHub Actions tab.

## Optional Scraper (Local)
If you want to scrape live data and generate the CSV/JSON files automatically, you can still use the Flask app in `app/`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FLASK_APP=app.py
flask init-db
flask fetch-politicians
flask seed-politicians
```

## Disclaimer
This tool analyzes public data from official sources for transparency purposes only. It does not imply wrongdoing, corruption, or any accusations. Data may contain errors; verify independently. Complies with fair dealing under Australian copyright law.
