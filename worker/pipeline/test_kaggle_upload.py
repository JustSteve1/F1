"""Unit tests for the Kaggle publish step (no network)."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

import kaggle_metadata as meta
import kaggle_upload as upload


COLUMN_ORDER = [field["name"] for field in meta.COLUMN_FIELDS]


class DownloadMatcherTests(unittest.TestCase):
    def test_accepts_stable_and_legacy_names(self) -> None:
        self.assertTrue(upload.is_kaggle_laps_csv("all_laps.csv"))
        self.assertTrue(upload.is_kaggle_laps_csv("All Laps - 24 October 2026.csv"))
        self.assertTrue(upload.is_kaggle_laps_csv("/tmp/All Laps - 11 October 2026.csv"))
        self.assertFalse(upload.is_kaggle_laps_csv("dataset-metadata.json"))
        self.assertFalse(upload.is_kaggle_laps_csv("notes.txt"))


class MetadataBuilderTests(unittest.TestCase):
    def test_scores_named_license_tags_provenance_and_schema(self) -> None:
        with patch.dict(os.environ, {"KAGGLE_DATASET_ID": "9485317"}, clear=False):
            os.environ.pop("KAGGLE_LICENSE", None)
            os.environ.pop("KAGGLE_KEYWORDS", None)
            os.environ.pop("KAGGLE_DATASET", None)
            built = upload.build_dataset_metadata(
                existing={
                    "title": "Keep this title",
                    "subtitle": "Existing subtitle that is long enough!!",
                    "description": "# Live card",
                }
            )

        self.assertEqual(built["id"], "stevefza/f1-2026-bahrain-testing-day-2")
        self.assertEqual(built["id_no"], 9485317)
        self.assertEqual(built["licenses"], [{"name": "CC-BY-4.0"}])
        self.assertEqual(
            built["keywords"],
            ["sports", "time series analysis", "tabular", "beginner"],
        )
        self.assertEqual(built["expectedUpdateFrequency"], "weekly")
        self.assertIn("FastF1", built["userSpecifiedSources"])
        self.assertIn("not an official", built["userSpecifiedSources"].lower())
        self.assertEqual(built["title"], "Keep this title")
        self.assertEqual(built["description"], "# Live card")
        resource = built["resources"][0]
        self.assertEqual(resource["path"], "all_laps.csv")
        self.assertIn("2 Hz", resource["description"])
        self.assertEqual(
            [field["name"] for field in resource["schema"]["fields"]],
            COLUMN_ORDER,
        )


class UploadToKaggleTests(unittest.TestCase):
    def test_writes_stable_csv_and_metadata_then_calls_both_apis(self) -> None:
        frame = pd.DataFrame([{column: 0 for column in COLUMN_ORDER}])
        captured: dict = {}

        def create_version(folder, notes, quiet=False, convert_to_csv=False):
            captured["folder"] = folder
            captured["notes"] = notes
            captured["files"] = set(os.listdir(folder))
            captured["meta"] = json.loads(
                Path(folder, "dataset-metadata.json").read_text(encoding="utf-8")
            )
            captured["header"] = Path(folder, "all_laps.csv").read_text(encoding="utf-8").splitlines()[0]

        api = MagicMock()
        api.dataset_create_version.side_effect = create_version
        api.dataset_metadata_update.side_effect = lambda handle, folder: captured.setdefault(
            "update", (handle, folder)
        )

        with patch.dict(os.environ, {"KAGGLE_DATASET_ID": "9485317"}, clear=False):
            os.environ.pop("KAGGLE_LICENSE", None)
            os.environ.pop("KAGGLE_DATASET", None)
            with (
                patch.object(upload, "ensure_kaggle_auth"),
                patch.object(
                    upload,
                    "resolve_dataset_handle",
                    return_value="stevefza/f1-2026-bahrain-testing-day-2",
                ),
                patch.object(
                    upload,
                    "fetch_existing_card_metadata",
                    return_value={
                        "title": "Keep this title",
                        "subtitle": "Existing subtitle that is long enough!!",
                        "description": "# Live card",
                    },
                ),
            ):
                upload.upload_to_kaggle(frame, api=api)

        self.assertEqual(
            captured["files"],
            {"all_laps.csv", "dataset-metadata.json"},
        )
        self.assertEqual(captured["header"].split(","), COLUMN_ORDER)
        self.assertEqual(captured["meta"]["licenses"], [{"name": "CC-BY-4.0"}])
        self.assertEqual(captured["meta"]["resources"][0]["path"], "all_laps.csv")
        self.assertEqual(
            [field["name"] for field in captured["meta"]["resources"][0]["schema"]["fields"]],
            COLUMN_ORDER,
        )
        self.assertEqual(captured["meta"]["description"], "# Live card")
        self.assertTrue(captured["notes"].startswith("Auto-update: 1 laps as of "))
        self.assertEqual(
            captured["update"],
            ("stevefza/f1-2026-bahrain-testing-day-2", captured["folder"]),
        )
        api.dataset_create_version.assert_called_once()
        api.dataset_metadata_update.assert_called_once()


if __name__ == "__main__":
    unittest.main()
