/** Shared API types for the dashboard. */

export interface Detection {
  class_id: number;
  category: string;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface LatestPayload {
  available: boolean;
  message?: string;
  request_id?: string;
  timestamp?: number;
  phase?: "idle" | "scan" | "process" | "result";
  ewaste?: boolean;
  category?: string;
  confidence?: number;
  inference_ms?: number;
  serial_command?: string | null;
  serial_status?: string | null;
  detections?: Detection[];
  original_image_b64?: string | null;
  annotated_image_b64?: string | null;
  request_count?: number;
  frame_index?: number;
  final_decision?: boolean;
}

export interface HealthPayload {
  status: string;
  model_loaded: boolean;
  model_path: string;
  uptime_seconds: number;
  request_count: number;
  approx_fps: number;
  last_error: string | null;
  has_latest: boolean;
  phase?: string;
}

export interface ConfigPayload {
  confidence_threshold: number;
  inference_imgsz: number;
  serial_enabled: boolean;
  motor_duration_ms: number;
  motor_speed: number;
  allowed_classes: string[];
  future_reject_classes: string[];
  model_path: string;
}

export interface DeviceConfigPayload {
  wifi_ssid: string;
  has_wifi_password: boolean;
  wifi_password?: string;
  api_base_url: string;
  predict_url: string;
  capture_interval_ms: number;
  updated_at: number;
  configured: boolean;
  esp32_softap_ssid: string;
  esp32_softap_ip: string;
  provision_path: string;
  ok?: boolean;
  instructions?: string[];
}

export interface LiveEvent {
  type: string;
  request_id?: string;
  phase?: string;
  ewaste?: boolean;
  category?: string;
  confidence?: number;
  inference_ms?: number;
  serial_command?: string | null;
  serial_status?: string | null;
  detections?: Detection[];
  original_image_b64?: string | null;
  annotated_image_b64?: string | null;
  timestamp?: number;
  message?: string;
  frame_index?: number;
  final_decision?: boolean;
}
