interface StatusPillProps {
  label: string;
  value: string;
  ok?: boolean;
}

function StatusPill({ label, value, ok }: StatusPillProps) {
  return (
    <div className="rounded-lg border border-white/5 bg-ink-900/60 px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div
        className={`mt-0.5 font-mono text-sm ${
          ok === undefined ? "text-slate-200" : ok ? "text-teal-glow" : "text-amber-glow"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

interface Props {
  cloudOk: boolean;
  modelLoaded: boolean;
  serialEnabled: boolean;
  serialStatus: string | null;
  requestCount: number;
  uptime: number;
  fps: number;
}

export function StatusGrid({
  cloudOk,
  modelLoaded,
  serialEnabled,
  serialStatus,
  requestCount,
  uptime,
  fps,
}: Props) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      <StatusPill label="Cloud / API" value={cloudOk ? "Online" : "Down"} ok={cloudOk} />
      <StatusPill label="Health" value={modelLoaded ? "Model ready" : "No model"} ok={modelLoaded} />
      <StatusPill
        label="Serial"
        value={
          serialEnabled
            ? serialStatus
              ? serialStatus
              : "Enabled"
            : "Bridge / off"
        }
        ok={serialEnabled ? serialStatus !== "ERROR" : undefined}
      />
      <StatusPill label="Requests" value={String(requestCount)} />
      <StatusPill label="Uptime" value={`${Math.floor(uptime)}s`} />
      <StatusPill label="Approx FPS" value={fps.toFixed(2)} />
    </div>
  );
}
