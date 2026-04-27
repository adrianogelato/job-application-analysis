# Job Application Analysis

Visualization of a personal job application process. The goal is to identify patterns in hiring timelines and rejection behaviour using a lightweight, fully local setup.

## Directory Structure

```
job-application-analysis/
│
├── README.md                   ← This file
├── analysis.py                 ← Run this to generate the HTML output
│
├── queries/                    ← SQL files loaded by analysis.py
│   ├── 01_status_overview.sql
│   ├── 02_rejection_duration.sql
│   ├── 03_rejections_by_weekday.sql
│   └── 04_cumulative_timeline.sql
│
├── data/
│   └── applications.csv        ← Exported from Obsidian
│
└── docs/
    └── index.html              ← Generated HTML output (served via GitHub Pages)
```

## Stack

| Layer           | Tool                           |
|-----------------|--------------------------------|
| Data tracking   | Obsidian (manual, per note)    |
| Data ingestion  | Obsidian Dataview (CSV export) |
| Storage / query | DuckDB                         |
| Transformation  | SQL (files in `queries/`)      |
| Visualisation   | Python + Plotly                |
| Output          | Plain Python script → HTML     |

## Design Decisions

**Local-only setup.** No cloud services, no database server, no live sync. The data lives in an Obsidian vault and is exported manually when an analysis run is needed. This keeps the setup dependency-free and the data private.

**DuckDB over a traditional database.** DuckDB queries CSV files directly without an import step. Zero configuration, no running process. It behaves like a full SQL engine (window functions, CTEs, date arithmetic) while being a single Python package.

**Plotly over matplotlib.** The output target is a self-contained HTML file. Plotly's output is natively HTML and JavaScript — `fig.to_html()` makes the pipeline trivial. matplotlib produces static images, which would require additional tooling to embed interactively in HTML.

**SQL in separate files.** Queries are kept in `.sql` files rather than inline Python strings so they can be read, tweaked, and extended without touching the analysis code. Each file corresponds to one chart.

**Plain script over a notebook.** A notebook was considered but dropped due to kernel management friction in VS Code on macOS. A plain `python3 analysis.py` invocation is simpler, more reproducible, and easier to run in CI if needed later.

**Manual export, no live updates.** The CSV is exported from Obsidian occasionally via a DataviewJS snippet. The analysis does not need to reflect real-time data — a periodic snapshot is sufficient.

## Obsidian Tracking Setup

Each job application is tracked as an individual note in Obsidian using the following conventions.

**Frontmatter properties:**

| Property           | Type   | Values / Notes                                      |
|--------------------|--------|-----------------------------------------------------|
| `role`             | text   |                                                     |
| `company`          | text   |                                                     |
| `salary`           | number | Target salary, optional                             |
| `application-date` | date   |                                                     |
| `interview-date`   | date   | Optional                                            |
| `end-date`         | date   | Date of rejection, ghosting confirmation, or offer  |
| `status`           | text   | `open` / `waiting` / `interviewing` / `rejected` / `ghosted` |
| `source-url`       | text   | Job posting URL, optional                           |
| `tags`             | list   | Always includes `job-application`                   |

**Status lifecycle:**

```
open → waiting → interviewing → rejected
                              ↘ ghosted
```

**Templater template** (`templates/job-application.md`):

```markdown
---
role: 
company: 
salary: 
application-date: <% tp.date.now("YYYY-MM-DD") %>
interview-date: 
end-date: 
status: open
tags:
  - job-application
source-url: 
---

## Timeline

- <% tp.date.now("YYYY-MM-DD") %> — 
```

New notes are created from this template via Templater, frontmatter is filled in manually, and the file is moved to the `applications/` folder in the vault.

## Exporting Data from Obsidian

Create a note in your vault with the following DataviewJS block. Adjust the folder path `"Applications"` to match your vault structure. Click the download link to save `applications.csv` into the `data/` folder.

````javascript
```dataviewjs
const pages = dv.pages('"Applications"')
    .where(p => p.status !== undefined);

const fields = [
    "role", "company", "salary",
    "application-date", "interview-date", "end-date",
    "status", "source-url"
];

function formatValue(val) {
    if (val === null || val === undefined) return "";
    if (val.ts !== undefined) return val.toFormat("yyyy-MM-dd"); // Luxon DateTime
    return String(val).replace(/"/g, '""');
}

const headers = ["filename", ...fields].join(",");
const rows = pages
    .map(p => {
        const frontmatter = fields.map(f => `"${formatValue(p[f])}"`);
        return [`"${p.file.name}"`, ...frontmatter].join(",");
    })
    .array();

const csv = [headers, ...rows].join("\n");
const blob = new Blob([csv], { type: "text/csv" });
const a = document.createElement("a");
a.href = URL.createObjectURL(blob);
a.download = "applications.csv";
a.textContent = "⬇ Download applications.csv";
a.style.cssText = "display:block;padding:8px;background:#4a9;color:white;border-radius:4px;text-decoration:none;width:fit-content";
dv.container.appendChild(a);
```
````

## Setup

The project uses a virtual environment (`.venv`) to keep dependencies isolated from the rest of your system.

Create it once:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

VS Code will detect `.venv` automatically once it exists.

## Running the Analysis

1. Place `applications.csv` in `data/`
2. Open a terminal in the project folder and run:

```bash
source .venv/bin/activate
python3 analysis.py
```

3. Open `docs/index.html` in your browser, or push to GitHub and enable Pages from the `docs/` folder

## Adding New Queries

Add a `.sql` file to `queries/`, add a corresponding chart function in `analysis.py` following the same pattern as the existing ones, and append it to the `figures` list at the bottom of the script.

The view `applications` is available in all queries with these columns:

| Column             | Type    | Notes           |
|--------------------|---------|-----------------|
| `filename`         | VARCHAR | Obsidian note name |
| `role`             | VARCHAR |                 |
| `company`          | VARCHAR |                 |
| `salary`           | BIGINT  | NULL if missing |
| `application_date` | DATE    | NULL if missing |
| `interview_date`   | DATE    | NULL if missing |
| `end_date`         | DATE    | NULL if missing |
| `status`           | VARCHAR | open, waiting, interviewing, rejected, ghosted |
| `source_url`       | VARCHAR |                 |

## Analysis Questions

- What is the total number and share per status?
- What is the average and distribution of days between application and rejection?
- On which weekdays are rejections most commonly sent?
- How do applications, rejections, and interviews accumulate over time?
