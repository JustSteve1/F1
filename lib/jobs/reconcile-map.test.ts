import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { mapCloudRunCompletion } from "./reconcile-map.ts";

describe("mapCloudRunCompletion", () => {
  it("maps FAILED to failed", () => {
    assert.equal(mapCloudRunCompletion("running", "EXECUTION_FAILED"), "failed");
  });

  it("maps CANCELLED to cancelled even if the job was still running", () => {
    assert.equal(
      mapCloudRunCompletion("cancelling", "EXECUTION_CANCELLED"),
      "cancelled",
    );
    assert.equal(
      mapCloudRunCompletion("running", "EXECUTION_CANCELLED"),
      "cancelled",
    );
  });

  it("maps a finished execution with a live job to failed", () => {
    assert.equal(
      mapCloudRunCompletion("running", "EXECUTION_SUCCEEDED"),
      "failed",
    );
    assert.equal(
      mapCloudRunCompletion("succeeded", "EXECUTION_SUCCEEDED"),
      "check-stale",
    );
  });

  it("falls back to the heartbeat watchdog while still running", () => {
    assert.equal(mapCloudRunCompletion("running", null), "check-stale");
    assert.equal(
      mapCloudRunCompletion("running", "EXECUTION_RUNNING"),
      "check-stale",
    );
  });
});
