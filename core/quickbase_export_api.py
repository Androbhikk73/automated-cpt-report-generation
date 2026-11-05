import os
import csv
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
from core.csv_transformer import CSVTransformer

def _build_paged_where(base_where: str, sort_field_id: int, last_id: Optional[int]) -> str:
    if last_id is None:
        return base_where
    cursor_clause = f"{{{sort_field_id}.GT.{last_id}}}"
    if not base_where:
        return cursor_clause
    return f"({base_where}AND{cursor_clause})"

def API_Extract(
    job_name: str,
    destination_path: str,
    table_id: str,
    select_fields: List[int],
    where_clause: str,
    field_labels: Optional[Dict[str, str]] = None,
    sort_by: int = 3,
    transforms: Optional[List[str]] = None,
    header_only_when_empty: bool = True
) -> Dict[int, str]:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    realm_hostname = (os.getenv("QB_REALM_HOSTNAME") or "").strip().strip("'").strip('"')
    user_token = (os.getenv("QB_USER_TOKEN") or "").strip().strip("'").strip('"')

    if not realm_hostname or not user_token:
        raise EnvironmentError("Quickbase credentials missing.")

    url = "https://api.quickbase.com/v1/records/query"
    headers = {
        "QB-Realm-Hostname": realm_hostname,
        "Authorization": f"QB-USER-TOKEN {user_token}",
        "Content-Type": "application/json"
    }

    # Ensure field 3 and 6-18 are selected
    query_select = list(dict.fromkeys(select_fields or [3, *range(6, 19)]))
    if sort_by not in query_select:
        query_select.insert(0, sort_by)

    all_records = []
    seen_ids = set()
    field_metadata = []
    expected_total_records: Optional[int] = None
    last_id: Optional[int] = None
    sort_fid_str = str(sort_by)

    logging.info(f"[{job_name}] Initiating QuickBase API extraction for table {table_id}")

    while True:
        paged_where = _build_paged_where(where_clause, sort_by, last_id)
        payload = {
            "from": table_id,
            "select": query_select,
            "where": paged_where,
            "sortBy": [{"fieldId": int(sort_by), "order": "ASC"}],
            "options": {"top": 1000}
        }

        max_retries = 4
        response: Optional[requests.Response] = None
        for attempt in range(1, max_retries + 1):
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            if response.status_code in (429, 502, 503, 504) and attempt < max_retries:
                wait_seconds = 2 ** attempt  # 2s, 4s, 8s
                logging.warning(
                    f"[{job_name}] QuickBase returned {response.status_code} "
                    f"(Attempt {attempt}/{max_retries}): {response.text}. "
                    f"Retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
                continue
            break

        if response is None:
            raise RuntimeError(f"[{job_name}] Failed to receive a response from QuickBase.")

        if not response.ok:
            logging.error(f"[{job_name}] QuickBase API Error ({response.status_code}): {response.text}")
        response.raise_for_status()
        response_json = response.json()

        metadata = response_json.get("metadata", {})
        if expected_total_records is None:
            field_metadata = response_json.get("fields", [])
            expected_total_records = metadata.get("totalRecords", metadata.get("numRecords", 0))

        data_chunk = response_json.get("data", [])
        if not data_chunk:
            break

        for record in data_chunk:
            raw_id = record.get(sort_fid_str, {}).get("value")
            if raw_id is None:
                raise RuntimeError(f"[{job_name}] Record missing sort/page field ID {sort_by}.")
            rec_id = int(raw_id)
            if rec_id in seen_ids:
                raise RuntimeError(f"[{job_name}] Duplicate Record ID detected during paging: {rec_id}")
            seen_ids.add(rec_id)
            last_id = rec_id
            all_records.append(record)

        num_records = metadata.get("numRecords", len(data_chunk))
        logging.info(f"[{job_name}] Fetched {num_records} records (last_id={last_id}, total so far={len(all_records)}/{expected_total_records})")

        if len(all_records) >= (expected_total_records or 0):
            break

    # Validate total count matches totalRecords from first query
    if expected_total_records is not None and len(all_records) != expected_total_records:
        raise RuntimeError(
            f"[{job_name}] Record count mismatch: extracted {len(all_records)} records, "
            f"expected totalRecords={expected_total_records}"
        )

    # Requirement 7: Log field types for fields 6-17 (types only, no values)
    field_types_6_to_17 = {
        int(f["id"]): f.get("type") or f.get("fieldType") or "unknown"
        for f in field_metadata
        if f.get("id") in range(6, 18)
    }
    logging.info(f"[{job_name}] Field types for 6-17 (types only): {dict(sorted(field_types_6_to_17.items()))}")

    if not all_records and not header_only_when_empty:
        logging.info(f"[{job_name}] No records found and header_only_when_empty=False. Skipping file write.")
        return field_types_6_to_17

    # Requirement 4: Write file once, straight to output folder, applying cleanups in memory
    if field_labels:
        output_field_ids = list(field_labels.keys())
        header_row = [field_labels[fid] for fid in output_field_ids]
    else:
        output_field_ids = [str(f.get("id")) for f in field_metadata if f.get("id") in range(6, 18)]
        header_row = []
        for f in field_metadata:
            if str(f.get("id")) in output_field_ids:
                fid_val = f.get("id")
                header_row.append(f.get("label", f"Field_{fid_val}"))

    with open(destination_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header_row)

        for record in all_records:
            row = []
            for fid in output_field_ids:
                cell_data = record.get(fid, {}).get("value", "")
                if cell_data is None:
                    cell_data = ""
                elif isinstance(cell_data, (list, dict)):
                    cell_data = str(cell_data)
                else:
                    cell_data = str(cell_data)

                cleaned_val = CSVTransformer.clean_text_values(cell_data, transforms=transforms)
                row.append(cleaned_val)

            writer.writerow(row)

    logging.info(f"[{job_name}] CSV successfully generated at {destination_path} ({len(all_records)} rows)")
    return field_types_6_to_17