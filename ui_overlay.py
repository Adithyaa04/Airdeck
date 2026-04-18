"""
ui_overlay.py — SignFlow
All visual rendering: overlays, panels, laser pointer, trails, annotation, flash.
"""

import cv2
import numpy as np
import math
import time
from collections import deque


# ──────────────────────────────────────────────
# COLOUR PALETTE
# ──────────────────────────────────────────────

# BGR colours
C_ACCENT      = (0,   220, 255)   # Cyan-gold accent
C_GREEN       = (50,  230, 100)
C_RED         = (40,   60, 220)   # Red in BGR
C_ORANGE      = (30,  160, 255)
C_WHITE       = (255, 255, 255)
C_BLACK       = (0,     0,   0)
C_DARK        = (20,   20,  30)
C_PANEL_BG    = (10,   10,  18)   # Deep dark panel
C_LASER       = (0,    50, 255)   # Bright red laser dot
C_TRAIL       = (0,   200, 255)   # Swipe trail
C_ANNOTATE    = (60,  255, 120)   # Annotation green
C_FLASH_GOOD  = (50,  230, 100)   # Green flash
C_FLASH_BAD   = (40,   60, 200)   # Red flash
C_LANDMARK    = (0,   200, 255)
C_BONE        = (120, 200, 255)


# ──────────────────────────────────────────────
# OVERLAY PRIMITIVES
# ──────────────────────────────────────────────

def draw_translucent_rect(frame, x1, y1, x2, y2, color, alpha=0.55, radius=8):
    """Draw a semi-transparent rounded rectangle on the frame (in-place)."""
    overlay = frame.copy()
    # Fill rounded rect using ellipse corners
    cv2.rectangle(overlay, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2 - radius), color, -1)
    cv2.ellipse(overlay, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, -1)
    cv2.ellipse(overlay, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, -1)
    cv2.ellipse(overlay, (x1 + radius, y2 - radius), (radius, radius),  90, 0, 90, color, -1)
    cv2.ellipse(overlay, (x2 - radius, y2 - radius), (radius, radius),   0, 0, 90, color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def put_text_shadow(frame, text, pos, font_scale=0.7, color=C_WHITE, thickness=1):
    """Draw text with a subtle drop shadow."""
    x, y = pos
    cv2.putText(frame, text, (x + 1, y + 1), cv2.FONT_HERSHEY_DUPLEX,
                font_scale, C_BLACK, thickness + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_DUPLEX,
                font_scale, color, thickness, cv2.LINE_AA)


# ──────────────────────────────────────────────
# MOTION TRAIL
# ──────────────────────────────────────────────

class MotionTrail:
    """Stores recent hand positions and renders a fading swipe trail."""

    def __init__(self, maxlen: int = 20):
        self.points: deque = deque(maxlen=maxlen)

    def push(self, pt: tuple):
        self.points.append(pt)

    def draw(self, frame, color=C_TRAIL, base_thickness: int = 3):
        pts = list(self.points)
        if len(pts) < 2:
            return
        n = len(pts)
        for i in range(1, n):
            alpha = i / n                     # grows from transparent to opaque
            thickness = max(1, int(base_thickness * alpha))
            col = tuple(int(c * alpha) for c in color)
            cv2.line(frame, pts[i - 1], pts[i], col, thickness, cv2.LINE_AA)

    def clear(self):
        self.points.clear()


# ──────────────────────────────────────────────
# GESTURE FLASH
# ──────────────────────────────────────────────

class GestureFlash:
    """Renders a brief screen-edge flash when a gesture fires."""

    def __init__(self, duration: float = 0.35):
        self.duration = duration
        self._start: float = 0.0
        self._color: tuple = C_FLASH_GOOD
        self._label: str   = ""

    def trigger(self, label: str, color: tuple = C_FLASH_GOOD):
        self._start = time.time()
        self._color = color
        self._label = label

    def draw(self, frame):
        elapsed = time.time() - self._start
        if elapsed >= self.duration:
            return
        progress = elapsed / self.duration
        alpha = (1.0 - progress) * 0.4
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), self._color, -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        if self._label:
            text_size = cv2.getTextSize(self._label, cv2.FONT_HERSHEY_DUPLEX, 1.4, 2)[0]
            tx = (w - text_size[0]) // 2
            ty = (h + text_size[1]) // 2
            put_text_shadow(frame, self._label, (tx, ty),
                            font_scale=1.4, color=C_WHITE, thickness=2)


# ──────────────────────────────────────────────
# LANDMARK RENDERER
# ──────────────────────────────────────────────

