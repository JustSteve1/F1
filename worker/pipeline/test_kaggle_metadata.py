"""Unit tests for Kaggle usability metadata (no network)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kaggle_metadata as meta


class IsKaggleLapsCsvTests(unittest.TestCase):
    def test_stable_and_legacy_names(self) -> None:
        self.assertTrue(meta.is_kaggle_laps_csv("all_laps.csv"))
        self.assertTrue(meta.is_kaggle_laps_csv("All Laps - 24 October 2026.csv"))
        self.assertTrue(meta.is_kaggle_laps_csv("/tmp/All Laps - 11 October 2026.csv"))
        self.assertFalse(meta.is_kaggle_laps_csv("dataset-metadata.json"))
        self.assertFalse(meta.is_kaggle_laps_csv("notes.txt"))


class DatasetHandleTests(unittest.TestCase):
    def test_default_slug_is_formula_one_topic(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KAGGLE_DATASET", None)
            self.assertEqual(meta.kaggle_dataset(), "stevefza/formula-one-all-laps-telemetry")
            candidates = meta.dataset_handle_candidates()
            self.assertEqual(candidates[0], "stevefza/formula-one-all-laps-telemetry")
            self.assertIn(meta.KAGGLE_DATASET_LEGACY, candidates)

    def test_env_override_still_falls_back_to_legacy(self) -> None:
        with patch.dict(os.environ, {"KAGGLE_DATASET": "stevefza/custom-slug"}):
            self.assertEqual(
                meta.dataset_handle_candidates(),
                ["stevefza/custom-slug", meta.KAGGLE_DATASET_LEGACY],
            )


class MetadataBuilderTests(unittest.TestCase):
    def test_scores_all_five_usability_fields(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KAGGLE_LICENSE", None)
            os.environ.pop("KAGGLE_KEYWORDS", None)
            os.environ.pop("KAGGLE_DATASET_ID", None)
            built = meta.build_dataset_metadata()

        self.assertEqual(built["id"], "stevefza/formula-one-all-laps-telemetry")
        self.assertEqual(built["id_no"], 9485317)
        self.assertEqual(built["licenses"], [{"name": "CC-BY-4.0"}])
        self.assertEqual(
            built["keywords"],
            ["sports", "time series analysis", "tabular", "beginner"],
        )
        self.assertEqual(built["expectedUpdateFrequency"], "weekly")
        self.assertIn("FastF1", built["userSpecifiedSources"])
        self.assertEqual(built["resources"][0]["path"], "all_laps.csv")
        self.assertIn("2 Hz", built["resources"][0]["description"])
        field_names = [field["name"] for field in built["resources"][0]["schema"]["fields"]]
        self.assertEqual(field_names, [field["name"] for field in meta.COLUMN_FIELDS])
        self.assertGreaterEqual(len(built["subtitle"]), 20)
        self.assertLessEqual(len(built["subtitle"]), 80)

    def test_schema_follows_actual_column_order(self) -> None:
        built = meta.build_dataset_metadata(columns=["telemetry", "season"])
        names = [field["name"] for field in built["resources"][0]["schema"]["fields"]]
        self.assertEqual(names, ["telemetry", "season"])

    def test_preserves_existing_card_text(self) -> None:
        existing = {
            "title": "Keep this title",
            "subtitle": "Existing subtitle that is long enough!!",
            "description": "# Live card\nLeave this markdown alone.",
        }
        built = meta.build_dataset_metadata(existing=existing)
        self.assertEqual(built["title"], "Keep this title")
        self.assertEqual(built["subtitle"], existing["subtitle"])
        self.assertEqual(built["description"], existing["description"])

    def test_short_subtitle_is_replaced(self) -> None:
        built = meta.build_dataset_metadata(existing={"subtitle": "too short"})
        self.assertEqual(built["subtitle"], meta.KAGGLE_SUBTITLE_DEFAULT)


class MetadataFileTests(unittest.TestCase):
    def test_version_file_is_object_update_file_is_double_encoded(self) -> None:
        payload = {"id": "stevefza/formula-one-all-laps-telemetry"}
        with tempfile.TemporaryDirectory() as tmp:
            version_path = Path(tmp) / "dataset-metadata.json"
            meta.write_metadata_file(version_path, payload)
            self.assertIsInstance(json.loads(version_path.read_text()), dict)
            self.assertEqual(meta.load_metadata_file(version_path)["id"], payload["id"])

            update_path = Path(tmp) / "update.json"
            meta.write_metadata_file(update_path, payload, for_update=True)
            raw = json.loads(update_path.read_text())
            self.assertIsInstance(raw, str)
            self.assertEqual(meta.load_metadata_file(update_path)["id"], payload["id"])


if __name__ == "__main__":
    unittest.main()
