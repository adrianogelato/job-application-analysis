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
from plotly.subplots import make_subplots

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "applications.csv"
QUERIES = ROOT / "queries"
OUTPUT = ROOT / "docs" / "index.html"

# ── Color scheme ──────────────────────────────────────────────────────────────
# Status colors — used in the pie chart, one per tracking state
COLOR_STATUS = {
    "open": "lightgrey",
    "waiting": "steelblue",
    "interviewing": "seagreen",
    "rejected": "tomato",
    "ghosted": "slategrey",
}
# Comparison colors — used when plotting submissions vs rejections vs interviews
COLOR_SUBMISSIONS = "cornflowerblue"  # all non-open submissions (multi-state aggregate)
COLOR_REJECTIONS = "tomato"  # matches rejected status
COLOR_INTERVIEWS = "seagreen"  # matches interviewing status


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
    stats = run_query(conn, "07_summary_stats.sql").iloc[0]

    def count(status):
        rows = df[df["status"] == status]["count"]
        return int(rows.values[0]) if len(rows) > 0 else 0

    submitted_statuses = ["waiting", "interviewing", "rejected", "ghosted"]
    submitted_total = sum(count(s) for s in submitted_statuses)
    open_count = count("open")
    total = submitted_total + open_count

    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.6, 0.4],
        specs=[[{"type": "xy"}, {"type": "table"}]],
    )

    for rank, (status, color) in enumerate(
        [
            ("open", COLOR_STATUS["open"]),
            ("waiting", COLOR_STATUS["waiting"]),
            ("interviewing", COLOR_STATUS["interviewing"]),
            ("rejected", COLOR_REJECTIONS),
            ("ghosted", COLOR_STATUS["ghosted"]),
        ],
        start=1,
    ):
        n = count(status)
        fig.add_trace(
            go.Bar(
                y=[""],
                x=[n],
                name=status,
                orientation="h",
                marker_color=color,
                text=str(n) if n > 0 else "",
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=13, color="white"),
                legendrank=rank,
            ),
            row=1,
            col=1,
        )

    duration_days = (stats["latest_submission"] - stats["first_submission"]).days
    weeks = duration_days / 7
    submissions_per_week = int(stats["total_submitted"]) / weeks if weeks > 0 else 0

    table_headers = ["Metric", "Value"]
    table_rows = [
        ["Total", str(total)],
        ["First submission", str(stats["first_submission"])[:10]],
        ["Latest submission", str(stats["latest_submission"])[:10]],
        ["Duration", f"{duration_days} days"],
        ["Submissions / week", f"{submissions_per_week:.1f}"],
        ["Waiting", str(int(stats["total_waiting"]))],
        ["Interviewing", str(int(stats["total_interviewing"]))],
        ["Rejected", str(int(stats["total_rejected"]))],
        ["Ghosted", str(int(stats["total_ghosted"]))],
    ]

    fig.add_trace(
        go.Table(
            header=dict(
                values=table_headers,
                align="left",
                font=dict(size=12),
            ),
            cells=dict(
                values=list(zip(*table_rows)),
                align="left",
                font=dict(size=12),
            ),
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title=f"1 · Application Status Overview  ·  {total} total",
        barmode="stack",
        xaxis=dict(visible=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="left",
            x=0,
            traceorder="normal",
        ),
    )
    return fig


def chart_rejection_duration(conn) -> go.Figure:
    df = run_query(conn, "02_rejection_duration.sql")
    avg = df["days_to_rejection"].mean()
    median = df["days_to_rejection"].median()

    fig = px.histogram(
        df,
        x="days_to_rejection",
        title=f"2 · Days to Rejection  ·  mean {avg:.1f} d  ·  median {median:.1f} d",
        labels={"days_to_rejection": "Days from Submission to Rejection"},
        color_discrete_sequence=[COLOR_REJECTIONS],
    )
    fig.update_traces(xbins=dict(size=1))
    fig.add_vline(
        x=avg,
        line_dash="dash",
        annotation_text=f"Mean {avg:.1f} d",
        annotation_position="top right",
    )
    return fig


def chart_weekday_activity(conn) -> go.Figure:
    df_app = run_query(conn, "05_submissions_by_weekday.sql")
    df_rej = run_query(conn, "03_rejections_by_weekday.sql")

    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    df = (
        df_app[["weekday", "count", "sort_order"]]
        .rename(columns={"count": "submissions"})
        .merge(
            df_rej[["weekday", "count"]].rename(columns={"count": "rejections"}),
            on="weekday",
            how="outer",
        )
        .fillna(0)
        .sort_values("sort_order")
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["weekday"],
            y=df["submissions"],
            name="Submissions",
            marker_color=COLOR_SUBMISSIONS,
            text=df["submissions"].astype(int),
            textposition="outside",
            textfont=dict(color=COLOR_SUBMISSIONS),
        )
    )
    fig.add_trace(
        go.Bar(
            x=df["weekday"],
            y=df["rejections"],
            name="Rejections",
            marker_color=COLOR_REJECTIONS,
            text=df["rejections"].astype(int),
            textposition="outside",
            textfont=dict(color=COLOR_REJECTIONS),
        )
    )
    fig.update_layout(
        title="3 · Submissions and Rejections by Day of Week",
        xaxis=dict(categoryorder="array", categoryarray=weekday_order),
        yaxis_title="Count",
        barmode="group",
        hovermode="x unified",
    )
    return fig


