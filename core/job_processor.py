import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from core import quickbase_export_api
from config.job_config import JobConfig
from core.csv_transformer import CSVTransformer

class QuickBaseJobProcessor:
    def __init__(self, config: JobConfig) -> None:
        self.config = config

    def _resolve_where_clause(self, raw_where: str) -> str:
        """Replaces placeholders like '<run date minus 1>' with actual dates (YYYY-MM-DD)."""
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

        # Compute formatted filenames based on config rules
        date_str = datetime.now().strftime(self.config.date_stamp_format)
        filename = f"{self.config.destination_file_mask}{date_str}{self.config.export_file_extension}"
        staging_dir = Path(self.config.staging_folder_path)
        dest_dir = Path(self.config.destination_folder_path)

        staging_dir.mkdir(parents=True, exist_ok=True)
        dest_dir.mkdir(parents=True, exist_ok=True)

        staging_path = staging_dir / filename
        dest_path = dest_dir / filename

        if staging_path.exists():
            staging_path.unlink()

        if dest_path.exists():
            dest_path.unlink()

        # Construct Dynamic QuickBase API Parameters
        clist = ".".join(self.config.field_labels.keys()) if self.config.field_labels else ""
        resolved_where = self._resolve_where_clause(self.config.where_clause or "")

        # Extract from Quickbase API
        quickbase_export_api.API_Extract(
            job_name=self.config.name_id,
            destination_path=str(staging_path),
            table_id=str(self.config.table_id),
            clist=clist,
            where_clause=resolved_where,
            field_labels=self.config.field_labels,
            sort_by=self.config.sort_by,
            header_only_when_empty=self.config.header_only_when_empty
        )

        # Transform CSV
        zip_col = None
        if self.config.export_file_mask == "IDRPortalExtract":
            zip_col = "Combined Text QDE_PlanIssuer_ReferenceFormula - PlanIssuer_Zip"

        CSVTransformer.transform_file(
            staging_path,
            transforms=self.config.transforms,
            fix_zip_column=zip_col
        )

        # Copy to Destination & Clean up staging
        if staging_path.exists():
            shutil.copy(str(staging_path), str(dest_path))
            staging_path.unlink()

        logging.info(f"Completed Job: {self.config.name_id} -> Output: {dest_path}")

        return dest_path