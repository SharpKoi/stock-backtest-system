"""Report Generator: console summary and HTML report with charts.

Produces two types of output:
1. Console summary - text-based quick overview
2. HTML report - interactive charts (equity curve, drawdown) and trade tables
"""



from app.core.config import REPORTS_DIR
from app.models.schemas import PerformanceMetrics
from app.services.strategy import Portfolio, Side


def generate_console_report(metrics: PerformanceMetrics,
                            portfolio: Portfolio,
                            strategy_name: str,
                            symbols: list[str]) -> str:
    """Generate a text-based console summary report.

    Args:
        metrics: Computed performance metrics.
        portfolio: Portfolio with equity history and trades.
        strategy_name: Name of the strategy.
        symbols: List of traded symbols.

    Returns:
        Formatted string for console output.
    """
    divider = "=" * 60

    lines = [
        divider,
        f"  BACKTEST REPORT: {strategy_name}",
        divider,
        f"  Symbols:            {', '.join(symbols)}",
        f"  Initial Capital:    ${portfolio.initial_capital:,.2f}",
    ]

    if portfolio.equity_history:
        final = portfolio.equity_history[-1]["equity"]
        start_date = portfolio.equity_history[0]["date"]
        end_date = portfolio.equity_history[-1]["date"]
        lines.extend([
            f"  Final Equity:       ${final:,.2f}",
            f"  Period:             {start_date} to {end_date}",
        ])

    lines.extend([
        divider,
        "  PERFORMANCE METRICS",
        divider,
        f"  Total Return:       ${metrics.total_return:,.2f} ({metrics.total_return_pct:+.2f}%)",
        f"  Annualized Return:  {metrics.annualized_return_pct:+.2f}%",
        f"  Max Drawdown:       {metrics.max_drawdown_pct:.2f}%",
        f"  Sharpe Ratio:       {metrics.sharpe_ratio:.4f}",
        f"  Profit Factor:      {metrics.profit_factor:.4f}",
        divider,
        "  TRADE STATISTICS",
        divider,
        f"  Total Trades:       {metrics.total_trades}",
        f"  Winning Trades:     {metrics.winning_trades}",
        f"  Losing Trades:      {metrics.losing_trades}",
        f"  Win Rate:           {metrics.win_rate:.2f}%",
        f"  Avg Trade Return:   {metrics.avg_trade_return_pct:+.2f}%",
        f"  Max Consec. Wins:   {metrics.max_consecutive_wins}",
        f"  Max Consec. Losses: {metrics.max_consecutive_losses}",
        divider,
    ])

    return "\n".join(lines)


