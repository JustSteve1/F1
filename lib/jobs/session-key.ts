import { createHash } from "node:crypto";

/** Mirror of `generate_session_key` in worker/pipeline/f1_telemetry_import.py */
export function generateSessionKey(
  year: number,
  race: string,
  sessionType: string,
): number {
  const keyStr = `${year}-${race}-${sessionType}`;
  const hex = createHash("md5").update(keyStr).digest("hex").slice(0, 8);
  return parseInt(hex, 16);
}
