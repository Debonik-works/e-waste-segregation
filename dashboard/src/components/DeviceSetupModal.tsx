import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { fetchDeviceConfig, fetchLanInfo, pushToEsp32SoftAp, saveDeviceConfig } from "../api";
import type { DeviceConfigPayload } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function DeviceSetupModal({ open, onClose }: Props) {
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [apiBase, setApiBase] = useState("http://127.0.0.1:8080");
  const [intervalMs, setIntervalMs] = useState(5000);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<DeviceConfigPayload | null>(null);
  const [lanHint, setLanHint] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    void fetchDeviceConfig()
      .then((cfg) => {
        if (cfg.wifi_ssid) setSsid(cfg.wifi_ssid);
        if (cfg.api_base_url) setApiBase(cfg.api_base_url);
        if (cfg.capture_interval_ms) setIntervalMs(cfg.capture_interval_ms);
        setSaved(cfg);
      })
      .catch(() => undefined);
    void detectLan();
  }, [open]);

  async function detectLan() {
    try {
      const info = await fetchLanInfo();
      setLanHint(info.recommended_api_base_url);
      // Auto-fill only if still localhost placeholder
      setApiBase((prev) =>
        prev.includes("127.0.0.1") || prev.includes("localhost")
          ? info.recommended_api_base_url
          : prev
      );
    } catch {
      setLanHint(null);
    }
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      if (apiBase.includes("127.0.0.1") || apiBase.includes("localhost")) {
        throw new Error(
          "ESP32 cannot reach 127.0.0.1. Connect PC to the phone hotspot, click “Detect LAN IP”, then use that URL."
        );
      }
      const res = await saveDeviceConfig({
        wifi_ssid: ssid,
        wifi_password: password,
        api_base_url: apiBase,
        capture_interval_ms: intervalMs,
      });
      setSaved(res);
      setStatus("Saved on backend. Next: join WiFi EWaste-Setup on this PC, then Push to ESP32.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onPushEsp32() {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      if (apiBase.includes("127.0.0.1") || apiBase.includes("localhost")) {
        throw new Error(
          "ESP32 cannot reach 127.0.0.1. Use Detect LAN IP while PC is on the phone hotspot."
        );
      }
      await saveDeviceConfig({
        wifi_ssid: ssid,
        wifi_password: password,
        api_base_url: apiBase,
        capture_interval_ms: intervalMs,
      });
      const res = await pushToEsp32SoftAp({
        wifi_ssid: ssid,
        wifi_password: password,
        api_base_url: apiBase,
        capture_interval_ms: intervalMs,
      });
      setStatus(
        res.message ||
          "ESP32 saved config and is rebooting. Rejoin the phone hotspot on this PC; camera will POST to /predict."
      );
    } catch (err) {
      setError(
        (err instanceof Error ? err.message : String(err)) +
          " — Is this PC connected to WiFi “EWaste-Setup” (password ewaste123)?"
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-white/10 bg-ink-900 p-6 shadow-2xl"
            initial={{ y: 24, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 16, opacity: 0 }}
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="font-display text-xl font-semibold text-white">Device setup</h2>
                <p className="mt-1 text-sm text-slate-400">
                  Phone hotspot + local FastAPI — enter WiFi here; ESP32 stores it and uploads to /predict.
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-md px-2 py-1 font-mono text-xs text-slate-400 hover:bg-ink-700 hover:text-white"
              >
                ESC
              </button>
            </div>

            <div className="mb-4 rounded-lg border border-amber-glow/20 bg-amber-glow/5 px-3 py-2 text-xs text-slate-300">
              <p className="font-semibold text-amber-glow">Phone hotspot checklist</p>
              <ol className="mt-1 list-decimal space-y-1 pl-4 text-slate-400">
                <li>Turn on hotspot on your phone. Note its <span className="text-slate-200">name (SSID)</span> and password.</li>
                <li>Connect <span className="text-slate-200">this PC</span> to that hotspot.</li>
                <li>Start backend: <span className="font-mono text-teal-glow">uvicorn … --host 0.0.0.0 --port 8080</span></li>
                <li>Click <span className="text-slate-200">Detect LAN IP</span> below — that URL is what ESP32 must use (not 127.0.0.1).</li>
                <li>Power ESP32 → SoftAP <span className="text-teal-glow">EWaste-Setup</span> / <span className="font-mono">ewaste123</span>.</li>
                <li>Join PC to EWaste-Setup → <span className="text-slate-200">Push to ESP32</span> → PC rejoins phone hotspot.</li>
              </ol>
            </div>

            <form className="space-y-3" onSubmit={onSave}>
              <label className="block text-xs text-slate-400">
                WiFi SSID (your phone hotspot name)
                <input
                  required
                  value={ssid}
                  onChange={(e) => setSsid(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-2 font-mono text-sm text-white outline-none focus:border-teal-glow/50"
                  placeholder="AndroidAP / iPhone"
                />
              </label>
              <label className="block text-xs text-slate-400">
                WiFi password (hotspot password)
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-2 font-mono text-sm text-white outline-none focus:border-teal-glow/50"
                  placeholder={saved?.has_wifi_password ? "(unchanged if empty — enter to set)" : "••••••••"}
                />
              </label>
              <label className="block text-xs text-slate-400">
                Backend base URL (this PC on the hotspot — ESP32 posts here /predict)
                <div className="mt-1 flex gap-2">
                  <input
                    required
                    value={apiBase}
                    onChange={(e) => setApiBase(e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-2 font-mono text-sm text-white outline-none focus:border-teal-glow/50"
                    placeholder="http://192.168.43.10:8080"
                  />
                  <button
                    type="button"
                    onClick={() => void detectLan()}
                    className="shrink-0 rounded-lg border border-teal-glow/40 px-3 py-2 text-xs font-semibold text-teal-glow hover:bg-teal-deep/30"
                  >
                    Detect LAN IP
                  </button>
                </div>
                {lanHint && (
                  <button
                    type="button"
                    className="mt-1 font-mono text-[11px] text-teal-glow underline"
                    onClick={() => setApiBase(lanHint)}
                  >
                    Use {lanHint}
                  </button>
                )}
              </label>
              <label className="block text-xs text-slate-400">
                Capture interval (ms)
                <input
                  type="number"
                  min={1000}
                  max={60000}
                  value={intervalMs}
                  onChange={(e) => setIntervalMs(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-2 font-mono text-sm text-white outline-none focus:border-teal-glow/50"
                />
              </label>

              {error && (
                <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</p>
              )}
              {status && (
                <p className="rounded-lg bg-teal-deep/20 px-3 py-2 text-xs text-teal-glow">{status}</p>
              )}

              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-lg bg-ink-700 px-4 py-2 text-sm font-medium text-white hover:bg-ink-700/80 disabled:opacity-50"
                >
                  Save on backend
                </button>
                <button
                  type="button"
                  disabled={busy || !ssid || !apiBase}
                  onClick={() => void onPushEsp32()}
                  className="rounded-lg bg-teal-deep px-4 py-2 text-sm font-semibold text-white hover:bg-teal-deep/80 disabled:opacity-50"
                >
                  Push to ESP32
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="ml-auto rounded-lg px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Close
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
