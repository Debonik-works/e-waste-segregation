import { AnimatePresence, motion } from "framer-motion";

type Stage = "idle" | "scan" | "process" | "decide" | "move";

interface Props {
  stage: Stage;
  ewaste: boolean | null;
}

const STAGES: { id: Stage; label: string }[] = [
  { id: "scan", label: "Image scan" },
  { id: "process", label: "AI inference" },
  { id: "decide", label: "Decision" },
  { id: "move", label: "Conveyor" },
];

export function ProcessingTimeline({ stage, ewaste }: Props) {
  const order = ["idle", "scan", "process", "decide", "move"];
  const currentIdx = order.indexOf(stage);

  return (
    <div className="space-y-3">
      <h3 className="font-display text-sm font-semibold tracking-wide text-slate-200">
        Processing timeline
      </h3>
      <ol className="space-y-2">
        {STAGES.map((s, i) => {
          const idx = order.indexOf(s.id);
          const active = stage === s.id;
          const done = currentIdx > idx;
          return (
            <li
              key={s.id}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${
                active ? "bg-teal-deep/30 text-teal-glow" : done ? "text-slate-300" : "text-slate-500"
              }`}
            >
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full font-mono text-xs ${
                  active
                    ? "bg-teal-glow text-ink-950"
                    : done
                      ? "bg-ink-700 text-teal-glow"
                      : "bg-ink-800 text-slate-500"
                }`}
              >
                {done ? "✓" : i + 1}
              </span>
              <span className="font-body">{s.label}</span>
              <AnimatePresence>
                {active && (
                  <motion.span
                    className="ml-auto h-1.5 w-1.5 rounded-full bg-teal-glow"
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  />
                )}
              </AnimatePresence>
            </li>
          );
        })}
      </ol>
      {stage === "move" && ewaste !== null && (
        <p className="font-mono text-xs text-slate-400">
          Diverting {ewaste ? "RIGHT → E-Waste" : "LEFT → Reject"}
        </p>
      )}
    </div>
  );
}
