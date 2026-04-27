#!/usr/bin/env python3
"""
Job Application Analysis
Reads data/applications.csv, runs SQL queries, writes output/analysis.html.

Usage:
    python3 analysis.py
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "applications.csv"
QUERIES = ROOT / "queries"
OUTPUT = ROOT / "docs" / "index.html"


# ── Data setup ────────────────────────────────────────────────────────────────


def check_data() -> None:
    if not DATA.exists():
        print(f"ERROR: {DATA} not found.\nExport from Obsidian first (see README).")
        sys.exit(1)


def setup_db() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    conn.execute(
        f"""
        CREATE OR REPLACE VIEW applications AS
        SELECT
            TRIM(filename)                            AS filename,
            TRIM(role)                                AS role,
            TRIM(company)                             AS company,
            salary,
            TRY_CAST("application-date" AS DATE)      AS application_date,
            TRY_CAST("interview-date"   AS DATE)      AS interview_date,
            TRY_CAST("end-date"         AS DATE)      AS end_date,
            TRIM(LOWER(status))                       AS status,
            "source-url"                              AS source_url
        FROM read_csv_auto('{DATA}')
    """
    )
    return conn


def run_query(conn: duckdb.DuckDBPyConnection, filename: str) -> pd.DataFrame:
    """Load and execute a SQL file from queries/."""
    sql = (QUERIES / filename).read_text()
    return conn.execute(sql).df()


def validate_data(conn: duckdb.DuckDBPyConnection) -> None:
    """Print a summary of the loaded data to validate the CSV was read correctly."""
    df = conn.execute("SELECT * FROM applications").df()

    print("=" * 50)
    print("DATA VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Rows:     {len(df)}")
    print(f"Columns:  {list(df.columns)}")
    print()
    print("── Null counts ──")
    print(df.isnull().sum().to_string())
    print()
    print("── Status values ──")
    print(df["status"].value_counts().to_string())
    print()
    print("── Date range (application_date) ──")
    print(f"  earliest: {df['application_date'].min()}")
    print(f"  latest:   {df['application_date'].max()}")
    print()
    print("── Sample rows (first 3) ──")
    print(df.head(3).to_string())
    print("=" * 50)
    print()


# ── Charts ────────────────────────────────────────────────────────────────────


def chart_status_overview(conn) -> go.Figure:
    df = run_query(conn, "01_status_overview.sql")
    print(f"[status overview]\n{df.to_string()}\n")
    fig = px.pie(
        df,
        values="count",
        names="status",
        title="Application Status Distribution",
        hole=0.4,
        category_orders={
            "status": ["open", "waiting", "interviewing", "rejected", "ghosted"]
        },
    )
    fig.update_traces(textinfo="label+value")
    total = df["count"].sum()
    fig.update_layout(
        annotations=[
            dict(
                text=str(total),
                x=0.5,
                y=0.5,
                font_size=24,
                showarrow=False,
            )
        ]
    )
    return fig


def chart_rejection_duration(conn) -> go.Figure:
    df = run_query(conn, "02_rejection_duration.sql")
    print(
        f"[rejection duration] {len(df)} rows, days range: {df['days_to_rejection'].min()}–{df['days_to_rejection'].max()}\n"
    )
    avg = df["days_to_rejection"].mean()
    median = df["days_to_rejection"].median()

    fig = px.histogram(
        df,
        x="days_to_rejection",
        title=f"Days to Rejection  ·  mean {avg:.1f} d  ·  median {median:.1f} d",
        labels={"days_to_rejection": "Days from Application to Rejection"},
    )
    fig.update_traces(xbins=dict(size=1))
    fig.add_vline(
        x=avg,
        line_dash="dash",
        annotation_text=f"Mean {avg:.1f} d",
        annotation_position="top right",
    )
    return fig


def chart_rejections_by_weekday(conn) -> go.Figure:
    df = run_query(conn, "03_rejections_by_weekday.sql")
    print(f"[rejections by weekday]\n{df.to_string()}\n")
    fig = px.bar(
        df,
        x="weekday",
        y="count",
        title="Rejections by Day of Week",
        labels={"weekday": "Day", "count": "Rejections"},
        category_orders={
            "weekday": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
        },
    )
    return fig


def chart_applications_by_weekday(conn) -> go.Figure:
    df = run_query(conn, "05_applications_by_weekday.sql")
    print(f"[applications by weekday]\n{df.to_string()}\n")
    fig = px.bar(
        df,
        x="weekday",
        y="count",
        title="Applications by Day of Week",
        labels={"weekday": "Day", "count": "Applications"},
        category_orders={
            "weekday": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
        },
    )
    return fig


def chart_cumulative_timeline(conn) -> go.Figure:
    df = run_query(conn, "04_cumulative_timeline.sql")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["event_date"],
            y=df["cumulative_applications"],
            mode="lines",
            name="Applications submitted",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["event_date"],
            y=df["cumulative_rejections"],
            mode="lines",
            name="Rejections received",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["event_date"],
            y=df["cumulative_interviews"],
            mode="lines",
            name="Interviews started",
        )
    )
    fig.update_layout(
        title="Cumulative Activity Over Time",
        xaxis_title="Date",
        yaxis_title="Cumulative Count",
        hovermode="x unified",
    )
    return fig


# ── HTML output ───────────────────────────────────────────────────────────────


def write_html(figures: list) -> None:
    OUTPUT.parent.mkdir(exist_ok=True)

    # First figure injects the correct versioned Plotly CDN script tag;
    # subsequent figures reuse it with include_plotlyjs=False.
    chart_divs = "\n".join(
        f'<div class="chart">'
        f'{fig.to_html(full_html=False, include_plotlyjs=("cdn" if i == 0 else False))}'
        f"</div>"
        for i, fig in enumerate(figures)
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Job Application Analysis</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            max-width: 1100px;
            margin: 0 auto;
            padding: 2rem;
            background: #fafafa;
            color: #333;
        }}
        h1 {{ margin-bottom: 0.25rem; }}
        .subtitle {{ color: #888; margin-bottom: 2rem; font-size: 0.9rem; }}
        .chart {{
            background: white;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
    </style>
</head>
<body>
    <h1>Job Application Analysis</h1>
    <p class="subtitle">Generated {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}</p>
    {chart_divs}
</body>
</html>"""

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Written → {OUTPUT}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    check_data()
    conn = setup_db()
    validate_data(conn)
    figures = [
        chart_status_overview(conn),
        chart_rejection_duration(conn),
        chart_rejections_by_weekday(conn),
        chart_applications_by_weekday(conn),
        chart_cumulative_timeline(conn),
    ]
    write_html(figures)
