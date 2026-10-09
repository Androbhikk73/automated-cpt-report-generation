import os
import csv
import logging
import requests
from dotenv import load_dotenv

def API_Extract(job_name: str, destination_path: str, table_id: str, clist: str, where_clause: str) -> None:
    load_dotenv()

    realm_hostname = os.environ.get("QB_REALM_HOSTNAME") or os.getenv("QB_REALM_HOSTNAME") or ""
    user_token = os.environ.get("QB_USER_TOKEN") or os.getenv("QB_USER_TOKEN") or ""

    logging.info(f"HOST: {realm_hostname} with TOKEN: {user_token}")

    if not realm_hostname or not user_token:
        raise EnvironmentError("Quickbase credentials missing.")

    url = f"https://api.quickbase.com/v1/records/query"

    headers = {
        "QB-Realm-Hostname": realm_hostname,
        "Authorization": f"QB-USER-TOKEN {user_token}",
        "Content-Type": "application/json"
    }

    select_fields = [int(fid.strip()) for fid in clist.split(".")] if clist else []
    all_records = []
    field_metadata = []
    skip = 0

    logging.info(f"[{job_name}] Initiating QuickBase API extraction for table {table_id}")

    while True:
        payload = {
            "from": table_id,
            "select": select_fields,
            "where": where_clause,
            "options": {
                "skip": skip
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()

        if skip == 0:
            field_metadata = response_json.get("fields", [])

        data_chunk = response_json.get("data", [])
        if not data_chunk:
            break

        all_records.extend(data_chunk)

        num_records = response_json.get("metadata", {}).get("numRecords", 0)

        logging.info(f"[{job_name}] Fetched {num_records} records (Skip: {skip})...")

        if num_records == 0:
            break

        skip += num_records

    # Write to CSV
    logging.info(f"[{job_name}] Total records extracted: {len(all_records)}. Writing to {destination_path}")

    with open(destination_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        header_row = [field.get("label", f"Field_{field.get('id')}") for field in field_metadata]
        writer.writerow(header_row)

        field_ids = [str(field.get("id")) for field in field_metadata]

        for record in all_records:
            row = []
            for fid in field_ids:
                cell_data = record.get(fid, {}).get("value", "")

                if isinstance(cell_data, (list, dict)):
                    cell_data = str(cell_data)

                row.append(cell_data)

            writer.writerow(row)

    logging.info(f"[{job_name}] CSV successfully generated at {destination_path}")