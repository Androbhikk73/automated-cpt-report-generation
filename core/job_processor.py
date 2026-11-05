import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from core import quickbase_export_api
from config.job_config import JobConfig

class QuickBaseJobProcessor:
    def __init__(self, config: JobConfig, override_output_dir: Optional[Path] = None) -> None:
        self.config = config
        self.override_output_dir = override_output_dir

    def _resolve_where_clause(self, raw_where: str) -> str:
        if not raw_where:
            return ""
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = datetime.now().strftime("%Y-%m-%d")
        return (
            raw_where
            .replace("<run date minus 1>", yesterday_str)
            .replace("<run date>", today_str)
        )

    def execute(self) -> Path:
        logging.info(f"Starting Job: {self.config.name_id}")

        date_str = datetime.now().strftime(self.config.date_stamp_format)
        filename = f"{self.config.destination_file_mask}{date_str}{self.config.export_file_extension}"

        dest_dir = self.override_output_dir or Path(self.config.destination_folder_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        resolved_where = self._resolve_where_clause(self.config.where_clause or "")

        # Requirement 4: Do not delete existing file before the pull; write once straight to output
        quickbase_export_api.API_Extract(
            job_name=self.config.name_id,
            destination_path=str(dest_path),
            table_id=str(self.config.table_id),
            select_fields=self.config.select_fields,
            where_clause=resolved_where,
            field_labels=self.config.field_labels,
            sort_by=self.config.sort_by,
            transforms=self.config.transforms,
            header_only_when_empty=self.config.header_only_when_empty
        )

        logging.info(f"Completed Job: {self.config.name_id} -> Output: {dest_path}")
        return dest_path