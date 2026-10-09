import json
from pathlib import Path
from typing import Dict
from config.job_config import JobConfig

def load_merged_registry(schedule_path: Path, qb_config_path: Path) -> Dict[str, JobConfig]:
    # Load Scheduling & Path Data
    if not schedule_path.exists():
        raise FileNotFoundError(f"Config file not found at: {schedule_path}")

    with open(schedule_path, "r", encoding="utf-8") as f:
        schedule_data = json.load(f) or {}

    # Load QuickBase Query Data
    qb_data_lookup = {}
    if qb_config_path.exists():
        with open(qb_config_path, "r", encoding="utf-8") as f:
            qb_raw = json.load(f)
            for table in qb_raw.get("tables", []):
                qb_data_lookup[table["job_name"]] = table

    # Merge configurations
    registry = {}
    for job_key, job_params in schedule_data.items():
        qb_params = qb_data_lookup.get(job_key, {})
        where_clause = qb_params.get("where_clause")
        if "table_id" in qb_params:
            job_params["table_id"] = qb_params["table_id"]
            job_params["where_clause"] = where_clause
            job_params["field_labels"] = qb_params.get("field_labels", {})

        registry[job_key] = JobConfig(**job_params)

    return registry

CONFIG_DIR = Path(__file__).parent
SCHEDULE_PATH = CONFIG_DIR / "jobs.json"
QB_CONFIG_PATH = CONFIG_DIR / "config.json"
JOBS_REGISTRY: Dict[str, JobConfig] = load_merged_registry(SCHEDULE_PATH, QB_CONFIG_PATH)