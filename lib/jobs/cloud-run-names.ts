export type ExecutionNamePayload = {
  name?: string;
  metadata?: { name?: string; completionStatus?: string; reconciling?: boolean };
  response?: { name?: string; completionStatus?: string; reconciling?: boolean };
  completionStatus?: string;
  reconciling?: boolean;
};

export type ParsedExecutionInfo = {
  name: string;
  completionStatus: string | null;
  reconciling: boolean;
};

export function isRemoteCloudRunName(
  name: string | null | undefined,
): name is string {
  return Boolean(
    name && !name.startsWith("stub://") && !name.startsWith("local://"),
  );
}

export function isExecutionResource(name: string): boolean {
  return /\/jobs\/[^/]+\/executions\/[^/]+$/.test(name);
}

export function isOperationResource(name: string): boolean {
  return /\/operations\/[^/]+$/.test(name);
}

export function executionShortName(
  name: string | null | undefined,
): string | null {
  if (!name) return null;
  if (name.startsWith("stub://") || name.startsWith("local://")) return name;
  const parts = name.split("/");
  const idx = parts.lastIndexOf("executions");
  if (idx >= 0 && parts[idx + 1]) return parts[idx + 1];
  return parts.at(-1) || name;
}

/**
 * Cloud Run Jobs `:run` returns an Operation. Prefer the Execution resource
 * in metadata/response over the Operation name so cancel/get hit the right URL.
 */
export function pickExecutionName(
  payload: ExecutionNamePayload,
): string | null {
  const candidates = [
    payload.metadata?.name,
    payload.response?.name,
    payload.name,
  ];
  for (const c of candidates) {
    if (c && isExecutionResource(c)) return c;
  }
  for (const c of candidates) {
    if (c) return c;
  }
  return null;
}

export function parseExecutionInfo(
  data: ExecutionNamePayload,
  fallbackName: string,
): ParsedExecutionInfo {
  const name = pickExecutionName(data) || fallbackName;
  const completionStatus =
    data.completionStatus ??
    data.metadata?.completionStatus ??
    data.response?.completionStatus ??
    null;
  const reconciling = Boolean(
    data.reconciling ??
      data.metadata?.reconciling ??
      data.response?.reconciling,
  );
  return { name, completionStatus, reconciling };
}
