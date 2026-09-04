import type { Analytics, AppSettings, CameraInfo, Health, PersonLive, TimelineEvent, Zone } from "../types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.text()) as T;
}

export const api = {
  health: () => req<Health>("/api/health"),
  cameras: () => req<CameraInfo[]>("/api/cameras"),
  cameraStatus: () => req<CameraInfo>("/api/cameras/status"),
  startCamera: (body: Record<string, unknown>) =>
    req<CameraInfo>("/api/cameras/start", { method: "POST", body: JSON.stringify(body) }),
  stopCamera: () => req("/api/cameras/stop", { method: "POST" }),
  uploadVideo: async (file: File) => {
    const data = new FormData();
    data.append("file", file);
    const res = await fetch("/api/cameras/upload", { method: "POST", body: data });
    if (!res.ok) throw new Error("upload failed");
    return (await res.json()) as { path: string; filename: string };
  },
  people: () => req<PersonLive[]>("/api/people"),
  person: (id: string) => req<PersonLive & { reconstruction?: unknown; objects?: unknown; zone_history?: unknown }>(`/api/people/${id}`),
  events: (personId?: string) => req<TimelineEvent[]>(personId ? `/api/events/${personId}` : "/api/events"),
  analytics: () => req<Analytics>("/api/analytics"),
  settings: () => req<AppSettings>("/api/settings"),
  saveSettings: (body: Partial<AppSettings>) =>
    req<AppSettings>("/api/settings", { method: "PUT", body: JSON.stringify(body) }),
  zones: () => req<Zone[]>("/api/zones"),
  saveZone: (z: Partial<Zone> & { id: string; name: string; x1: number; y1: number; x2: number; y2: number }) =>
    req<Zone>("/api/zones", { method: "POST", body: JSON.stringify(z) }),
  toggleAudio: (enabled: boolean) => req("/api/audio/toggle", { method: "POST", body: JSON.stringify({ enabled }) }),
  search: (params: URLSearchParams) => req<TimelineEvent[]>(`/api/search?${params.toString()}`),
  models: () => req("/api/models"),
};
