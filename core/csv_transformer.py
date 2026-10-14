import re
import csv
from pathlib import Path
from typing import Optional, List

class CSVTransformer:
    @staticmethod
    def clean_text_values(value: str, transforms: Optional[List[str]] = None) -> str:
        if not transforms:
            transforms = [
                "comma_lists_to_semicolons",
                "strip_brackets_and_quotes",
                "collapse_semicolons"
            ]

        cleaned = value
        for step in transforms:
            if step == "comma_lists_to_semicolons":
                cleaned = re.sub(r"'\s*,\s*'", ";", cleaned)
                cleaned = re.sub(r'"\s*,\s*"', ";", cleaned)
            elif step == "strip_brackets_and_quotes":
                cleaned = cleaned.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
            elif step == "collapse_semicolons":
                cleaned = re.sub(r";(?:\s*;)+", ";", cleaned)
                cleaned = cleaned.strip(";")

        return cleaned

    @classmethod
    def transform_file(
        cls,
        source_path: Path,
        transforms: Optional[List[str]] = None,
        fix_zip_column: Optional[str] = None,
        zip_prefix: str = "0"
    ) -> Path:
        if not source_path.exists():
            return source_path

        temp_path = source_path.with_name(f"{source_path.stem}_cleaned{source_path.suffix}")

        with open(source_path, mode="r", newline="", encoding="utf-8") as infile, \
             open(temp_path, mode="w", newline="", encoding="utf-8") as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            try:
                header = next(reader)
            except StopIteration:
                return source_path

            writer.writerow(header)

            zip_idx = None
            if fix_zip_column:
                for i, col in enumerate(header):
                    if fix_zip_column.lower() in col.lower():
                        zip_idx = i
                        break

            for row in reader:
                cleaned_row = []
                for idx, value in enumerate(row):
                    cell_val = cls.clean_text_values(value, transforms=transforms)

                    if zip_idx is not None and idx == zip_idx:
                        if len(cell_val) == 4:
                            cell_val = f"'{zip_prefix}{cell_val}'"
                        elif cell_val.startswith("0"):
                            cell_val = f"'{cell_val}'"

                    cleaned_row.append(cell_val)

                writer.writerow(cleaned_row)

        if source_path.exists():
            source_path.unlink()

        temp_path.rename(source_path)

        return source_path