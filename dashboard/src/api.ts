import type {
  ConfigPayload,
  DeviceConfigPayload,
  HealthPayload,
  LatestPayload,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path));
  if (!res.ok) {
    throw new Error(`${path} → HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchLatest(): Promise<LatestPayload> {
  return getJson<LatestPayload>("/latest");
}

export function fetchHealth(): Promise<HealthPayload> {
  return getJson<HealthPayload>("/health");
}

export function fetchConfig(): Promise<ConfigPayload> {
  return getJson<ConfigPayload>("/config");
}

export function fetchDeviceConfig(): Promise<DeviceConfigPayload> {
  return getJson<DeviceConfigPayload>("/device-config");
}

export interface LanInfoPayload {
  port: number;
  addresses: { ip: string; api_base_url: string; predict_url: string; primary?: string }[];
  recommended_api_base_url: string;
  note: string;
}

export function fetchLanInfo(): Promise<LanInfoPayload> {
  return getJson<LanInfoPayload>("/lan-info");
}

export async function saveDeviceConfig(body: {
  wifi_ssid: string;
  wifi_password: string;
  api_base_url: string;
  capture_interval_ms: number;
}): Promise<DeviceConfigPayload> {
  const res = await fetch(apiUrl("/device-config"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<DeviceConfigPayload>;
}

/** Push credentials to ESP32 SoftAP (PC must be on EWaste-Setup WiFi). */
export async function pushToEsp32SoftAp(body: {
  wifi_ssid: string;
  wifi_password: string;
  api_base_url: string;
  capture_interval_ms: number;
}): Promise<{ ok: boolean; message?: string }> {
  const res = await fetch("http://192.168.4.1/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ssid: body.wifi_ssid,
      password: body.wifi_password,
      api_base_url: body.api_base_url,
      interval_ms: body.capture_interval_ms,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `ESP32 SoftAP HTTP ${res.status}`);
  }
  return res.json() as Promise<{ ok: boolean; message?: string }>;
}

export function b64ToSrc(b64: string | null | undefined): string | null {
  if (!b64) return null;
  return `data:image/jpeg;base64,${b64}`;
}

export function eventsUrl(): string {
  return apiUrl("/events");
}
