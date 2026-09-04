# Models

This directory is for optional local weights. Nothing here is required to start
the application.

## Detector (person + accessories)

Preferred: a YOLO-family model via Ultralytics.

```bash
# from the project root, with the backend venv active
pip install ultralytics
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

Ultralytics downloads `yolov8n.pt` on first use (COCO classes, including
`person`, `backpack`, `handbag`, `umbrella`, `bottle`, `cell phone`, …).

Place custom weights here if you train your own detector:

```
models/person-detector.pt
```

Then set `YOLO_WEIGHTS=models/person-detector.pt` in `.env` (optional; the
default is `yolov8n.pt`).

If Ultralytics is not installed, the backend uses OpenCV HOG when available.
On OpenCV 5 (no HOG/Haar), it tracks **faces** from YuNet or a skin-region
fallback so a close-up webcam still works.

## Face mesh and pose

Preferred: MediaPipe. Fallback on this machine: OpenCV **YuNet**
(`models/face_detection_yunet_2023mar.onnx`), then a skin-region estimator.

The dashboard **Start webcam** button captures the camera in the browser
(macOS Camera permission) and streams frames to the backend. Allow camera
access when the browser prompts you, then look at the lens.

## Speech

Preferred: faster-whisper (optional).

```bash
pip install faster-whisper
```

Audio is **off by default**. The UI must show `MICROPHONE: OFF` until the
operator enables it. There is no always-on secret recording.

## Device

`MODEL_DEVICE=auto` uses CUDA when PyTorch reports a GPU, otherwise CPU.
CUDA is never mandatory.

Do not commit large weight files or API keys.
