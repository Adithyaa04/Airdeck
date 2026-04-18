"""
utils.py — SignFlow
Helper utilities: smoothing, distance calculation, debouncing, coordinate mapping.
"""

import math
import time
from collections import deque


# ──────────────────────────────────────────────
# DISTANCE HELPER
# ──────────────────────────────────────────────

def euclidean_distance(p1, p2):
    """Return Euclidean distance between two (x, y) points."""
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


# ──────────────────────────────────────────────
# POSITION SMOOTHER
# ──────────────────────────────────────────────

class PositionSmoother:
    """
    Smooths a (x, y) position stream using a rolling moving average.
    Reduces jitter from hand-tracking noise.
    """

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.x_history: deque = deque(maxlen=window_size)
        self.y_history: deque = deque(maxlen=window_size)

    def update(self, x: float, y: float) -> tuple[float, float]:
        """Add a new point and return the smoothed position."""
        self.x_history.append(x)
        self.y_history.append(y)
        smooth_x = sum(self.x_history) / len(self.x_history)
        smooth_y = sum(self.y_history) / len(self.y_history)
        return smooth_x, smooth_y

    def reset(self):
        self.x_history.clear()
        self.y_history.clear()


# ──────────────────────────────────────────────
# DEBOUNCE MANAGER
# ──────────────────────────────────────────────

class DebounceManager:
    """
    Prevents repeated gesture triggers within a cooldown window.
    Each gesture name has its own independent cooldown timer.
    """

    def __init__(self, default_cooldown: float = 1.0):
        self.default_cooldown = default_cooldown
        self._last_times: dict[str, float] = {}

    def is_ready(self, gesture_name: str, cooldown: float = None) -> bool:
        """Return True if the gesture is allowed to fire (cooldown elapsed)."""
        cooldown = cooldown if cooldown is not None else self.default_cooldown
        now = time.time()
        last = self._last_times.get(gesture_name, 0.0)
        return (now - last) >= cooldown

    def trigger(self, gesture_name: str):
        """Mark a gesture as just triggered."""
        self._last_times[gesture_name] = time.time()

    def time_since(self, gesture_name: str) -> float:
        """Return seconds since the gesture last fired."""
        return time.time() - self._last_times.get(gesture_name, 0.0)

    def cooldown_fraction(self, gesture_name: str, cooldown: float = None) -> float:
        """Return a 0.0–1.0 fraction of how much cooldown has elapsed."""
        cooldown = cooldown if cooldown is not None else self.default_cooldown
        elapsed = self.time_since(gesture_name)
        return min(elapsed / cooldown, 1.0)


# ──────────────────────────────────────────────
# COORDINATE MAPPER
# ──────────────────────────────────────────────

def map_to_screen(
    norm_x: float,
    norm_y: float,
    frame_w: int,
    frame_h: int,
    screen_w: int,
    screen_h: int,
    margin: float = 0.1,
    speed_multiplier: float = 1.0,
) -> tuple[int, int]:
    """
    Map a normalised MediaPipe coordinate (0–1) to screen pixel coordinates.

    Args:
        norm_x / norm_y  : landmark x/y from MediaPipe (0.0 – 1.0)
        frame_w / frame_h: webcam frame size
        screen_w / h     : display resolution
        margin           : fraction of frame to treat as dead-zone at edges
        speed_multiplier : scale factor to amplify pointer movement
    """
    # Clamp to the active region (ignore extreme edge noise)
    active_x = (norm_x - margin) / (1.0 - 2 * margin)
    active_y = (norm_y - margin) / (1.0 - 2 * margin)

    # Mirror horizontally (webcam is flipped)
    active_x = 1.0 - active_x

    # Apply speed multiplier centred on 0.5
    active_x = 0.5 + (active_x - 0.5) * speed_multiplier
    active_y = 0.5 + (active_y - 0.5) * speed_multiplier

    # Clamp to [0, 1]
    active_x = max(0.0, min(1.0, active_x))
    active_y = max(0.0, min(1.0, active_y))

    screen_x = int(active_x * screen_w)
    screen_y = int(active_y * screen_h)
    return screen_x, screen_y


# ──────────────────────────────────────────────
# SWIPE HISTORY BUFFER
# ──────────────────────────────────────────────

class SwipeBuffer:
    """
    Stores recent wrist x-positions with timestamps to detect intentional swipes.
    """

    def __init__(self, maxlen: int = 10):
        self.positions: deque = deque(maxlen=maxlen)  # (x, timestamp)

    def push(self, x: float):
        self.positions.append((x, time.time()))

    def detect_swipe(
        self,
        displacement_thresh: float = 0.12,
        speed_thresh: float = 0.30,
        time_window: float = 0.6,
    ) -> str | None:
        """
        Analyse buffer and return 'right', 'left', or None.

        Args:
            displacement_thresh : minimum total x-movement (0-1 normalised)
            speed_thresh        : minimum speed in units/second
            time_window         : only consider positions within this many seconds
        """
        if len(self.positions) < 4:
            return None

        now = time.time()
        # Filter to recent window
        recent = [(x, t) for x, t in self.positions if now - t <= time_window]
        if len(recent) < 4:
            return None

        oldest_x, oldest_t = recent[0]
        newest_x, newest_t = recent[-1]

        dt = newest_t - oldest_t
        if dt < 0.05:
            return None

        displacement = newest_x - oldest_x
        speed = abs(displacement) / dt

        if abs(displacement) >= displacement_thresh and speed >= speed_thresh:
            return "right" if displacement > 0 else "left"
        return None

    def clear(self):
        self.positions.clear()
