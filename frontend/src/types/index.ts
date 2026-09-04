export type Landmark = {
  id: number;
  x: number;
  y: number;
  z: number;
  confidence: number;
};

export type DetectedObject = {
  object: string;
  confidence: number;
  bbox: number[];
  timestamp: string;
};

export type Attributes = {
  hair_presence: string;
  hair_color: string;
  hair_style: string;
  hair_length: string;
  hair_confidence: number;
  top_label: string;
  top_color: string;
  top_confidence: number;
  bottom_label: string;
  bottom_color: string;
  bottom_confidence: number;
  shoes_label: string;
  shoes_color: string;
  shoes_confidence: number;
  glasses: string;
  glasses_confidence: number;
  backpack: string;
  backpack_confidence: number;
};

export type PersonLive = {
  person_id: string;
  confidence: number;
  bbox: number[];
  timestamp: string;
  camera_id: string;
  zone_id?: string | null;
  zone_name?: string | null;
  velocity: number[];
  first_seen: string;
  last_seen: string;
  duration_seconds: number;
  duration_label: string;
  observation_count: number;
  orientation: string;
  yaw?: number | null;
  pitch?: number | null;
  roll?: number | null;
  face_bbox?: number[] | null;
  face_landmarks: Landmark[];
  pose_landmarks: Landmark[];
  objects: DetectedObject[];
  attributes: Attributes;
  reconstruction_coverage: number;
  demo?: boolean;
  simulated?: boolean;
};

export type TimelineEvent = {
  id?: string;
  person_id?: string | null;
  type: string;
  timestamp: string;
  camera_id?: string;
  zone_id?: string | null;
  confidence?: number;
  metadata?: Record<string, unknown>;
  demo?: boolean;
};

export type Reconstruction = {
  person_id: string;
  label: string;
  disclaimer: string;
  coverage: number;
  views: Record<string, boolean>;
  mesh_confidence: number;
  insufficient: string[];
  pose_landmarks: Landmark[];
  face_landmarks: Landmark[];
  skeleton_edges: number[][];
  objects: DetectedObject[];
  yaw?: number | null;
  pitch?: number | null;
  roll?: number | null;
};

export type FrameMessage = {
  type: string;
  timestamp: string;
  camera_id: string;
  fps: number;
  device: string;
  demo_mode: boolean;
  simulated?: boolean;
  width: number;
  height: number;
  jpeg_base64: string;
  people: PersonLive[];
  events: TimelineEvent[];
  model_status: {
    detector: string;
    face: string;
    pose: string;
    accessories: string;
    speech: string;
    device: string;
    messages: string[];
  };
  microphone: "ON" | "OFF";
  reconstruction: Record<string, Reconstruction>;
};

export type CameraInfo = {
  id: string;
  source: string;
  status: string;
  demo_mode: boolean;
  message: string;
  width: number;
  height: number;
  fps: number;
  device: string;
};

export type Health = {
  status: string;
  app: string;
  env: string;
  device: string;
  demo_mode: boolean;
  camera: string;
  models: Record<string, string>;
  microphone: "ON" | "OFF";
  identity_module: "OFF" | "ON";
  time: string;
};

export type Zone = {
  id: string;
  name: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  camera_id: string;
};

export type Analytics = {
  people_per_hour: { hour: string; count: number }[];
  average_dwell_seconds: number;
  zone_occupancy: { zone: string; visits: number }[];
  most_visited_zones: { zone: string; visits: number }[];
  detection_events: { type: string; count: number }[];
  object_detections: { object: string; count: number }[];
  camera_activity: { hour: string; frames: number }[];
  reconstruction_coverage: { person_id: string; coverage: number }[];
  speech_event_count: number;
  people_detected: number;
  active_people: number;
  events_today: number;
};

export type AppSettings = {
  detection_confidence: number;
  object_confidence: number;
  tracking_timeout: number;
  process_every_n_frames: number;
  reconstruction_enabled: boolean;
  audio_enabled: boolean;
  demo_mode: boolean;
  data_retention_days: number;
  model_device: string;
  identity_module_enabled: boolean;
  microphone: "ON" | "OFF";
};
