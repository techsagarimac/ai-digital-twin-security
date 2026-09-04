import { createContext, useContext } from "react";
import type { FrameMessage, PersonLive, Reconstruction, TimelineEvent } from "../types";

export type LiveState = {
  frame: FrameMessage | null;
  people: PersonLive[];
  events: TimelineEvent[];
  recon: Record<string, Reconstruction>;
  connected: boolean;
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
};

export const LiveContext = createContext<LiveState | null>(null);

export function useLive() {
  const ctx = useContext(LiveContext);
  if (!ctx) throw new Error("LiveContext missing");
  return ctx;
}
