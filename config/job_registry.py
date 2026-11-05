import re
import yaml
from pathlib import Path
from typing import Dict
from config.job_config import JobConfig

def _parse_file_pattern(file_name_pattern: str):
    path_obj = Path(file_name_pattern)
    ext = path_obj.suffix
    stem = path_obj.stem

    match = re.search(r"<([^>]+)>", stem)
    if match:
        token = match.group(1)
        py_fmt = token.replace("yyyy", "%Y").replace("MM", "%m").replace("dd", "%d")
        mask = stem[:match.start()]
    else:
        py_fmt = "%Y%m%d"
        mask = stem

    return mask, py_fmt, ext

def load_yaml_registry(job_yaml_path: Path, overlay_yaml_path: Path) -> Dict[str, JobConfig]:
    if not job_yaml_path.exists():
        raise FileNotFoundError(f"Job YAML config not found at: {job_yaml_path}")
    if not overlay_yaml_path.exists():
        raise FileNotFoundError(f"Overlay YAML config not found at: {overlay_yaml_path}")

    with open(job_yaml_path, "r", encoding="utf-8") as f:
        job_data = yaml.safe_load(f) or {}

    with open(overlay_yaml_path, "r", encoding="utf-8") as f:
        overlay_data = yaml.safe_load(f) or {}

    job_name = job_data.get("job", "DEFAULT_JOB")
    source = job_data.get("source", {})
    output = job_data.get("output", {})
    transforms = job_data.get("transforms", [])
    schedule = job_data.get("schedule", {}) or {}

    file_name_pattern = output.get("file_name", f"{job_name}_<yyyyMMdd>.csv")
    mask, date_fmt, ext = _parse_file_pattern(file_name_pattern)

    columns = output.get("columns", [])
    field_labels = {str(col["field"]): col["header"] for col in columns}

    # Ensure fields 3 and 6-18 are selected as required
    raw_fields = source.get("fields", [3, *range(6, 19)])
    select_fields = [int(fid) for fid in raw_fields]
    if 3 not in select_fields:
        select_fields.insert(0, 3)

    drop_location = overlay_data.get("drop_location", "./output")

    config = JobConfig(
        name_id=job_name,
        date_stamp_format=date_fmt,
        scheduled_time=schedule.get("time", ""),
        scheduled_type=schedule.get("type", "OnDemand"),
        export_file_mask=mask,
        export_file_extension=ext,
        destination_file_mask=mask,
        destination_folder_path=drop_location,
        table_id=overlay_data.get("table_id"),
        app_id=overlay_data.get("app_id"),
        where_clause=source.get("filter"),
        sort_by=int(source.get("sort_by", 3)),
        select_fields=select_fields,
        field_labels=field_labels,
        transforms=transforms,
        header_only_when_empty=output.get("header_only_when_empty", True)
    )

    return {job_name: config}

BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = BASE_DIR / "jobs"
CPT_YAML_PATH = JOBS_DIR / "cpt_config.yml"
OVERLAYS_YAML_PATH = JOBS_DIR / "overlays.yml"

JOBS_REGISTRY: Dict[str, JobConfig] = load_yaml_registry(CPT_YAML_PATH, OVERLAYS_YAML_PATH)