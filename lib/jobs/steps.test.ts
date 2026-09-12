import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { stepsForParams, type JobParams } from "./steps.ts";

const base: JobParams = {
  years: [2026],
  race: "Italian Grand Prix",
  sessions: ["R"],
  noSkip: false,
  skipQuality: false,
  skipUnified: false,
  includeKaggle: false,
};

describe("stepsForParams", () => {
  it("warehouse jobs skip the Kaggle export table and upload", () => {
    const keys = stepsForParams(base).map((s) => s.key);
    assert.equal(keys.includes("upload_kaggle_export"), false);
    assert.equal(keys.includes("kaggle_upload"), false);
    assert.equal(keys.includes("upload_sessions_laps"), true);
    assert.equal(keys.includes("upload_telemetry"), true);
    assert.equal(keys.includes("laps_unified"), true);
  });

  it("Kaggle jobs write for_kaggle_export and skip warehouse tables", () => {
    const keys = stepsForParams({ ...base, includeKaggle: true }).map(
      (s) => s.key,
    );
    assert.deepEqual(keys, [
      "queued",
      "load_fastf1",
      "resample_telemetry",
      "upload_kaggle_export",
      "quality_checks",
      "kaggle_upload",
      "done",
    ]);
    assert.equal(keys.includes("upload_sessions_laps"), false);
    assert.equal(keys.includes("upload_telemetry"), false);
    assert.equal(keys.includes("verify"), false);
    assert.equal(keys.includes("laps_unified"), false);
  });
});
