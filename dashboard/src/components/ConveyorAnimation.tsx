import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

interface Props {
  requestId: string | undefined;
  ewaste: boolean | null;
  scanning: boolean;
}

export function ConveyorAnimation({ requestId, ewaste, scanning }: Props) {
  const [phase, setPhase] = useState<"in" | "scan" | "out">("in");

  useEffect(() => {
    if (!requestId) return;
    setPhase("in");
    const t1 = window.setTimeout(() => setPhase("scan"), 400);
    const t2 = window.setTimeout(() => setPhase("out"), 1400);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [requestId]);

  const targetX = ewaste === null ? 0 : ewaste ? 140 : -140;

  return (
    <div className="relative overflow-hidden rounded-xl border border-white/5 bg-ink-900/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold text-slate-200">Conveyor diversion</h3>
        <span className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
          live animation
        </span>
      </div>

      <div className="relative h-40">
        {/* Bins */}
        <div className="absolute bottom-2 left-2 flex h-20 w-16 flex-col items-center justify-end rounded-md border border-slate-500/40 bg-bin-reject/20">
          <span className="mb-2 font-mono text-[10px] text-slate-400">REJECT</span>
          <div className="h-2 w-full bg-bin-reject/60" />
        </div>
        <div className="absolute bottom-2 right-2 flex h-20 w-16 flex-col items-center justify-end rounded-md border border-bin-green/50 bg-bin-green/15 shadow-[0_0_24px_rgba(34,197,94,0.25)]">
          <span className="mb-2 font-mono text-[10px] text-bin-green">E-WASTE</span>
          <div className="h-2 w-full bg-bin-green/70" />
        </div>

        {/* Belt */}
        <div className="absolute bottom-10 left-20 right-20 h-3 overflow-hidden rounded-full bg-ink-700">
          <motion.div
            className="h-full w-[200%] bg-[repeating-linear-gradient(90deg,#1a2533_0_12px,#243044_12px_24px)]"
            animate={{ x: [0, -24] }}
            transition={{ repeat: Infinity, duration: 0.6, ease: "linear" }}
          />
        </div>

        {/* Laser scan */}
        <AnimatePresence>
          {(scanning || phase === "scan") && (
            <motion.div
              className="absolute left-1/2 top-4 h-24 w-0.5 -translate-x-1/2 bg-teal-glow shadow-[0_0_12px_#2dd4bf]"
              initial={{ opacity: 0, scaleY: 0 }}
              animate={{ opacity: [0.2, 1, 0.2], scaleY: 1, x: [-40, 40, -40] }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.2, repeat: Infinity }}
            />
          )}
        </AnimatePresence>

        {/* Package */}
        <AnimatePresence mode="wait">
          {requestId && (
            <motion.div
              key={requestId}
              className="absolute bottom-14 left-1/2 h-10 w-14 -translate-x-1/2 rounded-md border border-amber-glow/40 bg-gradient-to-br from-amber-glow/80 to-amber-700 shadow-lg"
              initial={{ x: 0, y: -30, opacity: 0, scale: 0.8 }}
              animate={{
                x: phase === "out" ? targetX : 0,
                y: phase === "out" ? 28 : 0,
                opacity: 1,
                scale: 1,
                rotate: phase === "out" ? (ewaste ? 12 : -12) : 0,
              }}
              exit={{ opacity: 0 }}
              transition={{ type: "spring", stiffness: 90, damping: 16 }}
            >
              <div className="absolute inset-1 rounded border border-white/20" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
