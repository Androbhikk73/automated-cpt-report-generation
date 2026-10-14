import sys
import logging
from config.job_registry import JOBS_REGISTRY
from pipeline.extract_pipeline import QuickBaseExtractPipeline
from utils.logger import setup_logger

def main():
    env = sys.argv[1].upper() if len(sys.argv) > 1 else "DEV"
    sched_time = sys.argv[2] if len(sys.argv) > 2 else "0"

    setup_logger()
    logging.info(f"Starting QuickBase pipeline execution | Environment: {env} | Schedule Time: {sched_time}")

    try:
        pipeline = QuickBaseExtractPipeline(environment = env, schedule_time_str = sched_time, jobs_registry = JOBS_REGISTRY)
        pipeline.run()
        logging.info("Pipeline execution completed successfully.")

    except Exception as ex:
        logging.error(f"Pipeline execution failed for schedule '{sched_time}': {ex}", exc_info = True)
        sys.exit(1)

if __name__ == "__main__":
    main()