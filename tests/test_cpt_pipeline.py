import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from config.job_config import JobConfig
from core.csv_transformer import CSVTransformer
from core.quickbase_export_api import API_Extract
from pipeline.extract_pipeline import QuickBaseExtractPipeline


class TestCPTTransformAndPaging(unittest.TestCase):
    def test_individual_cleanups_match_edw_exactly(self):
        # 1. comma_lists_to_semicolons: only replaces ' , ' with ;
        val1 = "['A' , 'B', 'C']"
        res1 = CSVTransformer.clean_text_values(val1, ["comma_lists_to_semicolons"])
        self.assertEqual(res1, "['A;B;C']")

        # 2. strip_brackets_and_quotes: strips [ ] and ', keeps double quotes "
        val2 = "['A;B'; \"quoted\"]"
        res2 = CSVTransformer.clean_text_values(val2, ["strip_brackets_and_quotes"])
        self.assertEqual(res2, 'A;B; "quoted"')

        # 3. collapse_semicolons: replaces ; ; and ;; with empty string, does NOT trim trailing ;
        val3 = "A;;B; ;C;"
        res3 = CSVTransformer.clean_text_values(val3, ["collapse_semicolons"])
        self.assertEqual(res3, "ABC;")

    @patch("core.quickbase_export_api.requests.post")
    @patch.dict("os.environ", {"QB_REALM_HOSTNAME": "test.quickbase.com", "QB_USER_TOKEN": "token123"})
    def test_cursor_paging_and_exact_csv_output(self, mock_post):
        fields_meta = [
            {"id": 3, "label": "Record ID#", "type": "recordid"},
            {"id": 6, "label": "ONP Initiated Date", "type": "date"},
            {"id": 7, "label": "IDR Initiated Date", "type": "date"},
            {"id": 8, "label": "Invoice", "type": "text"},
            {"id": 9, "label": "CPT Code", "type": "text"},
            {"id": 10, "label": "Transaction Sequence", "type": "text"},
            {"id": 11, "label": "IDR Case Number", "type": "text"},
            {"id": 12, "label": "Pre-Arbitration Total Allowed Amount", "type": "text"},
            {"id": 13, "label": "Pre-Arbitration PT Resp", "type": "text"},
            {"id": 14, "label": "Expected After Finalization Arbitration", "type": "text"},
            {"id": 15, "label": "Result", "type": "text"},
            {"id": 16, "label": "Date Finalized", "type": "date"},
            {"id": 17, "label": "Date Pmt Expected", "type": "date"},
            {"id": 18, "label": "Extra Field", "type": "text"},
        ]

        page1 = MagicMock(ok=True, status_code=200)
        page1.json.return_value = {
            "fields": fields_meta,
            "data": [
                {
                    "3": {"value": 101},
                    "6": {"value": "2026-10-01"},
                    "7": {"value": "2026-10-02"},
                    "8": {"value": "INV-1"},
                    "9": {"value": "['99284' , '99285']"},
                    "10": {"value": 1},
                    "11": {"value": "CASE-\"1\""},
                    "12": {"value": 500.0},
                    "13": {"value": 50.0},
                    "14": {"value": 750.0},
                    "15": {"value": "Win;;"},
                    "16": {"value": "2026-10-10"},
                    "17": {"value": "2026-10-25"},
                    "18": {"value": "Ignored"},
                }
            ],
            "metadata": {"totalRecords": 2, "numRecords": 1},
        }

        page2 = MagicMock(ok=True, status_code=200)
        page2.json.return_value = {
            "fields": fields_meta,
            "data": [
                {
                    "3": {"value": 105},
                    "6": {"value": "2026-10-03"},
                    "7": {"value": "2026-10-04"},
                    "8": {"value": "INV-2"},
                    "9": {"value": "['00100']"},
                    "10": {"value": 2},
                    "11": {"value": "CASE-2"},
                    "12": {"value": 300.0},
                    "13": {"value": 30.0},
                    "14": {"value": 450.0},
                    "15": {"value": "Settled;"},
                    "16": {"value": "2026-10-12"},
                    "17": {"value": "2026-10-27"},
                    "18": {"value": "Ignored"},
                }
            ],
            "metadata": {"totalRecords": 1, "numRecords": 1},
        }

        mock_post.side_effect = [page1, page2]

        field_labels = {
            "6": "ONP Initiated Date",
            "7": "IDR Initiated Date",
            "8": "Invoice",
            "9": "CPT Code",
            "10": "Transaction Sequence",
            "11": "IDR Case Number",
            "12": "Pre-Arbitration Total Allowed Amount",
            "13": "Pre-Arbitration PT Resp",
            "14": "Expected After Finalization Arbitration",
            "15": "Result (Win/Loss/Settled/Closed/Withdrawn)",
            "16": "Date Finalized",
            "17": "Date Pmt Expected",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            out_csv = Path(tmpdir) / "out.csv"
            field_types = API_Extract(
                job_name="CPT",
                destination_path=str(out_csv),
                table_id="bvtwb6zyg",
                select_fields=[3, *range(6, 19)],
                where_clause="{19.EX.'2026-11-03'}",
                field_labels=field_labels,
                sort_by=3,
            )

            # Verify field types for 6-17 returned accurately
            self.assertEqual(len(field_types), 12)
            self.assertEqual(field_types[6], "date")
            self.assertEqual(field_types[9], "text")

            # Verify 1st call and 2nd call cursor filter ({3.GT.101}) and no 'skip' option
            first_payload = mock_post.call_args_list[0].kwargs["json"]
            second_payload = mock_post.call_args_list[1].kwargs["json"]
            self.assertEqual(first_payload["where"], "{19.EX.'2026-11-03'}")
            self.assertEqual(second_payload["where"], "({19.EX.'2026-11-03'}AND{3.GT.101})")
            self.assertNotIn("skip", first_payload.get("options", {}))

            with open(out_csv, "r", encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))

            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0], list(field_labels.values()))
            self.assertEqual(
                rows[1],
                ["2026-10-01", "2026-10-02", "INV-1", "99284;99285", "1", 'CASE-"1"', "500.0", "50.0", "750.0", "Win", "2026-10-10", "2026-10-25"],
            )
            self.assertEqual(
                rows[2],
                ["2026-10-03", "2026-10-04", "INV-2", "00100", "2", "CASE-2", "300.0", "30.0", "450.0", "Settled;", "2026-10-12", "2026-10-27"],
            )

    @patch("core.quickbase_export_api.requests.post")
    @patch.dict("os.environ", {"QB_REALM_HOSTNAME": "test.quickbase.com", "QB_USER_TOKEN": "token123"})
    def test_fails_on_duplicate_record_id_or_total_mismatch(self, mock_post):
        dup_page = MagicMock(ok=True, status_code=200)
        dup_page.json.return_value = {
            "fields": [{"id": 3, "type": "recordid"}],
            "data": [{"3": {"value": 10}}, {"3": {"value": 10}}],
            "metadata": {"totalRecords": 2, "numRecords": 2},
        }
        mock_post.return_value = dup_page

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(RuntimeError, "Duplicate Record ID"):
                API_Extract("CPT", str(Path(tmpdir) / "dup.csv"), "tbl", [3], "{19.EX.'2026-11-03'}")

        # Test totalRecords mismatch
        mismatch_page1 = MagicMock(ok=True, status_code=200)
        mismatch_page1.json.return_value = {
            "fields": [{"id": 3, "type": "recordid"}],
            "data": [{"3": {"value": 10}}],
            "metadata": {"totalRecords": 2, "numRecords": 1},
        }
        mismatch_page2 = MagicMock(ok=True, status_code=200)
        mismatch_page2.json.return_value = {"fields": [], "data": [], "metadata": {"totalRecords": 0, "numRecords": 0}}
        mock_post.side_effect = [mismatch_page1, mismatch_page2]

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(RuntimeError, "Record count mismatch"):
                API_Extract("CPT", str(Path(tmpdir) / "mismatch.csv"), "tbl", [3], "{19.EX.'2026-11-03'}")

    @patch("pipeline.extract_pipeline.logging.error")
    @patch("pipeline.extract_pipeline.QuickBaseJobProcessor")
    def test_dev_temp_folder_deleted_even_on_failure(self, mock_processor_cls, _mock_log_error):
        captured_temp_dir = []

        def fail_execute():
            raise RuntimeError("Simulated API Failure")

        def side_effect(job_config, override_output_dir=None):
            captured_temp_dir.append(override_output_dir)
            instance = MagicMock()
            instance.execute.side_effect = fail_execute
            return instance

        mock_processor_cls.side_effect = side_effect

        dummy_config = JobConfig(
            name_id="CPT",
            date_stamp_format="%Y%m%d",
            scheduled_time="",
            scheduled_type="OnDemand",
            export_file_mask="CPTLevelRpt_",
            export_file_extension=".csv",
            destination_file_mask="CPTLevelRpt_",
            destination_folder_path="./reports",
            table_id="bvtwb6zyg",
        )

        pipeline = QuickBaseExtractPipeline("DEV", "0", {"CPT": dummy_config})
        with self.assertRaisesRegex(RuntimeError, "Simulated API Failure"):
            pipeline.run()

        self.assertEqual(len(captured_temp_dir), 1)
        self.assertIsNotNone(captured_temp_dir[0])
        self.assertFalse(captured_temp_dir[0].exists())


if __name__ == "__main__":
    unittest.main()