from pathlib import Path
import platform
import subprocess
import webbrowser
from xml.sax.saxutils import escape

import pandas


PORTFOLIO_VALUE = 100000
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

weights = {
    "AAPL": 0.25,
    "MSFT": 0.25,
    "JPM": 0.20,
    "GLD": 0.15,
    "SPY": 0.15,
}

scenarios = {
    "Equity Crash": {
        "AAPL": -0.20,
        "MSFT": -0.20,
        "JPM": -0.20,
        "GLD": 0.05,
        "SPY": -0.20,
    },
    "Banking Stress": {
        "AAPL": -0.05,
        "MSFT": -0.05,
        "JPM": -0.30,
        "GLD": 0.03,
        "SPY": -0.10,
    },
    "Tech Selloff": {
        "AAPL": -0.25,
        "MSFT": -0.25,
        "JPM": -0.05,
        "GLD": 0.02,
        "SPY": -0.12,
    },
    "Gold Rally / Risk Off": {
        "AAPL": -0.10,
        "MSFT": -0.10,
        "JPM": -0.12,
        "GLD": 0.15,
        "SPY": -0.10,
    },
    "Broad Market Correction": {
        "AAPL": -0.15,
        "MSFT": -0.15,
        "JPM": -0.15,
        "GLD": -0.02,
        "SPY": -0.15,
    },
}


def calculate_scenario_return(portfolio_weights, shocks):
    return sum(weight * shocks[asset] for asset, weight in portfolio_weights.items())


def calculate_asset_contributions(portfolio_weights, shocks, portfolio_value):
    return {
        asset: portfolio_value * weight * shocks[asset]
        for asset, weight in portfolio_weights.items()
    }


def run_stress_test(portfolio_weights, scenario_shocks, portfolio_value):
    results = []

    for scenario_name, shocks in scenario_shocks.items():
        scenario_return = calculate_scenario_return(portfolio_weights, shocks)
        scenario_pnl = portfolio_value * scenario_return
        asset_contributions = calculate_asset_contributions(
            portfolio_weights,
            shocks,
            portfolio_value,
        )

        results.append(
            {
                "Scenario": scenario_name,
                "Portfolio Return": scenario_return,
                "Portfolio P&L": scenario_pnl,
                **asset_contributions,
            }
        )

    return pandas.DataFrame(results)


def format_currency(value):
    return f"-GBP {abs(value):,.2f}" if value < 0 else f"GBP {value:,.2f}"


def format_percent(value):
    return f"{value:.2%}"


def make_svg(width, height, content):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#fbfaf7"/>'
        f"{content}</svg>"
    )


def text(x, y, value, size=14, fill="#202124", weight="400", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-family="Inter, Arial, sans-serif" '
        f'font-size="{size}" fill="{fill}" font-weight="{weight}" '
        f'text-anchor="{anchor}">{escape(str(value))}</text>'
    )


def rect(x, y, width, height, fill, radius=0):
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{radius}" fill="{fill}"/>'
    )


def line(x1, y1, x2, y2, stroke="#d8d2c7", width=1):
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="{width}"/>'
    )


