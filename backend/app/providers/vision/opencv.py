"""OpenCV Haar-cascade face detection (default smart-reframing provider).

Fully local: OpenCV ships the cascade classifier and there is no model
download. Frames are sampled on a fixed interval and only the largest face in
each sampled frame is kept, giving a stable subject anchor per timestamp.
"""

from __future__ import annotations

from pathlib import Path

from app.providers.vision.base import SubjectSample, SubjectTrack, VisionProvider

_CASCADE_FILE = "haarcascade_frontalface_default.xml"


class OpenCVVisionProvider(VisionProvider):
    """Face detection via OpenCV's bundled Haar cascade."""

    def __init__(self, sample_interval_seconds: float = 1.0, min_confidence: float = 0.5) -> None:
        self._interval = max(sample_interval_seconds, 0.1)
        self._min_confidence = min_confidence

    @property
    def name(self) -> str:
        return "opencv"

    def is_available(self) -> bool:
        try:
            import cv2  # noqa: F401  (availability probe only)
        except ImportError:
            return False
        return True

    def track_subjects(self, video_path: Path, *, duration_seconds: float) -> SubjectTrack:
        import cv2

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return SubjectTrack(samples=())
        try:
            samples = self._sample(cv2, capture, duration_seconds)
        finally:
            capture.release()
        return SubjectTrack(samples=tuple(samples))

    def _sample(self, cv2, capture, duration_seconds: float) -> list[SubjectSample]:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + _CASCADE_FILE)
        duration = duration_seconds or self._duration(cv2, capture)
        if duration <= 0:
            return []

        samples: list[SubjectSample] = []
        time = 0.0
        while time <= duration:
            capture.set(cv2.CAP_PROP_POS_MSEC, time * 1000.0)
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            sample = self._detect(cv2, cascade, frame, time)
            if sample is not None:
                samples.append(sample)
            time += self._interval
        return samples

    @staticmethod
    def _duration(cv2, capture) -> float:
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if fps and frames:
            return float(frames / fps)
        return 0.0

    def _detect(self, cv2, cascade, frame, time_seconds: float) -> SubjectSample | None:
        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda box: int(box[2]) * int(box[3]))
        confidence = min(1.0, 0.6 + (w * h) / float(width * height))
        if confidence < self._min_confidence:
            return None
        return SubjectSample(
            time_seconds=round(time_seconds, 3),
            x_center=round((x + w / 2) / width, 4),
            y_center=round((y + h / 2) / height, 4),
            width=round(w / width, 4),
            height=round(h / height, 4),
            confidence=round(confidence, 4),
        )
