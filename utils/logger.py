import os
import logging
from pathlib import Path

def setup_logger():
    base_dir = Path(__file__).resolve().parent.parent
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents = True, exist_ok = True)
    os.chdir(log_dir)

    logging.basicConfig(
        filename = "quickbase_export_extract.log",
        format = "%(asctime)s %(levelname)-8s %(message)s",
        level = logging.INFO,
        datefmt = "%Y-%m-%d %H:%M:%S",
        force = True)