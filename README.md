# QuickBase ETL Automation Pipeline

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Code Style](https://img.shields.io/badge/code%20style-PEP%208-green.svg)](https://peps.python.org/pep-0008/)
[![License](https://img.shields.io/badge/license-Internal-lightgrey.svg)](#)

A modular, object-oriented ETL service designed to query and export data directly from the **QuickBase REST API**, sanitize and format CSV extracts, and deliver them to designated staging and network share locations without third-party orchestrators like Azure Data Factory.

---

## Table of Contents

- [Features](#features)
- [Architecture & Design](#architecture--design)
- [Directory Layout](#directory-layout)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Configuration Reference](#configuration-reference)
- [Data Transformation Rules](#data-transformation-rules)
- [Logging & Diagnostics](#logging--diagnostics)

---

## Features

- **Direct QuickBase REST API Integration:** Queries records dynamically using `/v1/records/query` without external ADF dependencies.
- **Automated Pagination:** Automatically resolves multi-page responses with automatic `skip` handling.
- **Dynamic Query Building:** Merges scheduling rules (`jobs.json`) with extraction criteria (`config.json`), resolving Table IDs, custom `where_clause` filters, and field projections.
- **Single-Pass CSV Sanitization:** Cleans delimiters, strips unwanted quotes and brackets, handles multi-value string formats, and normalizes leading zeros for ZIP codes.
- **Flexible Execution Modes:** Trigger extraction by relative system schedule ($\pm 5$ minutes window), target time string, or explicit job name.

---

## Architecture & Design

The application follows clean object-oriented principles:

```
                  ┌────────────────────────┐
                  │        main.py         │
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ QuickBaseExtract-      │
                  │ Pipeline (Scheduler)   │
                  └───────────┬────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
            ▼                                   ▼
   ┌──────────────────┐               ┌──────────────────┐
   │ QuickBaseJob-    │               │  CSVTransformer  │
   │ Processor        │               │  (Sanitization)  │
   └────────┬─────────┘               └──────────────────┘
            │
            ▼
   ┌──────────────────┐
   │ quickbase_export_│
   │ api (REST API)   │
   └──────────────────┘
```

- **`config/job_config.py`**: Immutable dataclass describing job specs.
- **`config/job_registry.py`**: Loads and merges operational parameters with extraction rules.
- **`core/quickbase_export_api.py`**: Handles authentication, pagination, and initial CSV generation.
- **`core/csv_transformer.py`**: Cleans cell strings and fixes data column issues in a single pass.
- **`core/job_processor.py`**: Coordinates extraction, cleanup, and destination deployment.
- **`pipeline/extract_pipeline.py`**: Matches scheduled jobs against execution time.

---

## Directory Layout

```text
.
├── config/
│   ├── __init__.py
│   ├── job_config.py            # JobConfig dataclass definition
│   ├── job_registry.py          # Merges jobs.json and config.json
│   ├── jobs.json                # Schedules, masks, and folder targets
│   └── config.json              # QuickBase Table IDs, where clauses, and fields
│
├── core/
│   ├── __init__.py
│   ├── csv_transformer.py       # Regex cleanup and column transformations
│   ├── job_processor.py         # Job extraction lifecycle controller
│   └── quickbase_export_api.py  # QuickBase REST API client
│
├── pipeline/
│   ├── __init__.py
│   └── extract_pipeline.py      # Execution planner and batch manager
│
├── utils/
│   ├── __init__.py
│   └── logger.py                # Logging configuration
│
├── .gitignore
├── requirements.txt             # Python dependencies
├── main.py                      # Application entry point
└── README.md
```

---

## Prerequisites

- **Python 3.8+**
- Active access to QuickBase with API credentials (User Token & Realm Hostname)
- Read/Write filesystem permissions for target staging and destination directories

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Androbhikk73/automated-cpt-report-generation.git
cd automated-cpt-report-generation
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell / CMD):**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## Environment Variables

The QuickBase API client requires authorization credentials in your runtime environment.

### Windows (PowerShell)

```powershell
$env:QB_REALM_HOSTNAME="yourcompany.quickbase.com"
$env:QB_USER_TOKEN="your_quickbase_user_token"
```

### Windows (CMD)

```cmd
set QB_REALM_HOSTNAME=yourcompany.quickbase.com
set QB_USER_TOKEN=your_quickbase_user_token
```

### Linux / macOS

```bash
export QB_REALM_HOSTNAME="yourcompany.quickbase.com"
export QB_USER_TOKEN="your_quickbase_user_token"
```

---

## Running the Application

`main.py` requires two CLI arguments:

```bash
python main.py <ENVIRONMENT> <SCHEDULE_ARGUMENT>
```

| Argument              | Description                                     | Example Values                 |
| --------------------- | ----------------------------------------------- | ------------------------------ |
| `<ENVIRONMENT>`       | Environment tag                                 | `DEV`, `QA`, `PROD`            |
| `<SCHEDULE_ARGUMENT>` | Trigger time, current clock, or manual job name | `02:00:00`, `0`, `CPTLevelRpt` |

### Examples

#### 1. Test by Job Schedule Window

Trigger jobs scheduled around 2:00 AM ($\pm 5$ minutes window):

```bash
python main.py DEV 02:00:00
```

#### 2. Run Using Current System Clock

Checks all configured tasks against the current system time:

```bash
python main.py DEV 0
```

_Note: If no job in `jobs.yaml` is scheduled within 5 minutes of your current machine time, the runner will log `No matching jobs found` and exit cleanly._

#### 3. Run a Specific Job by Name

Execute directly regardless of scheduled execution window:

```bash
python main.py DEV CPTLevelRpt
```

---

## Configuration Reference

The application separates schedule routing from QuickBase query specifications:

### 1. `config/jobs.json` (Schedules & Output Locations)

```json
CPTLevelRpt:
  {
    "name_id": "CPTLevelRpt"
    "date_stamp_format": "%Y%m%d"
    "scheduled_time": "02:00:00"
    "scheduled_type": "Daily"
    "export_file_mask": "CPTLevelRpt"
    "export_file_extension": ".csv"
    "staging_folder_path": 'C:\data\staging\CPTLevelRpt'
    "destination_file_mask": "CPTLevelRpt_"
    "destination_folder_path": 'C:\data\destination\CPTLevelRpt'
  }
```

### 2. `config/config.json` (QuickBase Table & Field Schema)

```json
{
  "tables": [
    {
      "job_name": "CPTLevelRpt",
      "table_id": "bvq9k588k",
      "where_clause": "{19.EX.YESTERDAY}",
      "field_labels": {
        "6": "ONP Initiated Date",
        "7": "IDR Initiated Date",
        "8": "Invoice",
        "9": "CPT Code"
      }
    }
  ]
}
```

---

## Data Transformation Rules

`CSVTransformer` automatically cleans raw QuickBase extracts:

1. **Delimiter Normalization:** Converts multi-value string formats like `'value1','value2'` into semicolon-delimited values (`value1;value2`).
2. **Noise Character Stripping:** Removes square brackets (`[`, `]`) and single quotes (`'`).
3. **Double Delimiter Removal:** Removes duplicate patterns such as `;;`.
4. **ZIP Code Normalization:** Prepends `'0` to 4-digit numeric postal codes to preserve leading zeros in Excel and downstream consumers.

---

## Logging & Diagnostics

Logs are recorded in `quickbase_export_extract.log` and printed to `stdout`:

```text
2026-10-10 02:00:01 INFO     Starting QuickBase pipeline execution | Environment: DEV | Schedule Time: 02:00:00
2026-10-10 02:00:01 INFO     Starting Job: CPTLevelRpt
2026-10-10 02:00:02 INFO     [CPTLevelRpt] Initiating QuickBase API extraction for table bvq9k588k
2026-10-10 02:00:03 INFO     [CPTLevelRpt] Fetched 142 records (Skip: 0)...
2026-10-10 02:00:03 INFO     Completed Job: CPTLevelRpt -> Output: C:\data\destination\CPTLevelRpt\CPTLevelRpt_20261010.csv
2026-10-10 02:00:03 INFO     Pipeline execution completed successfully.
```

If an error occurs, full stack traces are logged directly to the log file to assist troubleshooting.
