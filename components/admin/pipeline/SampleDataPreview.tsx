import type { SampleTable } from "@/lib/jobs/pipeline-guide";

export function SampleDataPreview({
  sample,
  caption,
}: {
  sample: SampleTable | null;
  caption?: string;
}) {
  if (!sample || sample.rows.length === 0) {
    return (
      <p className="text-xs text-white/35 italic">No sample payload for this step.</p>
    );
  }

  return (
    <div className="space-y-2">
      {caption && (
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">
          {caption}
        </p>
      )}
      <div className="overflow-x-auto border border-white/10">
        <table className="w-full min-w-max text-left text-[11px] font-mono">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.03]">
              {sample.columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 font-bold uppercase tracking-wider text-white/45"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sample.rows.map((row, i) => (
              <tr
                key={i}
                className="border-b border-white/5 last:border-0 text-white/75"
              >
                {row.map((cell, j) => (
                  <td key={j} className="px-3 py-1.5 whitespace-nowrap">
                    {cell === null ? (
                      <span className="text-white/30">null</span>
                    ) : typeof cell === "boolean" ? (
                      cell ? "true" : "false"
                    ) : (
                      String(cell)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
