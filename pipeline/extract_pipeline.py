import logging
from datetime import datetime, timedelta
from typing import Dict, List
from config.job_config import JobConfig
from core.job_processor import QuickBaseJobProcessor

class QuickBaseExtractPipeline:
    def __init__(self, environment: str, schedule_time_str: str, jobs_registry: Dict[str, JobConfig]) -> None:
        self.environment = environment
        self.schedule_time_str = schedule_time_str
        self.jobs_registry = jobs_registry
        self.recipients_success = "kousik.kayal@usap.com"
        self.recipients_failure = "kousik.kayal@usap.com"

    def _determine_execution_time(self) -> datetime:
        now = datetime.now()
        if self.schedule_time_str == "0":
            return now

        parsed_time = datetime.strptime(self.schedule_time_str, "%H:%M:%S")

        return now.replace(
            hour = parsed_time.hour,
            minute = parsed_time.minute,
            second = parsed_time.second,
            microsecond = 0
        )

    def get_scheduled_jobs(self) -> List[JobConfig]:
        current_time = self._determine_execution_time()
        matched_jobs = []

        for job in self.jobs_registry.values():
            parsed_job_time = datetime.strptime(job.scheduled_time, "%H:%M:%S")
            job_target_time = current_time.replace(
                hour = parsed_job_time.hour,
                minute = parsed_job_time.minute,
                second = parsed_job_time.second
            )

            if abs(current_time - job_target_time) < timedelta(minutes = 5):
                matched_jobs.append(job)

        return matched_jobs

    def run(self):
        matched_jobs = self.get_scheduled_jobs()
        if not matched_jobs:
            logging.info("No matching jobs found for current schedule")
            return

        completed_jobs = []
        for job_config in matched_jobs:
            try:
                processor = QuickBaseJobProcessor(job_config)
                output_path = processor.execute()
                completed_jobs.append(job_config.name_id)
                logging.info(f"Job '{job_config.name_id}' finished successfully -> {output_path}")
            except Exception as ex:
                logging.error(f"Job '{job_config.name_id}' failed: {ex}", exc_info=True)
                raise

        # sending email for success
        # if completed_jobs:
        #     jobs_str = "|".join(completed_jobs)
        #     Azure_Email_Notification.email_notification(self.recipients_success, "arbitration quickbase_export_extract", self.environment, "Complete", f"arbitration quickbase_export_extract: {jobs_str} is done", "", "")

        logging.info(f"Batch completed: {len(completed_jobs)} job(s) processed ({', '.join(completed_jobs)}).")