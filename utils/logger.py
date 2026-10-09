import os
import logging
from pathlib import Path

def setup_logger():
    log_dir = Path(r"D:\Python\cpt_report_kousik\logs")
    log_dir.mkdir(parents = True, exist_ok = True)
    os.chdir(log_dir)

    logging.basicConfig(
        filename = "quickbase_export_extract.log",
        format = "%(asctime)s %(levelname)-8s %(message)s",
        level = logging.INFO,
        datefmt = "%Y-%m-%d %H:%M:%S",
        force = True)