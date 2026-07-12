import { motion } from "framer-motion";

interface Props {
  value: number;
  threshold: number;
}

export function ConfidenceMeter({ value, threshold }: Props) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const ok = value >= threshold;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs font-mono text-slate-400">
        <span>Confidence</span>
        <span className={ok ? "text-teal-glow" : "text-amber-glow"}>
          {(value * 100).toFixed(1)}%
        </span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-ink-700">
        <motion.div
          className={`h-full rounded-full ${ok ? "bg-teal-glow" : "bg-amber-glow"}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 80, damping: 18 }}
        />
      </div>
      <div className="text-[10px] font-mono text-slate-500">
        threshold {(threshold * 100).toFixed(0)}%
      </div>
    </div>
  );
}
