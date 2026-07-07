# CFA Stress Testing Scenario Analysis Engine

A compact Python stress testing engine for portfolio scenario analysis. The script applies predefined shocks to a multi-asset portfolio, calculates scenario-level returns and P&L, breaks out asset-level contributions, and generates a browser dashboard with charts.

## What it does

- Calculates portfolio return and P&L for each stress scenario.
- Identifies the worst scenario before formatting results for display.
- Exports formatted scenario results to CSV.
- Generates SVG charts without requiring a charting library.
- Builds an HTML dashboard and opens it automatically when the script runs.

## Portfolio and scenarios

The current example portfolio is allocated across:

- AAPL
- MSFT
- JPM
- GLD
- SPY

Included scenarios:

- Equity Crash
- Banking Stress
- Tech Selloff
- Gold Rally / Risk Off
- Broad Market Correction

You can edit the `weights` and `scenarios` dictionaries in `stress_test.py` to test different portfolios or macro assumptions.

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the environment with:

```bash
.venv\Scripts\activate
```

## Run

```bash
python stress_test.py
```

After running, the script creates an `outputs/` folder containing:

- `scenario_results.csv`
- `dashboard.html`
- `scenario_pnl.svg`
- `portfolio_returns.svg`
- `asset_contributions.svg`
- `shock_matrix.svg`

The dashboard should open automatically in your default browser. If it does not, open `outputs/dashboard.html` manually.

## Notes

This project is designed as a CFA-style practical project: the scenario shocks are illustrative, not investment advice or a market forecast. For real-world use, stress assumptions should be linked to a documented risk framework, historical events, or forward-looking macro views.
