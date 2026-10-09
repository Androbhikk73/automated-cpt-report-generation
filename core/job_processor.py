import logging
import shutil
from datetime import datetime
from pathlib import Path
from core import quickbase_export_api
from config.job_config import JobConfig
from core.csv_transformer import CSVTransformer

class QuickBaseJobProcessor:
    def __init__(self, config: JobConfig) -> None:
        self.config = config

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
        clist = ""
        if self.config.field_labels:
            clist = ".".join(self.config.field_labels.keys())

        # Extract from Quickbase API
        quickbase_export_api.API_Extract(
            job_name = self.config.name_id,
            destination_path = str(staging_path),
            table_id = str(self.config.table_id),
            clist = clist,
            where_clause = str(self.config.where_clause)
        )

        # Transform CSV
        zip_col = None
        if self.config.export_file_mask == "IDRPortalExtract":
            zip_col = "Combined Text QDE_PlanIssuer_ReferenceFormula - PlanIssuer_Zip"

        CSVTransformer.transform_file(staging_path, fix_zip_column = zip_col)

        # Move to Destination
        shutil.copy(str(staging_path), str(dest_path))
        logging.info(f"Completed Job: {self.config.name_id} -> Output: {dest_path}")

        return dest_path