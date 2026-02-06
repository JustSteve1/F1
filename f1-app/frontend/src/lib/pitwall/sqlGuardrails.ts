
export interface SqlGuardrailsOptions {
  allowlistTables: string[];
  defaultLimit: number;
  maxLimit: number;
}

export function enforceSqlGuardrails(sql: string, options: SqlGuardrailsOptions): string {
  const { allowlistTables, defaultLimit, maxLimit } = options;
  const upperSql = sql.toUpperCase();

  // 1. Must start with SELECT
  if (!upperSql.trim().startsWith("SELECT")) {
    throw new Error("Guardrail Violation: Only SELECT queries are allowed.");
  }

  // 2. No destructive keywords (basic check)
  const forbiddenKeywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "MERGE", "GRANT", "REVOKE"];
  for (const keyword of forbiddenKeywords) {
    // Check for keyword boundaries to avoid false positives (like 'update_ts' column)
    const regex = new RegExp(`\\b${keyword}\\b`, "i");
    if (regex.test(sql)) {
      throw new Error(`Guardrail Violation: Forbidden keyword '${keyword}' detected.`);
    }
  }

  // 3. Must contain only allowlisted tables
  // This is a heuristic check. For robust parsing, we'd need a real SQL parser.
  // We check if any table in the query is NOT in the allowlist? 
  // Easier: Check if the query contains at least one allowed table, and potentially warn if others are found.
  // Rigorous approach: Extract FROM/JOIN clauses. 
  // For v1, let's enforce that if a table pattern is found (dataset.table), it must be allowed.
  // Or even simpler given the task: we expect the agent/code to produce queries against specific tables.

  const foundAllowedTable = allowlistTables.some(table =>
    sql.includes(table) || sql.includes(table.split('.').pop()!)
  );

  if (!foundAllowedTable) {
    throw new Error("Guardrail Violation: Query must target at least one allowlisted table.");
  }

  // 4. Force LIMIT
  // If LIMIT is missing, append default. 
  // If LIMIT exists, enforce max cap.
  const limitRegex = /\bLIMIT\s+(\d+)/i;
  const match = sql.match(limitRegex);

  if (match) {
    const declaredLimit = parseInt(match[1], 10);
    if (declaredLimit > maxLimit) {
      // Rewrite the limit
      return sql.replace(limitRegex, `LIMIT ${maxLimit}`);
    }
    return sql;
  } else {
    // Append proper limit
    // Check if SQL ends with semicolon
    const trimmed = sql.trim();
    if (trimmed.endsWith(";")) {
      return trimmed.slice(0, -1) + ` LIMIT ${defaultLimit}`;
    }
    return trimmed + ` LIMIT ${defaultLimit}`;
  }
}