def chart_cumulative_timeline(conn) -> go.Figure:
    df_cum = run_query(conn, "04_cumulative_timeline.sql")
    df_monthly = run_query(conn, "06_monthly_activity.sql")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Monthly bars on secondary y-axis — with data labels
    fig.add_trace(
        go.Bar(
            x=df_monthly["month"],
            y=df_monthly["submissions"],
            name="Submissions (monthly)",
            opacity=0.35,
            marker_color=COLOR_SUBMISSIONS,
            text=df_monthly["submissions"],
            textposition="outside",
            textfont=dict(color=COLOR_SUBMISSIONS),
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Bar(
            x=df_monthly["month"],
            y=df_monthly["rejections"],
            name="Rejections (monthly)",
            opacity=0.35,
            marker_color=COLOR_REJECTIONS,
            text=df_monthly["rejections"],
            textposition="outside",
            textfont=dict(color=COLOR_REJECTIONS),
        ),
        secondary_y=True,
    )

    # Cumulative lines on primary y-axis — with end labels showing final value
    n = len(df_cum)

    def end_label(series):
        return [""] * (n - 1) + [str(series.iloc[-1])]

    fig.add_trace(
        go.Scatter(
            x=df_cum["event_date"],
            y=df_cum["cumulative_submissions"],
            mode="lines+text",
            name="Submissions (cumulative)",
            line=dict(color=COLOR_SUBMISSIONS),
            text=end_label(df_cum["cumulative_submissions"]),
            textposition="middle right",
            textfont=dict(color=COLOR_SUBMISSIONS),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df_cum["event_date"],
            y=df_cum["cumulative_rejections"],
            mode="lines+text",
            name="Rejections (cumulative)",
            line=dict(color=COLOR_REJECTIONS),
            text=end_label(df_cum["cumulative_rejections"]),
            textposition="middle right",
            textfont=dict(color=COLOR_REJECTIONS),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df_cum["event_date"],
            y=df_cum["cumulative_interviews"],
            mode="lines+text",
            name="Interviews (cumulative)",
            line=dict(color=COLOR_INTERVIEWS),
            text=end_label(df_cum["cumulative_interviews"]),
            textposition="middle right",
            textfont=dict(color=COLOR_INTERVIEWS),
        ),
        secondary_y=False,
    )

    fig.update_layout(
        title="4 · Submission and Rejection Activity Over Time",
        hovermode="x unified",
        barmode="group",
        # Extra right margin so end labels aren't clipped
        margin=dict(r=80),
    )
    fig.update_yaxes(title_text="Cumulative count", secondary_y=False)
    fig.update_yaxes(title_text="Monthly count", secondary_y=True)
    fig.update_xaxes(
        dtick="M1",
        tickformat="%b %Y",
        tickangle=-45,
        showgrid=True,
        gridcolor="rgba(0,0,0,0.08)",
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
        chart_weekday_activity(conn),
        chart_cumulative_timeline(conn),
    ]
    write_html(figures)