# MediaPipe hand connections (index pairs)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),           # index
    (0, 9), (9, 10), (10, 11), (11, 12),      # middle
    (0, 13), (13, 14), (14, 15), (15, 16),    # ring
    (0, 17), (17, 18), (18, 19), (19, 20),    # pinky
    (5, 9), (9, 13), (13, 17),                # palm
]

def draw_landmarks(frame, px_landmarks: list, is_pinching: bool = False):
    """
    Draw hand skeleton from pixel coordinate list.
    px_landmarks: list of (x, y) tuples for all 21 landmarks.
    """
    # Bones
    for a, b in HAND_CONNECTIONS:
        pt1, pt2 = px_landmarks[a], px_landmarks[b]
        cv2.line(frame, pt1, pt2, C_BONE, 2, cv2.LINE_AA)

    # Joints
    for i, pt in enumerate(px_landmarks):
        r = 5 if i in (4, 8, 12, 16, 20) else 3
        col = C_ACCENT if i in (4, 8) and is_pinching else C_LANDMARK
        cv2.circle(frame, pt, r, col, -1, cv2.LINE_AA)
        cv2.circle(frame, pt, r + 1, C_BLACK, 1, cv2.LINE_AA)


# ──────────────────────────────────────────────
# LASER POINTER
# ──────────────────────────────────────────────

def draw_laser(frame, pt: tuple, pulse: float):
    """
    Draw a glowing red laser dot.
    pt    : (x, y) pixel coordinate on frame
    pulse : 0.0–1.0 animated pulse factor (call with time.time() * 3 % 1.0)
    """
    glow_r = int(18 + 6 * math.sin(pulse * 2 * math.pi))
    # Outer glow layers
    for r, alpha in [(glow_r, 0.08), (glow_r - 5, 0.15), (glow_r - 10, 0.30)]:
        if r > 0:
            overlay = frame.copy()
            cv2.circle(overlay, pt, r, C_LASER, -1, cv2.LINE_AA)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    # Core dot
    cv2.circle(frame, pt, 5, C_LASER, -1, cv2.LINE_AA)
    cv2.circle(frame, pt, 5, C_WHITE, 1, cv2.LINE_AA)


# ──────────────────────────────────────────────
# ANNOTATION RENDERER
# ──────────────────────────────────────────────

def draw_annotations(frame, points: list, color=C_ANNOTATE, thickness: int = 3):
    """
    Draw annotation strokes from a list of (x, y) or None (line break).
    """
    prev = None
    for pt in points:
        if pt is None:
            prev = None
            continue
        if prev is not None:
            cv2.line(frame, prev, pt, color, thickness, cv2.LINE_AA)
        prev = pt


# ──────────────────────────────────────────────
# CONFIDENCE BAR
# ──────────────────────────────────────────────

def draw_confidence_bar(frame, x, y, w, h, fraction: float, label: str = ""):
    """Draw a small horizontal progress bar."""
    draw_translucent_rect(frame, x, y, x + w, y + h, C_PANEL_BG, alpha=0.7, radius=4)
    fill_w = int(w * fraction)
    if fill_w > 0:
        col = C_GREEN if fraction > 0.6 else C_ORANGE
        cv2.rectangle(frame, (x + 2, y + 2), (x + fill_w - 2, y + h - 2), col, -1)
    if label:
        put_text_shadow(frame, label, (x + w + 6, y + h - 3),
                        font_scale=0.42, color=C_WHITE, thickness=1)


# ──────────────────────────────────────────────
# MAIN UI MANAGER
# ──────────────────────────────────────────────

