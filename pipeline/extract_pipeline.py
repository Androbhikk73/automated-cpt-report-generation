import logging
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from config.job_config import JobConfig
from core.job_processor import QuickBaseJobProcessor

class QuickBaseExtractPipeline:
    def __init__(self, environment: str, schedule_time_str: str, jobs_registry: Dict[str, JobConfig]) -> None:
        self.environment = environment.upper()
        self.schedule_time_str = schedule_time_str
        self.jobs_registry = jobs_registry

    def _determine_execution_time(self) -> datetime:
        now = datetime.now()
        if self.schedule_time_str == "0":
            return now
        parsed_time = datetime.strptime(self.schedule_time_str, "%H:%M:%S")
        return now.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=parsed_time.second,
            microsecond=0
        )

    def get_scheduled_jobs(self) -> List[JobConfig]:
        if self.schedule_time_str == "0":
            return list(self.jobs_registry.values())

        current_time = self._determine_execution_time()
        matched_jobs = []

        for job in self.jobs_registry.values():
            if not job.scheduled_time:
                matched_jobs.append(job)
                continue

            parsed_job_time = datetime.strptime(job.scheduled_time, "%H:%M:%S")
            job_target_time = current_time.replace(
                hour=parsed_job_time.hour,
                minute=parsed_job_time.minute,
                second=parsed_job_time.second
            )

            if abs(current_time - job_target_time) < timedelta(minutes=5):
                matched_jobs.append(job)

        return matched_jobs

    def run(self) -> None:
        matched_jobs = self.get_scheduled_jobs()
        if not matched_jobs:
            logging.info("No matching jobs found for current schedule")
            return

        # Requirement 5: dev runs go to a temp folder that gets deleted at the end, even when it fails
        temp_dev_dir: Optional[Path] = None
        if self.environment == "DEV":
            temp_dev_dir = Path(tempfile.mkdtemp(prefix="cpt_dev_run_"))
            logging.info(f"[DEV] Created temporary output folder: {temp_dev_dir}")

        completed_jobs = []
        try:
            for job_config in matched_jobs:
                try:
                    processor = QuickBaseJobProcessor(job_config, override_output_dir=temp_dev_dir)
                    output_path = processor.execute()
                    completed_jobs.append(job_config.name_id)
                    logging.info(f"Job '{job_config.name_id}' finished successfully -> {output_path}")
                except Exception as ex:
                    logging.error(f"Job '{job_config.name_id}' failed: {ex}", exc_info=True)
                    raise
        finally:
            if temp_dev_dir and temp_dev_dir.exists():
                shutil.rmtree(temp_dev_dir, ignore_errors=True)
                logging.info(f"[DEV] Cleaned up temporary output folder: {temp_dev_dir}")

        logging.info(f"Batch completed: {len(completed_jobs)} job(s) processed ({', '.join(completed_jobs)}).")