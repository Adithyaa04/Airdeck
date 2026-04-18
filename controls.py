"""
controls.py — SignFlow
Maps gestures to system-level keyboard / mouse actions via PyAutoGUI.
"""

import pyautogui
import time
from utils import DebounceManager

# Disable PyAutoGUI fail-safe (move mouse to corner) — set True for safety during dev
pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.0  # Remove built-in delay for snappy response


# ──────────────────────────────────────────────
# GESTURE → ACTION MAP
# ──────────────────────────────────────────────

GESTURE_COOLDOWNS = {
    "SWIPE_RIGHT":  0.8,
    "SWIPE_LEFT":   0.8,
    "OPEN_PALM":    1.2,
    "THUMBS_UP":    2.0,
    "CLOSED_FIST":  1.5,
    "TWO_FINGERS":  0.5,
    "PINCH":        0.05,  # Very short — continuous laser mode
}


class HandGestureController:
    """
    Executes system actions based on recognised gestures.

    Manages:
    - Keyboard shortcuts (next/prev slide, F5, ESC, space)
    - Laser pointer mouse movement
    - Annotation mode toggling
    - Debouncing per gesture
    """

    def __init__(self, cooldown_multiplier: float = 1.0):
        """
        Args:
            cooldown_multiplier: Scale all cooldowns (0.5 = faster, 2.0 = slower).
        """
        self.debounce = DebounceManager(default_cooldown=1.0)
        self.cooldown_multiplier = cooldown_multiplier

        # Internal state
        self.annotation_mode: bool  = False
        self.laser_mode: bool       = False
        self.last_mouse_pos: tuple  = (0, 0)

        # Pointer smoother for laser (separate from gesture smoother)
        from utils import PositionSmoother
        self._pointer_smoother = PositionSmoother(window_size=6)

    # ── Primary dispatcher ───────────────────────

    def handle(
        self,
        gesture: str,
        index_tip_screen: tuple[int, int] | None = None,
        annotation_points: list | None = None,
    ) -> str | None:
        """
        Process a detected gesture.

        Args:
            gesture            : e.g. "SWIPE_RIGHT"
            index_tip_screen   : (x, y) screen coords for laser/annotation
            annotation_points  : mutable list to append annotation points

        Returns:
            action string for UI feedback, or None.
        """
        cooldown = GESTURE_COOLDOWNS.get(gesture, 1.0) * self.cooldown_multiplier

        # ── LASER MODE (continuous, no hard debounce) ──
        if gesture == "PINCH":
            self.laser_mode = True
            self.annotation_mode = False
            if index_tip_screen:
                sx, sy = self._pointer_smoother.update(*index_tip_screen)
                sx, sy = int(sx), int(sy)
                try:
                    pyautogui.moveTo(sx, sy, duration=0)
                except Exception:
                    pass
                self.last_mouse_pos = (sx, sy)
            return "LASER"
        else:
            self.laser_mode = False

        # ── ANNOTATION MODE (continuous while TWO_FINGERS held) ──
        if gesture == "TWO_FINGERS":
            self.annotation_mode = True
            if index_tip_screen and annotation_points is not None:
                annotation_points.append(index_tip_screen)
            return "ANNOTATE"
        else:
            if self.annotation_mode:
                # Add a sentinel None to break the line when finger lifted
                if annotation_points is not None:
                    annotation_points.append(None)
            self.annotation_mode = False

        # ── DEBOUNCED ONE-SHOT GESTURES ──
        if not self.debounce.is_ready(gesture, cooldown):
            return None

        action = None

        if gesture == "SWIPE_RIGHT":
            self._press("right")
            action = "NEXT_SLIDE"

        elif gesture == "SWIPE_LEFT":
            self._press("left")
            action = "PREV_SLIDE"

        elif gesture == "OPEN_PALM":
            self._press("space")
            action = "PLAY_PAUSE"

        elif gesture == "THUMBS_UP":
            self._press("f5")
            action = "START_SLIDESHOW"

        elif gesture == "CLOSED_FIST":
            self._press("escape")
            action = "EXIT"

        if action:
            self.debounce.trigger(gesture)

        return action

    # ── Helpers ─────────────────────────────────

    @staticmethod
    def _press(key: str):
        """Safely press a key, catching any pyautogui exceptions."""
        try:
            pyautogui.press(key)
        except Exception as e:
            print(f"[controls] Key press failed: {e}")

    def get_cooldown_fraction(self, gesture: str) -> float:
        """Return 0.0–1.0 of how much cooldown has elapsed for a gesture."""
        cooldown = GESTURE_COOLDOWNS.get(gesture, 1.0) * self.cooldown_multiplier
        return self.debounce.cooldown_fraction(gesture, cooldown)