def generate_html_report(metrics: PerformanceMetrics,
                         portfolio: Portfolio,
                         strategy_name: str,
                         symbols: list[str],
                         backtest_id: int | None = None) -> str:
    """Generate an HTML report with interactive charts and trade table.

    Args:
        metrics: Computed performance metrics.
        portfolio: Portfolio with equity history and trades.
        strategy_name: Name of the strategy.
        symbols: List of traded symbols.
        backtest_id: Optional backtest ID for file naming.

    Returns:
        File path of the generated HTML report.
    """
    equity_chart = _build_equity_chart(portfolio)
    drawdown_chart = _build_drawdown_chart(portfolio)
    trade_table_html = _build_trade_table(portfolio)
    metrics_html = _build_metrics_section(metrics)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report: {strategy_name}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1117;
            color: #e0e0e0;
            padding: 24px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            font-size: 28px;
            margin-bottom: 8px;
            color: #ffffff;
        }}
        .subtitle {{
            color: #888;
            margin-bottom: 24px;
            font-size: 14px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .metric-card {{
            background: #1a1d29;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #2a2d3a;
        }}
        .metric-label {{
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: 600;
            margin-top: 4px;
        }}
        .positive {{ color: #00c853; }}
        .negative {{ color: #ff1744; }}
        .neutral {{ color: #ffffff; }}
        .chart-container {{
            background: #1a1d29;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 24px;
            border: 1px solid #2a2d3a;
        }}
        .chart-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            background: #1e2130;
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            color: #aaa;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 8px 12px;
            border-bottom: 1px solid #1e2130;
        }}
        tr:hover td {{ background: #1a1d29; }}
        .buy {{ color: #00c853; }}
        .sell {{ color: #ff1744; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Backtest Report: {strategy_name}</h1>
        <p class="subtitle">Symbols: {', '.join(symbols)} | Period: {_get_period(portfolio)}</p>

        {metrics_html}

        <div class="chart-container">
            <div class="chart-title">Equity Curve</div>
            <div id="equity-chart"></div>
        </div>

        <div class="chart-container">
            <div class="chart-title">Drawdown</div>
            <div id="drawdown-chart"></div>
        </div>

        <div class="chart-container">
            <div class="chart-title">Trade Log ({len(portfolio.trades)} trades)</div>
            {trade_table_html}
        </div>
    </div>

    <script>
        {equity_chart}
        {drawdown_chart}
    </script>
</body>
</html>"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"report_{backtest_id or 'latest'}.html"
    filepath = REPORTS_DIR / filename
    filepath.write_text(html, encoding="utf-8")
    return str(filepath)


def _get_period(portfolio: Portfolio) -> str:
    """Extract date range from equity history."""
    if not portfolio.equity_history:
        return "N/A"
    start = portfolio.equity_history[0]["date"]
    end = portfolio.equity_history[-1]["date"]
    return f"{start} to {end}"


def _build_metrics_section(metrics: PerformanceMetrics) -> str:
    """Build HTML for the metrics card grid."""

    def _css_class(value: float) -> str:
        if value > 0:
            return "positive"
        if value < 0:
            return "negative"
        return "neutral"

    cards = [
        ("Total Return", f"${metrics.total_return:,.2f}",
         _css_class(metrics.total_return)),
        ("Total Return %", f"{metrics.total_return_pct:+.2f}%",
         _css_class(metrics.total_return_pct)),
        ("Annualized Return", f"{metrics.annualized_return_pct:+.2f}%",
         _css_class(metrics.annualized_return_pct)),
        ("Max Drawdown", f"{metrics.max_drawdown_pct:.2f}%",
         _css_class(metrics.max_drawdown_pct)),
        ("Sharpe Ratio", f"{metrics.sharpe_ratio:.4f}",
         _css_class(metrics.sharpe_ratio)),
        ("Win Rate", f"{metrics.win_rate:.1f}%", "neutral"),
        ("Total Trades", str(metrics.total_trades), "neutral"),
        ("Profit Factor", f"{metrics.profit_factor:.2f}",
         _css_class(metrics.profit_factor - 1)),
    ]

    html_cards = []
    for label, value, css in cards:
        html_cards.append(
            f'<div class="metric-card">'
            f'<div class="metric-label">{label}</div>'
            f'<div class="metric-value {css}">{value}</div>'
            f'</div>'
        )

    return f'<div class="metrics-grid">{"".join(html_cards)}</div>'


def _build_equity_chart(portfolio: Portfolio) -> str:
    """Generate Plotly JS code for the equity curve chart."""
    if not portfolio.equity_history:
        return ""

    dates = [e["date"] for e in portfolio.equity_history]
    equities = [e["equity"] for e in portfolio.equity_history]

    return f"""
    Plotly.newPlot('equity-chart', [{{
        x: {dates},
        y: {equities},
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        line: {{ color: '#4fc3f7', width: 1.5 }},
        fillcolor: 'rgba(79, 195, 247, 0.1)',
    }}], {{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ color: '#888' }},
        xaxis: {{ gridcolor: '#1e2130', showgrid: true }},
        yaxis: {{ gridcolor: '#1e2130', showgrid: true, tickprefix: '$' }},
        margin: {{ l: 60, r: 20, t: 10, b: 40 }},
        height: 300,
    }});
    """


def _build_drawdown_chart(portfolio: Portfolio) -> str:
    """Generate Plotly JS code for the drawdown chart."""
    if not portfolio.equity_history:
        return ""

    dates = [e["date"] for e in portfolio.equity_history]
    equities = [e["equity"] for e in portfolio.equity_history]

    # Compute drawdown series
    peak = equities[0]
    drawdowns = []
    for eq in equities:
        if eq > peak:
            peak = eq
        dd = ((eq - peak) / peak) * 100 if peak > 0 else 0
        drawdowns.append(round(dd, 4))

    return f"""
    Plotly.newPlot('drawdown-chart', [{{
        x: {dates},
        y: {drawdowns},
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        line: {{ color: '#ff1744', width: 1.5 }},
        fillcolor: 'rgba(255, 23, 68, 0.1)',
    }}], {{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {{ color: '#888' }},
        xaxis: {{ gridcolor: '#1e2130', showgrid: true }},
        yaxis: {{ gridcolor: '#1e2130', showgrid: true, ticksuffix: '%' }},
        margin: {{ l: 60, r: 20, t: 10, b: 40 }},
        height: 250,
    }});
    """


def _build_trade_table(portfolio: Portfolio) -> str:
    """Build HTML table of all trades."""
    if not portfolio.trades:
        return "<p>No trades executed.</p>"

    rows = []
    for i, trade in enumerate(portfolio.trades, 1):
        side_class = "buy" if trade.side == Side.BUY else "sell"
        total = trade.quantity * trade.price
        rows.append(
            f"<tr>"
            f"<td>{i}</td>"
            f"<td>{trade.date}</td>"
            f"<td>{trade.symbol}</td>"
            f'<td class="{side_class}">{trade.side.value}</td>'
            f"<td>{trade.quantity:.0f}</td>"
            f"<td>${trade.price:.2f}</td>"
            f"<td>${total:,.2f}</td>"
            f"<td>${trade.commission:.2f}</td>"
            f"</tr>"
        )

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th><th>Date</th><th>Symbol</th><th>Side</th>
                <th>Qty</th><th>Price</th><th>Total</th><th>Commission</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """
