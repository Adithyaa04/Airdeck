"""
gesture_detector.py — SignFlow
All gesture recognition logic: finger states, swipe detection, pinch, fist, etc.
"""

import time
import mediapipe as mp
import numpy as np
from dataclasses import dataclass, field
from utils import euclidean_distance, SwipeBuffer, PositionSmoother


# ──────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────

@dataclass
class GestureResult:
    """Holds the output of a single gesture-detection pass."""
    gesture: str = "NONE"           # e.g. "SWIPE_RIGHT", "OPEN_PALM"
    confidence: float = 0.0         # 0.0 – 1.0
    label: str = ""                 # Human-readable display string
    swipe_direction: str | None = None
    is_pinching: bool = False
    index_tip: tuple = (0, 0)       # pixel coords on frame
    wrist_pos: tuple = (0, 0)
    all_landmarks: list = field(default_factory=list)


# ──────────────────────────────────────────────
# FINGER STATE HELPERS
# ──────────────────────────────────────────────

# MediaPipe landmark indices
WRIST       = 0
THUMB_CMC   = 1
THUMB_MCP   = 2
THUMB_IP    = 3
THUMB_TIP   = 4
INDEX_MCP   = 5
INDEX_PIP   = 6
INDEX_DIP   = 7
INDEX_TIP   = 8
MIDDLE_MCP  = 9
MIDDLE_PIP  = 10
MIDDLE_DIP  = 11
MIDDLE_TIP  = 12
RING_MCP    = 13
RING_PIP    = 14
RING_DIP    = 15
RING_TIP    = 16
PINKY_MCP   = 17
PINKY_PIP   = 18
PINKY_DIP   = 19
PINKY_TIP   = 20


def _lm(landmarks, idx):
    """Return (x, y, z) normalised coords of a landmark."""
    lm = landmarks[idx]
    return lm.x, lm.y, lm.z


def _is_finger_up(landmarks, tip_idx, pip_idx) -> bool:
    """True when a finger is extended (tip above its PIP joint in image space)."""
    tip_y = landmarks[tip_idx].y
    pip_y = landmarks[pip_idx].y
    return tip_y < pip_y  # y increases downward


def _is_thumb_up(landmarks, hand_label: str = "Right") -> bool:
    """
    Thumb direction depends on which hand it is.
    Checks if thumb tip is further from the palm centre than the IP joint.
    """
    tip_x = landmarks[THUMB_TIP].x
    ip_x  = landmarks[THUMB_IP].x
    # For a right hand viewed from front: thumb extends to the left (lower x)
    if hand_label == "Right":
        return tip_x < ip_x
    else:
        return tip_x > ip_x


def get_finger_states(landmarks, hand_label: str = "Right") -> dict[str, bool]:
    """
    Return a dict of {finger_name: is_extended} for all five fingers.
    """
    return {
        "thumb":  _is_thumb_up(landmarks, hand_label),
        "index":  _is_finger_up(landmarks, INDEX_TIP,  INDEX_PIP),
        "middle": _is_finger_up(landmarks, MIDDLE_TIP, MIDDLE_PIP),
        "ring":   _is_finger_up(landmarks, RING_TIP,   RING_PIP),
        "pinky":  _is_finger_up(landmarks, PINKY_TIP,  PINKY_PIP),
    }


# ──────────────────────────────────────────────
# GESTURE DETECTOR CLASS
# ──────────────────────────────────────────────

class GestureDetector:
    """
    Processes MediaPipe hand landmarks and returns a classified GestureResult.

    Detectable gestures:
      SWIPE_RIGHT   → next slide
      SWIPE_LEFT    → previous slide
      OPEN_PALM     → play / pause
      PINCH         → laser pointer
      TWO_FINGERS   → annotation mode
      THUMBS_UP     → start slideshow
      CLOSED_FIST   → exit / esc
      NONE          → no recognised gesture
    """

    # Tunable constants — adjust here or pass via constructor
    PINCH_THRESHOLD         = 0.06   # normalised distance; smaller = tighter pinch needed
    SWIPE_DISPLACEMENT      = 0.12   # minimum horizontal travel
    SWIPE_SPEED             = 0.28   # units/second
    SWIPE_TIME_WINDOW       = 0.55   # seconds of history to consider
    CONFIDENCE_SMOOTH_ALPHA = 0.35   # EMA alpha for confidence smoothing

    def __init__(
        self,
        pinch_threshold: float = None,
        swipe_displacement: float = None,
        swipe_speed: float = None,
    ):
        if pinch_threshold   is not None: self.PINCH_THRESHOLD    = pinch_threshold
        if swipe_displacement is not None: self.SWIPE_DISPLACEMENT = swipe_displacement
        if swipe_speed        is not None: self.SWIPE_SPEED        = swipe_speed

        self.swipe_buffer = SwipeBuffer(maxlen=12)
        self.wrist_smoother = PositionSmoother(window_size=5)

        self._prev_gesture: str = "NONE"
        self._gesture_start_time: float = 0.0
        self._smoothed_confidence: float = 0.0

    # ── Public API ──────────────────────────────

    def detect(self, hand_landmarks, frame_w: int, frame_h: int, hand_label: str = "Right") -> GestureResult:
        """
        Main entry point. Pass MediaPipe NormalizedLandmarkList and frame size.
        Returns a GestureResult.
        """
        lms = hand_landmarks.landmark

        # Pixel coordinates helpers
        def px(idx):
            return int(lms[idx].x * frame_w), int(lms[idx].y * frame_h)

        # Smoothed wrist position (normalised)
        raw_wx, raw_wy = lms[WRIST].x, lms[WRIST].y
        sw_x, sw_y = self.wrist_smoother.update(raw_wx, raw_wy)

        # Push wrist x to swipe buffer (flipped to match display)
        self.swipe_buffer.push(1.0 - sw_x)

        fingers = get_finger_states(lms, hand_label)
        n_up = sum(fingers.values())

        result = GestureResult()
        result.wrist_pos  = px(WRIST)
        result.index_tip  = px(INDEX_TIP)
        result.all_landmarks = [px(i) for i in range(21)]

        # ── Detect individual gestures in priority order ──

        gesture, conf = self._classify(lms, fingers, n_up, frame_w, frame_h, hand_label)

        # Smooth confidence using EMA
        self._smoothed_confidence = (
            self.CONFIDENCE_SMOOTH_ALPHA * conf
            + (1 - self.CONFIDENCE_SMOOTH_ALPHA) * self._smoothed_confidence
        )

        result.gesture    = gesture
        result.confidence = self._smoothed_confidence
        result.label      = self._label_for(gesture)
        result.is_pinching = gesture == "PINCH"

        return result

    # ── Classification ───────────────────────────

    def _classify(self, lms, fingers, n_up, fw, fh, hand_label) -> tuple[str, float]:
        """Classify and return (gesture_name, confidence)."""

        # 1. PINCH — high priority so it doesn't get classified as two-fingers
        pinch_dist = self._pinch_distance(lms)
        if pinch_dist < self.PINCH_THRESHOLD:
            conf = 1.0 - (pinch_dist / self.PINCH_THRESHOLD)
            return "PINCH", min(conf * 1.4, 1.0)

        # 2. SWIPE detection
        swipe = self.swipe_buffer.detect_swipe(
            displacement_thresh=self.SWIPE_DISPLACEMENT,
            speed_thresh=self.SWIPE_SPEED,
            time_window=self.SWIPE_TIME_WINDOW,
        )
        if swipe == "right":
            self.swipe_buffer.clear()
            return "SWIPE_RIGHT", 0.95
        if swipe == "left":
            self.swipe_buffer.clear()
            return "SWIPE_LEFT", 0.95

        # 3. CLOSED FIST — all fingers down
        if n_up == 0:
            return "CLOSED_FIST", 0.90

        # 4. OPEN PALM — all five up
        if n_up == 5:
            return "OPEN_PALM", 0.92

        # 5. THUMBS UP — only thumb
        if fingers["thumb"] and not fingers["index"] and not fingers["middle"] \
                and not fingers["ring"] and not fingers["pinky"]:
            return "THUMBS_UP", 0.88

        # 6. TWO FINGERS (index + middle only)
        if fingers["index"] and fingers["middle"] \
                and not fingers["thumb"] and not fingers["ring"] and not fingers["pinky"]:
            return "TWO_FINGERS", 0.85

        return "NONE", 0.0

    def _pinch_distance(self, lms) -> float:
        """Normalised Euclidean distance between thumb tip and index tip."""
        tx, ty = lms[THUMB_TIP].x, lms[THUMB_TIP].y
        ix, iy = lms[INDEX_TIP].x, lms[INDEX_TIP].y
        return euclidean_distance((tx, ty), (ix, iy))

    @staticmethod
    def _label_for(gesture: str) -> str:
        labels = {
            "SWIPE_RIGHT":  "NEXT SLIDE  →",
            "SWIPE_LEFT":   "←  PREV SLIDE",
            "OPEN_PALM":    "PLAY / PAUSE",
            "PINCH":        "LASER MODE",
            "TWO_FINGERS":  "ANNOTATE",
            "THUMBS_UP":    "START SLIDESHOW",
            "CLOSED_FIST":  "EXIT",
            "NONE":         "",
        }
        return labels.get(gesture, "")
