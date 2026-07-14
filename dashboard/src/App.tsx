import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  b64ToSrc,
  eventsUrl,
  fetchConfig,
  fetchDeviceConfig,
  fetchHealth,
  fetchLatest,
} from "./api";
import type { ConfigPayload, HealthPayload, LatestPayload, LiveEvent } from "./types";
import { ConveyorAnimation } from "./components/ConveyorAnimation";
import { DeviceSetupModal } from "./components/DeviceSetupModal";
import { ImagePanel } from "./components/ImagePanel";
import { PredictionCard } from "./components/PredictionCard";
import { ProcessingTimeline } from "./components/ProcessingTimeline";
import { StatusGrid } from "./components/StatusGrid";

type Stage = "idle" | "scan" | "process" | "decide" | "move";

export default function App() {
  const [latest, setLatest] = useState<LatestPayload>({ available: false, phase: "idle" });
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [config, setConfig] = useState<ConfigPayload | null>(null);
  const [cloudOk, setCloudOk] = useState(false);
  const [liveOk, setLiveOk] = useState(false);
  const [stage, setStage] = useState<Stage>("idle");
  const [setupOpen, setSetupOpen] = useState(false);
  const [deviceConfigured, setDeviceConfigured] = useState(false);
  const [displayedOriginal, setDisplayedOriginal] = useState<string | null>(null);
  const [displayedAnnotated, setDisplayedAnnotated] = useState<string | null>(null);

  const applyResult = useCallback((event: LiveEvent) => {
    setLatest({
      available: true,
      request_id: event.request_id,
      timestamp: event.timestamp,
      phase: "result",
      ewaste: event.ewaste,
      category: event.category,
      confidence: event.confidence,
      inference_ms: event.inference_ms,
      serial_command: event.serial_command,
      serial_status: event.serial_status,
      detections: event.detections,
      original_image_b64: event.original_image_b64,
      annotated_image_b64: event.annotated_image_b64,
      frame_index: event.frame_index,
      final_decision: event.final_decision,
    });
    if (event.final_decision) {
      setStage("decide");
      window.setTimeout(() => setStage("move"), 700);
    } else {
      setStage("scan");
    }
  }, []);

  // Live SSE from backend (frame → processing → result)
  useEffect(() => {
    const es = new EventSource(eventsUrl());
    es.onopen = () => setLiveOk(true);
    es.onerror = () => setLiveOk(false);
    es.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as LiveEvent;
        if (event.type === "frame") {
          setLatest({
            available: true,
            request_id: event.request_id,
            timestamp: event.timestamp,
            phase: "scan",
            original_image_b64: event.original_image_b64,
            annotated_image_b64: null,
            category: "…",
            confidence: 0,
            ewaste: undefined,
          });
          setStage("scan");
        } else if (event.type === "processing") {
          setStage("process");
          setLatest((prev) => ({ ...prev, phase: "process", request_id: event.request_id ?? prev.request_id }));
        } else if (event.type === "result") {
          applyResult(event);
        }
      } catch {
        // ignore malformed ping frames
      }
    };
    return () => es.close();
  }, [applyResult]);

  // Health + fallback /latest poll (keeps status grid fresh; recovers if SSE missed)
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const [l, h] = await Promise.all([fetchLatest(), fetchHealth()]);
        if (cancelled) return;
        setHealth(h);
        setCloudOk(true);
        // Hydrate from poll when SSE is down, we have nothing yet, or a newer request has completed
        if (!liveOk || !latest.request_id || (l.available && l.request_id !== latest.request_id)) {
          if (l.available && l.phase === "result") {
            setLatest(l);
            setStage("move");
          } else if (l.available && l.phase === "scan") {
            setLatest(l);
            setStage("scan");
          }
        }
      } catch {
        if (!cancelled) setCloudOk(false);
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [liveOk, latest.request_id]);

  useEffect(() => {
    void fetchConfig().then(setConfig).catch(() => undefined);
    void fetchDeviceConfig()
      .then((d) => {
        setDeviceConfigured(d.configured);
        if (!d.configured) setSetupOpen(true);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSetupOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (latest.original_image_b64) {
      setDisplayedOriginal(b64ToSrc(latest.original_image_b64));
    }
    if (latest.annotated_image_b64) {
      setDisplayedAnnotated(b64ToSrc(latest.annotated_image_b64));
    }
  }, [latest.original_image_b64, latest.annotated_image_b64]);

  const ewaste =
    latest.phase === "result" || stage === "decide" || stage === "move"
      ? Boolean(latest.ewaste)
      : null;
  const threshold = config?.confidence_threshold ?? 0.5;
  const showDecision =
    stage === "decide" || stage === "move" || latest.phase === "result";

  return (
    <div className="min-h-screen bg-grid bg-grid">
      <header className="border-b border-white/5 bg-ink-900/40 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <motion.p
              className="font-mono text-[11px] uppercase tracking-[0.25em] text-teal-glow"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
            >
              Production control
            </motion.p>
            <motion.h1
              className="font-display text-3xl font-bold tracking-tight text-white sm:text-4xl"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
            >
              E-Waste Segregation
            </motion.h1>
            <p className="mt-1 max-w-xl text-sm text-slate-400">
              ESP32 uploads → backend pushes live frames → scan → YOLO → conveyor diversion.
            </p>
          </div>
          <div className="flex flex-col items-stretch gap-2 sm:items-end">
            <button
              type="button"
              onClick={() => setSetupOpen(true)}
              className="rounded-lg border border-teal-glow/40 bg-teal-deep/30 px-4 py-2 text-sm font-semibold text-teal-glow hover:bg-teal-deep/50"
            >
              {deviceConfigured ? "Device / WiFi setup" : "Set up WiFi & API"}
            </button>
            <div className="font-mono text-[11px] text-slate-500">
              Live{" "}
              <span className={liveOk ? "text-teal-glow" : "text-amber-glow"}>
                {liveOk ? "SSE /events" : "reconnecting…"}
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
        <StatusGrid
          cloudOk={cloudOk}
          modelLoaded={Boolean(health?.model_loaded)}
          serialEnabled={Boolean(config?.serial_enabled)}
          serialStatus={latest.serial_status ?? null}
          requestCount={health?.request_count ?? latest.request_count ?? 0}
          uptime={health?.uptime_seconds ?? 0}
          fps={health?.approx_fps ?? 0}
        />

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <div className="grid gap-4 md:grid-cols-2">
              <ImagePanel
                src={displayedOriginal}
                title="Live camera frame"
                scanning={stage === "scan"}
                emptyHint="Waiting for ESP32-CAM upload…"
              />
              <ImagePanel
                src={displayedAnnotated}
                title="YOLO detection"
                scanning={stage === "process"}
                emptyHint="Annotated frame after inference"
              />
            </div>
            <ConveyorAnimation
              requestId={
                stage === "move" || stage === "decide" ? latest.request_id : undefined
              }
              ewaste={showDecision ? ewaste : null}
              scanning={stage === "scan" || stage === "process"}
            />
          </div>

          <div className="space-y-4">
            <PredictionCard
              ewaste={latest.ewaste !== undefined ? Boolean(latest.ewaste) : null}
              category={latest.category ?? "unknown"}
              confidence={latest.confidence ?? 0}
              threshold={threshold}
              inferenceMs={latest.inference_ms ?? null}
              frameIndex={latest.frame_index}
              finalDecision={latest.final_decision}
            />
            <div className="rounded-xl border border-white/5 bg-ink-900/80 p-5">
              <ProcessingTimeline
                stage={stage}
                ewaste={showDecision ? ewaste : null}
                frameIndex={latest.frame_index}
              />
            </div>
          </div>
        </div>
      </main>

      <DeviceSetupModal
        open={setupOpen}
        onClose={() => {
          setSetupOpen(false);
          void fetchDeviceConfig()
            .then((d) => setDeviceConfigured(d.configured))
            .catch(() => undefined);
        }}
      />
    </div>
  );
}
