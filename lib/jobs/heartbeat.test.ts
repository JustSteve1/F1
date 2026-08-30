import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  HEARTBEAT_LAGGING_MS,
  HEARTBEAT_LIVE_MS,
  HEARTBEAT_STALE_MS,
  describeHeartbeat,
  formatAge,
} from "./heartbeat.ts";

describe("formatAge", () => {
  it("formats seconds, minutes, hours", () => {
    assert.equal(formatAge(0), "0s");
    assert.equal(formatAge(12_000), "12s");
    assert.equal(formatAge(60_000), "1m");
    assert.equal(formatAge(90_000), "1m 30s");
    assert.equal(formatAge(3_600_000), "1h");
    assert.equal(formatAge(3_900_000), "1h 5m");
  });
});

describe("describeHeartbeat", () => {
  const now = Date.parse("2026-08-30T12:00:00.000Z");

  it("is idle when the job is terminal", () => {
    const r = describeHeartbeat({
      status: "failed",
      updatedAt: new Date(now - 5_000).toISOString(),
      now,
    });
    assert.equal(r.health, "idle");
    assert.equal(r.label, "Stopped");
  });

  it("is live within the heartbeat slack window", () => {
    const r = describeHeartbeat({
      status: "running",
      updatedAt: new Date(now - HEARTBEAT_LIVE_MS).toISOString(),
      now,
    });
    assert.equal(r.health, "live");
    assert.match(r.label, /^Live/);
  });

  it("lags after 45s and is silent after 3m", () => {
    const lag = describeHeartbeat({
      status: "running",
      updatedAt: new Date(now - HEARTBEAT_LIVE_MS - 1).toISOString(),
      now,
    });
    assert.equal(lag.health, "lagging");

    const silent = describeHeartbeat({
      status: "cancelling",
      updatedAt: new Date(now - HEARTBEAT_LAGGING_MS - 1).toISOString(),
      now,
    });
    assert.equal(silent.health, "silent");
    assert.equal(silent.stale, false);
  });

  it("marks stale at the 15 min watchdog threshold", () => {
    const r = describeHeartbeat({
      status: "queued",
      updatedAt: new Date(now - HEARTBEAT_STALE_MS).toISOString(),
      now,
    });
    assert.equal(r.health, "silent");
    assert.equal(r.stale, true);
  });
});
