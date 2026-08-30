import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  executionShortName,
  isExecutionResource,
  isOperationResource,
  isRemoteCloudRunName,
  parseExecutionInfo,
  pickExecutionName,
} from "./cloud-run-names.ts";

const EXEC =
  "projects/f1-data-library/locations/europe-west1/jobs/f1-telemetry-import/executions/f1-telemetry-import-abc";
const OP =
  "projects/f1-data-library/locations/europe-west1/operations/operation-123";

describe("cloud-run-names", () => {
  it("rejects stub and local names", () => {
    assert.equal(isRemoteCloudRunName(null), false);
    assert.equal(isRemoteCloudRunName("stub://job"), false);
    assert.equal(isRemoteCloudRunName("local://1"), false);
    assert.equal(isRemoteCloudRunName(EXEC), true);
  });

  it("distinguishes execution vs operation resources", () => {
    assert.equal(isExecutionResource(EXEC), true);
    assert.equal(isExecutionResource(OP), false);
    assert.equal(isOperationResource(OP), true);
    assert.equal(isOperationResource(EXEC), false);
  });

  it("prefers the Execution name inside an Operation payload", () => {
    assert.equal(
      pickExecutionName({
        name: OP,
        metadata: { name: EXEC, completionStatus: "EXECUTION_RUNNING" },
      }),
      EXEC,
    );
    assert.equal(
      executionShortName(EXEC),
      "f1-telemetry-import-abc",
    );
  });

  it("reads completionStatus from Operation metadata", () => {
    const info = parseExecutionInfo(
      {
        name: OP,
        metadata: {
          name: EXEC,
          completionStatus: "EXECUTION_CANCELLED",
        },
      },
      OP,
    );
    assert.equal(info.name, EXEC);
    assert.equal(info.completionStatus, "EXECUTION_CANCELLED");
  });
});
