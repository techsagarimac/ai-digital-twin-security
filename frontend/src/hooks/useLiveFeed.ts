import { useEffect, useRef, useState } from "react";
import type { FrameMessage, PersonLive, Reconstruction, TimelineEvent } from "../types";

const MAX_EVENTS = 250;

export function useLiveFeed() {
  const [frame, setFrame] = useState<FrameMessage | null>(null);
  const [people, setPeople] = useState<PersonLive[]>([]);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [recon, setRecon] = useState<Record<string, Reconstruction>>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws/live`;
    let closed = false;
    let ping: number | undefined;

    const connect = () => {
      if (closed) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        setConnected(true);
        ping = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        }, 15000);
      };
      ws.onclose = () => {
        setConnected(false);
        if (ping) window.clearInterval(ping);
        if (!closed) window.setTimeout(connect, 1200);
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as FrameMessage;
          if (msg.type === "frame") {
            setFrame(msg);
            setPeople(msg.people || []);
            setRecon(msg.reconstruction || {});
            if (msg.events?.length) {
              setEvents((prev) => [...msg.events, ...prev].slice(0, MAX_EVENTS));
            }
          }
        } catch {
          /* ignore */
        }
      };
    };
    connect();
    return () => {
      closed = true;
      if (ping) window.clearInterval(ping);
      wsRef.current?.close();
    };
  }, []);

  return { frame, people, events, recon, connected };
}
