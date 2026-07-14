import { motion } from "framer-motion";
import { ConfidenceMeter } from "./ConfidenceMeter";

interface Props {
  ewaste: boolean | null;
  category: string;
  confidence: number;
  threshold: number;
  inferenceMs: number | null;
  frameIndex?: number;
  finalDecision?: boolean;
}

export function PredictionCard({
  ewaste,
  category,
  confidence,
  threshold,
  inferenceMs,
  frameIndex,
  finalDecision,
}: Props) {
  const decided = Boolean(finalDecision && ewaste !== null);
  const isAnalyzing = Boolean(!finalDecision && frameIndex && frameIndex > 0);

  return (
    <motion.div
      layout
      className="rounded-xl border border-white/5 bg-ink-900/80 p-5"
      animate={
        decided
          ? {
              boxShadow: ewaste
                ? "0 0 0 1px rgba(34,197,94,0.4), 0 0 40px rgba(34,197,94,0.15)"
                : "0 0 0 1px rgba(100,116,139,0.4)",
            }
          : {}
      }
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
            Prediction
          </p>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-white">
            {decided ? (ewaste ? "E-Waste" : "Not E-Waste") : isAnalyzing ? `Analyzing (${frameIndex}/5)` : "Awaiting capture"}
          </h2>
        </div>
        <span
          className={`rounded-md px-2.5 py-1 font-mono text-xs uppercase ${
            decided && ewaste
              ? "bg-bin-green/20 text-bin-green"
              : decided
                ? "bg-slate-500/20 text-slate-300"
                : isAnalyzing
                  ? "bg-teal-glow/20 text-teal-glow"
                  : "bg-ink-700 text-slate-400"
          }`}
        >
          {decided ? category : isAnalyzing ? "SCANNED" : "—"}
        </span>
      </div>

      <ConfidenceMeter value={confidence} threshold={threshold} />

      <div className="mt-4 grid grid-cols-2 gap-3 font-mono text-xs text-slate-400">
        <div className="rounded-lg bg-ink-800/80 px-3 py-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">Inference</div>
          <div className="text-slate-200">
            {inferenceMs != null ? `${inferenceMs.toFixed(1)} ms` : "—"}
          </div>
        </div>
        <div className="rounded-lg bg-ink-800/80 px-3 py-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">Action</div>
          <div className="text-slate-200">
            {decided ? (ewaste ? "RIGHT → bin" : "LEFT → reject") : isAnalyzing ? "WAITING..." : "—"}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
