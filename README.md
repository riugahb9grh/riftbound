# Riftbound Movers

A mobile-first installable web app that ranks Riftbound cards by TCGplayer market-price movement over a selectable period.

## What it does

- Sort by biggest percentage gain/loss or dollar gain/loss
- Choose 24 hours, 3, 7, 14, 30, or 90 days
- Filter printings and search card names
- Tap any result to open TCGplayer
- Install to an iPhone or Android home screen
- Refresh prices automatically every six hours using GitHub Actions
- Build its own price history from recurring snapshots

## Deploy free with GitHub Pages

1. Create a new public GitHub repository.
2. Upload every file and folder in this project.
3. In the repository, open **Settings → Pages**.
4. Under **Build and deployment**, choose **Deploy from a branch**.
5. Select the `main` branch and `/ (root)`, then save.
6. Open **Actions → Update Riftbound prices → Run workflow** once.
7. Wait for the workflow to commit real data, then open the Pages URL.

The scheduled updater runs every six hours. GitHub Pages republishes after each commit.

## Add it to your phone

### iPhone
Open the Pages URL in Safari, tap **Share**, then **Add to Home Screen**.

### Android
Open the URL in Chrome and choose **Install app** or **Add to Home screen**.

## Important data behavior

TCGCSV supplies current TCGplayer catalog and market-price snapshots, but not archived prices. This repository creates history only after the updater begins running. Therefore:

- 24-hour movement becomes meaningful after roughly one day.
- 7-day movement becomes meaningful after roughly seven days.
- 30-day movement becomes meaningful after roughly thirty days.

For windows older than the available history, the app compares against the oldest snapshot and displays the actual elapsed window.

## Run locally

```bash
python scripts/update_prices.py
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Data source and responsibility

The updater uses the public TCGCSV interface, which describes itself as a public entry point for TCGplayer catalog and price data. Review the applicable TCGplayer and TCGCSV terms before publishing or commercializing the app. This project is intended as a personal dashboard, not an official TCGplayer product.
