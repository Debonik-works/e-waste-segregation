import { motion } from "framer-motion";

interface Props {
  src: string | null;
  title: string;
  scanning?: boolean;
  emptyHint: string;
}

export function ImagePanel({ src, title, scanning = false, emptyHint }: Props) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-white/5 bg-ink-900/70">
      <div className="flex items-center justify-between border-b border-white/5 px-4 py-2">
        <h3 className="font-display text-sm font-semibold text-slate-200">{title}</h3>
      </div>
      <div className="relative aspect-video bg-ink-950">
        {src ? (
          <>
            <img src={src} alt={title} className="h-full w-full object-contain" />
            {scanning && (
              <motion.div
                className="pointer-events-none absolute inset-x-0 h-0.5 bg-teal-glow/90 shadow-[0_0_20px_#2dd4bf]"
                animate={{ top: ["0%", "100%", "0%"] }}
                transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
              />
            )}
          </>
        ) : (
          <div className="flex h-full items-center justify-center font-mono text-xs text-slate-500">
            {emptyHint}
          </div>
        )}
      </div>
    </div>
  );
}