class UIManager:
    """
    Central UI renderer. Call draw_frame() each loop iteration.
    """

    HELP_ITEMS = [
        ("Swipe R/L", "Next/Prev"),
        ("Open Palm", "Play/Pause"),
        ("Pinch",     "Laser"),
        ("2 Fingers", "Annotate"),
        ("👍",        "Slideshow"),
        ("Fist",      "Exit"),
    ]

    def __init__(self):
        self.trail    = MotionTrail(maxlen=22)
        self.flash    = GestureFlash(duration=0.4)
        self._last_gesture_label: str = ""
        self._mode_label: str         = "READY"

    def set_mode(self, mode: str):
        self._mode_label = mode

    def notify_action(self, action: str):
        """Called when a gesture fires — triggers flash and mode update."""
        action_map = {
            "NEXT_SLIDE":    ("NEXT SLIDE  →",  C_FLASH_GOOD),
            "PREV_SLIDE":    ("←  PREV SLIDE",  C_FLASH_GOOD),
            "PLAY_PAUSE":    ("PLAY / PAUSE",    C_ACCENT),
            "START_SLIDESHOW": ("SLIDESHOW",     C_FLASH_GOOD),
            "EXIT":          ("EXIT",            C_FLASH_BAD),
            "LASER":         None,
            "ANNOTATE":      None,
        }
        entry = action_map.get(action)
        if entry:
            self.flash.trigger(*entry)

    def draw_frame(
        self,
        frame,
        gesture_result,
        is_laser: bool,
        is_annotate: bool,
        annotation_points: list,
        confidence: float,
        action_fired: str | None,
    ):
        """
        Render all UI elements onto the frame (in-place).

        Args:
            frame           : BGR OpenCV frame
            gesture_result  : GestureResult dataclass
            is_laser        : bool
            is_annotate     : bool
            annotation_points: list of (x,y)/None
            confidence      : float 0-1
            action_fired    : optional action string for flash
        """
        h, w = frame.shape[:2]

        # ── Hand skeleton ──
        if gesture_result.all_landmarks:
            draw_landmarks(frame, gesture_result.all_landmarks, gesture_result.is_pinching)

        # ── Motion trail ──
        if gesture_result.wrist_pos != (0, 0):
            self.trail.push(gesture_result.wrist_pos)
        self.trail.draw(frame)

        # ── Laser pointer ──
        if is_laser and gesture_result.index_tip != (0, 0):
            pulse = (time.time() * 4) % 1.0
            draw_laser(frame, gesture_result.index_tip, pulse)

        # ── Annotations ──
        if annotation_points:
            draw_annotations(frame, annotation_points)

        # ── Gesture flash ──
        if action_fired:
            self.notify_action(action_fired)
        self.flash.draw(frame)

        # ── Top-left panel: gesture name ──
        gesture_text = gesture_result.label or "No Gesture"
        self._draw_top_left_panel(frame, gesture_text, confidence)

        # ── Top-right panel: mode ──
        mode = "LASER" if is_laser else ("ANNOTATE" if is_annotate else self._mode_label)
        self._draw_top_right_panel(frame, mode, w)

        # ── Bottom help bar ──
        self._draw_help_bar(frame, h, w)

        # ── Confidence bar ──
        draw_confidence_bar(frame, 12, 90, 150, 14, confidence, "conf")

        # ── SignFlow watermark ──
        put_text_shadow(frame, "SignFlow", (w - 100, h - 12),
                        font_scale=0.5, color=(120, 120, 140), thickness=1)

    # ── Private helpers ──────────────────────────

    def _draw_top_left_panel(self, frame, gesture_text, confidence):
        draw_translucent_rect(frame, 8, 8, 300, 82, C_PANEL_BG, alpha=0.72)
        # Tiny label
        put_text_shadow(frame, "GESTURE", (18, 28), font_scale=0.42,
                        color=(140, 200, 220), thickness=1)
        # Main gesture text
        font_scale = 0.75 if len(gesture_text) <= 14 else 0.58
        put_text_shadow(frame, gesture_text, (18, 62),
                        font_scale=font_scale, color=C_ACCENT, thickness=1)

    def _draw_top_right_panel(self, frame, mode, frame_w):
        panel_w = 160
        x1 = frame_w - panel_w - 8
        draw_translucent_rect(frame, x1, 8, frame_w - 8, 52, C_PANEL_BG, alpha=0.72)
        put_text_shadow(frame, "MODE", (x1 + 10, 27), font_scale=0.42,
                        color=(140, 200, 220), thickness=1)
        col = C_GREEN if mode == "READY" else C_ORANGE
        put_text_shadow(frame, mode, (x1 + 10, 46), font_scale=0.6,
                        color=col, thickness=1)

    def _draw_help_bar(self, frame, h, w):
        bar_h = 32
        draw_translucent_rect(frame, 0, h - bar_h, w, h, C_PANEL_BG, alpha=0.8, radius=0)
        n = len(self.HELP_ITEMS)
        step = w // n
        for i, (key, val) in enumerate(self.HELP_ITEMS):
            x = i * step + step // 2 - 50
            text = f"{key}: {val}"
            put_text_shadow(frame, text, (x, h - 10), font_scale=0.38,
                            color=(180, 190, 200), thickness=1)

        # Separator dots
        for i in range(1, n):
            sx = i * step
            cv2.circle(frame, (sx, h - 16), 2, (80, 80, 100), -1)
