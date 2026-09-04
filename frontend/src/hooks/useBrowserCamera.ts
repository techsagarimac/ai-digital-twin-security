import { useRef } from "react";

/** Captures the user's webcam in the browser and POSTs JPEGs to the backend. */
export function useBrowserCamera() {
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const runningRef = useRef(false);

  const stop = () => {
    runningRef.current = false;
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    videoRef.current?.pause();
    videoRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const start = async () => {
    stop();
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 540 } },
      audio: false,
    });
    streamRef.current = stream;
    runningRef.current = true;
    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.srcObject = stream;
    await video.play();
    videoRef.current = video;
    const canvas = document.createElement("canvas");

    const tick = async () => {
      if (!runningRef.current || !videoRef.current) return;
      const clip = videoRef.current;
      if (clip.videoWidth >= 16) {
        canvas.width = clip.videoWidth;
        canvas.height = clip.videoHeight;
        const ctx = canvas.getContext("2d");
        ctx?.drawImage(clip, 0, 0);
        const blob: Blob | null = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.72));
        if (blob && runningRef.current) {
          const data = new FormData();
          data.append("file", blob, "frame.jpg");
          await fetch("/api/cameras/frame", { method: "POST", body: data }).catch(() => undefined);
        }
      }
      if (runningRef.current) {
        timerRef.current = window.setTimeout(tick, 80);
      }
    };
    void tick();
  };

  return { start, stop };
}