def blend(start_hex, end_hex, amount):
    amount = max(0, min(1, amount))
    start = tuple(int(start_hex[i : i + 2], 16) for i in (1, 3, 5))
    end = tuple(int(end_hex[i : i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(round(start[i] + (end[i] - start[i]) * amount) for i in range(3))
    return f"#{mixed[0]:02x}{mixed[1]:02x}{mixed[2]:02x}"


def save_bar_chart(df, value_column, output_path, title, value_formatter):
    sorted_df = df.sort_values(value_column)
    width = 980
    row_height = 58
    top = 86
    left = 250
    right = 150
    chart_width = width - left - right
    height = top + row_height * len(sorted_df) + 38
    max_abs = max(abs(value) for value in sorted_df[value_column]) or 1

    parts = [
        text(32, 38, title, size=24, weight="700"),
        text(32, 64, "Worst outcomes are shown first.", size=13, fill="#6c675f"),
        line(left, top - 18, left, height - 34),
    ]

    for index, row in sorted_df.reset_index(drop=True).iterrows():
        y = top + index * row_height
        scenario = row["Scenario"]
        value = row[value_column]
        bar_width = abs(value) / max_abs * chart_width
        color = "#b94a48" if value < 0 else "#2f7d5b"

        parts.extend(
            [
                text(32, y + 25, scenario, size=14, weight="600"),
                rect(left, y + 7, bar_width, 24, color, radius=4),
                text(
                    left + bar_width + 10,
                    y + 25,
                    value_formatter(value),
                    size=14,
                    weight="700",
                    fill=color,
                ),
                line(left, y + 45, width - 40, y + 45),
            ]
        )

    output_path.write_text(make_svg(width, height, "".join(parts)), encoding="utf-8")


def save_contribution_chart(df, assets, output_path):
    width = 1100
    row_height = 58
    top = 92
    left = 250
    right = 130
    chart_width = width - left - right
    height = top + row_height * len(df) + 92
    max_loss = max(abs(df[asset].clip(upper=0).sum()) for asset in assets)
    max_gain = max(abs(df[asset].clip(lower=0).sum()) for asset in assets)
    max_abs = max(max_loss, max_gain, 1)
    zero_x = left + chart_width / 2
    scale = (chart_width / 2) / max_abs
    colors = {
        "AAPL": "#386fa4",
        "MSFT": "#59a14f",
        "JPM": "#8e6c8a",
        "GLD": "#c79a2b",
        "SPY": "#e15759",
    }

    parts = [
        text(32, 38, "Asset Contribution by Scenario", size=24, weight="700"),
        text(
            32,
            64,
            "Each stacked bar shows which holdings drive gain or loss.",
            size=13,
            fill="#6c675f",
        ),
        line(zero_x, top - 18, zero_x, height - 86, stroke="#7a746b", width=1.5),
    ]

    for index, row in enumerate(df.itertuples(index=False)):
        y = top + index * row_height
        scenario = getattr(row, "Scenario")
        neg_x = zero_x
        pos_x = zero_x
        parts.append(text(32, y + 25, scenario, size=14, weight="600"))

        for asset in assets:
            value = getattr(row, asset)
            bar_width = abs(value) * scale
            if value < 0:
                neg_x -= bar_width
                parts.append(rect(neg_x, y + 8, bar_width, 24, colors[asset], radius=3))
            elif value > 0:
                parts.append(rect(pos_x, y + 8, bar_width, 24, colors[asset], radius=3))
                pos_x += bar_width

        parts.append(line(left, y + 45, width - 40, y + 45))

    legend_x = 32
    legend_y = height - 48
    for asset in assets:
        parts.append(rect(legend_x, legend_y - 13, 14, 14, colors[asset], radius=2))
        parts.append(text(legend_x + 22, legend_y, asset, size=13, fill="#4f4a43"))
        legend_x += 88

    output_path.write_text(make_svg(width, height, "".join(parts)), encoding="utf-8")


def save_heatmap(scenario_shocks, assets, output_path):
    cell_w = 118
    cell_h = 46
    left = 220
    top = 96
    width = left + cell_w * len(assets) + 48
    height = top + cell_h * len(scenario_shocks) + 40
    max_abs = max(abs(value) for shocks in scenario_shocks.values() for value in shocks.values())

    parts = [
        text(32, 38, "Scenario Shock Matrix", size=24, weight="700"),
        text(32, 64, "Input shocks by asset, colored by severity.", size=13, fill="#6c675f"),
    ]

    for col, asset in enumerate(assets):
        parts.append(
            text(
                left + col * cell_w + cell_w / 2,
                top - 22,
                asset,
                size=14,
                weight="700",
                anchor="middle",
            )
        )

    for row_index, (scenario, shocks) in enumerate(scenario_shocks.items()):
        y = top + row_index * cell_h
        parts.append(text(32, y + 29, scenario, size=14, weight="600"))

        for col, asset in enumerate(assets):
            value = shocks[asset]
            intensity = abs(value) / max_abs
            color = blend("#f2ede4", "#b94a48" if value < 0 else "#2f7d5b", intensity)
            x = left + col * cell_w
            parts.append(rect(x, y, cell_w - 8, cell_h - 8, color, radius=4))
            parts.append(
                text(
                    x + (cell_w - 8) / 2,
                    y + 25,
                    format_percent(value),
                    size=13,
                    weight="700",
                    anchor="middle",
                )
            )

    output_path.write_text(make_svg(width, height, "".join(parts)), encoding="utf-8")


def save_dashboard(formatted_results, worst_scenario):
    rows = []
    for row in formatted_results.to_dict("records"):
        cells = "".join(f"<td>{escape(str(value))}</td>" for value in row.values())
        rows.append(f"<tr>{cells}</tr>")

    headers = "".join(f"<th>{escape(column)}</th>" for column in formatted_results.columns)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Portfolio Stress Test Dashboard</title>
  <style>
    body {{
      margin: 0;
      background: #fbfaf7;
      color: #202124;
      font-family: Inter, Arial, sans-serif;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 24px 56px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
      letter-spacing: 0;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin: 24px 0;
    }}
    .metric {{
      border: 1px solid #ded7cb;
      border-radius: 8px;
      padding: 16px;
      background: #fffdfa;
    }}
    .label {{
      color: #6c675f;
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .value {{
      font-size: 22px;
      font-weight: 700;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      margin: 28px 0;
      border: 1px solid #ded7cb;
      border-radius: 8px;
      background: #fbfaf7;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fffdfa;
      border: 1px solid #ded7cb;
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      border-bottom: 1px solid #ebe5da;
      padding: 10px 12px;
      text-align: right;
      font-size: 14px;
    }}
    th:first-child, td:first-child {{
      text-align: left;
    }}
    th {{
      background: #f3efe7;
      color: #4f4a43;
    }}
    @media (max-width: 760px) {{
      .summary {{
        grid-template-columns: 1fr;
      }}
      table {{
        display: block;
        overflow-x: auto;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Portfolio Stress Test Dashboard</h1>
    <p>Scenario analysis for a GBP {PORTFOLIO_VALUE:,.0f} portfolio.</p>
    <section class="summary">
      <div class="metric">
        <div class="label">Worst scenario</div>
        <div class="value">{escape(worst_scenario["Scenario"])}</div>
      </div>
      <div class="metric">
        <div class="label">Worst return</div>
        <div class="value">{format_percent(worst_scenario["Portfolio Return"])}</div>
      </div>
      <div class="metric">
        <div class="label">Worst P&amp;L</div>
        <div class="value">{format_currency(worst_scenario["Portfolio P&L"])}</div>
      </div>
    </section>
    <img src="scenario_pnl.svg" alt="Scenario P&L bar chart">
    <img src="portfolio_returns.svg" alt="Portfolio return bar chart">
    <img src="asset_contributions.svg" alt="Asset contribution stacked bar chart">
    <img src="shock_matrix.svg" alt="Scenario shock heatmap">
    <table>
      <thead><tr>{headers}</tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </main>
</body>
</html>
"""
    dashboard_path = OUTPUT_DIR / "dashboard.html"
    dashboard_path.write_text(html, encoding="utf-8")
    return dashboard_path


def open_dashboard(dashboard_path):
    system = platform.system()
    resolved_path = dashboard_path.resolve()

    if system == "Darwin":
        subprocess.run(["open", str(resolved_path)], check=False)
    elif system == "Windows":
        try:
            subprocess.run(["cmd", "/c", "start", "", str(resolved_path)], check=False)
        except FileNotFoundError:
            webbrowser.open(resolved_path.as_uri())
    else:
        try:
            subprocess.run(["xdg-open", str(resolved_path)], check=False)
        except FileNotFoundError:
            webbrowser.open(resolved_path.as_uri())


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    results = run_stress_test(weights, scenarios, PORTFOLIO_VALUE)
    worst_scenario = results.loc[results["Portfolio P&L"].idxmin()]

    formatted_results = results.copy()
    formatted_results["Portfolio Return"] = formatted_results["Portfolio Return"].map(format_percent)
    formatted_results["Portfolio P&L"] = formatted_results["Portfolio P&L"].map(format_currency)

    for asset in weights:
        formatted_results[asset] = formatted_results[asset].map(format_currency)

    formatted_results.to_csv(OUTPUT_DIR / "scenario_results.csv", index=False)

    save_bar_chart(
        results,
        "Portfolio P&L",
        OUTPUT_DIR / "scenario_pnl.svg",
        "Scenario P&L",
        format_currency,
    )
    save_bar_chart(
        results,
        "Portfolio Return",
        OUTPUT_DIR / "portfolio_returns.svg",
        "Portfolio Return",
        format_percent,
    )
    save_contribution_chart(results, list(weights), OUTPUT_DIR / "asset_contributions.svg")
    save_heatmap(scenarios, list(weights), OUTPUT_DIR / "shock_matrix.svg")
    dashboard_path = save_dashboard(formatted_results, worst_scenario)
    open_dashboard(dashboard_path)

    print("Worst Scenario")
    print(f"Scenario: {worst_scenario['Scenario']}")
    print(f"Portfolio Return: {format_percent(worst_scenario['Portfolio Return'])}")
    print(f"Portfolio P&L: {format_currency(worst_scenario['Portfolio P&L'])}")
    print(f"Dashboard: {dashboard_path}")


if __name__ == "__main__":
    main()
