"""
main.py — SignFlow
Real-time gesture-based presentation and productivity controller.

Run:
    python main.py

Optional flags:
    --cam   <int>   webcam device index (default: 0)
    --flip          mirror the feed (default: on)
    --debug         print gesture info to console
    --cooldown <float>  global cooldown multiplier (default: 1.0)
    --sensitivity <float>  swipe sensitivity multiplier (default: 1.0)
"""

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import argparse
import time
import sys

from gesture_detector import GestureDetector, GestureResult
from controls         import HandGestureController
from ui_overlay       import UIManager
from utils            import map_to_screen, PositionSmoother


# ──────────────────────────────────────────────
# CONFIGURATION — tweak these to your liking
# ──────────────────────────────────────────────

class Config:
    CAMERA_INDEX          = 0
    FRAME_WIDTH           = 1280
    FRAME_HEIGHT          = 720
    FLIP_HORIZONTAL       = True     # Mirror for natural interaction

    # MediaPipe
    MAX_NUM_HANDS         = 1
    MIN_DETECTION_CONF    = 0.72
    MIN_TRACKING_CONF     = 0.60

    # Gesture thresholds
    PINCH_THRESHOLD       = 0.06
    SWIPE_DISPLACEMENT    = 0.12
    SWIPE_SPEED           = 0.28

    # System
    COOLDOWN_MULTIPLIER   = 1.0      # Lower = more responsive
    POINTER_SPEED         = 1.2      # Laser pointer amplification
    DEBUG                 = False

    # Annotation
    MAX_ANNOTATION_POINTS = 3000     # Cap to avoid memory growth


# ──────────────────────────────────────────────
# ARGUMENT PARSER
# ──────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="SignFlow – Gesture Presentation Controller")
    parser.add_argument("--cam",         type=int,   default=Config.CAMERA_INDEX)
    parser.add_argument("--flip",        action="store_true", default=True)
    parser.add_argument("--debug",       action="store_true", default=False)
    parser.add_argument("--cooldown",    type=float, default=1.0)
    parser.add_argument("--sensitivity", type=float, default=1.0)
    return parser.parse_args()


# ──────────────────────────────────────────────
# MAIN APPLICATION CLASS
# ──────────────────────────────────────────────

class SignFlowApp:
    """
    Main application class.
    Owns the webcam, MediaPipe, gesture detector, controller, and UI.
    """

    def __init__(self, args):
        self.args   = args
        self.config = Config()

        # Apply CLI overrides
        self.config.CAMERA_INDEX       = args.cam
        self.config.FLIP_HORIZONTAL    = args.flip
        self.config.DEBUG              = args.debug
        self.config.COOLDOWN_MULTIPLIER = args.cooldown

        # Apply sensitivity to swipe thresholds (inverse: higher sensitivity = lower threshold)
        sens = max(0.1, args.sensitivity)
        self.config.SWIPE_DISPLACEMENT /= sens
        self.config.SWIPE_SPEED        /= sens

        # MediaPipe setup
        self.mp_hands   = mp.solutions.hands
        self.hands      = self.mp_hands.Hands(
            static_image_mode    = False,
            max_num_hands        = self.config.MAX_NUM_HANDS,
            min_detection_confidence = self.config.MIN_DETECTION_CONF,
            min_tracking_confidence  = self.config.MIN_TRACKING_CONF,
        )

        # Core components
        self.detector   = GestureDetector(
            pinch_threshold   = self.config.PINCH_THRESHOLD,
            swipe_displacement = self.config.SWIPE_DISPLACEMENT,
            swipe_speed       = self.config.SWIPE_SPEED,
        )
        self.controller = HandGestureController(
            cooldown_multiplier = self.config.COOLDOWN_MULTIPLIER
        )
        self.ui         = UIManager()

        # State
        self.annotation_points: list = []
        self.screen_w, self.screen_h = pyautogui.size()

        # Pointer smoother (frame-space for laser dot display)
        self._laser_frame_smoother = PositionSmoother(window_size=5)

        # FPS tracking
        self._frame_times: list = []
        self._fps: float        = 0.0

    # ── Run ─────────────────────────────────────

    def run(self):
        """Open webcam and run the main loop."""
        cap = cv2.VideoCapture(self.config.CAMERA_INDEX)
        if not cap.isOpened():
            print(f"[SignFlow] ❌  Could not open camera index {self.config.CAMERA_INDEX}")
            sys.exit(1)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, 60)

        print("[SignFlow] ✅  Camera opened. Press  Q  to quit,  C  to clear annotations.")
        print("[SignFlow] ℹ️   Gestures: Swipe(slides) · Palm(pause) · Pinch(laser) · 2Fingers(draw) · 👍(F5) · Fist(Esc)")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[SignFlow] ⚠️  Frame read failed.")
                    break

                frame = self._process_frame(frame)
                self._draw_fps(frame)

                cv2.imshow("SignFlow — Gesture Controller", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("[SignFlow] Quit.")
                    break
                elif key == ord("c"):
                    self.annotation_points.clear()
                    print("[SignFlow] Annotations cleared.")

        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.hands.close()

    # ── Per-frame logic ──────────────────────────

    def _process_frame(self, frame) -> np.ndarray:
        """Full processing pipeline for one webcam frame."""

        # 1. Pre-process
        if self.config.FLIP_HORIZONTAL:
            frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        # 2. MediaPipe inference (needs RGB)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        gesture_result = GestureResult()  # default empty result
        action_fired   = None

        if results.multi_hand_landmarks:
            # Take first hand only
            hand_landmarks = results.multi_hand_landmarks[0]
            hand_label     = "Right"  # assume; adjust if using multi-hand
            if results.multi_handedness:
                hand_label = results.multi_handedness[0].classification[0].label

            # 3. Detect gesture
            gesture_result = self.detector.detect(hand_landmarks, w, h, hand_label)

            # 4. Map index tip to screen for laser/pointer
            lms = hand_landmarks.landmark
            sx, sy = map_to_screen(
                lms[8].x, lms[8].y,
                w, h,
                self.screen_w, self.screen_h,
                margin=0.08,
                speed_multiplier=self.config.POINTER_SPEED,
            )
            # Smooth the frame-space laser dot position separately
            frame_lx = int(lms[8].x * w)
            frame_ly = int(lms[8].y * h)
            slx, sly = self._laser_frame_smoother.update(frame_lx, frame_ly)
            gesture_result.index_tip = (int(slx), int(sly))

            # 5. Handle controls
            action_fired = self.controller.handle(
                gesture_result.gesture,
                index_tip_screen=(sx, sy),
                annotation_points=self.annotation_points,
            )

            # 6. Debug output
            if self.config.DEBUG and gesture_result.gesture != "NONE":
                print(f"[gesture] {gesture_result.gesture:15s}  conf={gesture_result.confidence:.2f}  action={action_fired}")

        # 7. Cap annotation points to prevent unbounded growth
        if len(self.annotation_points) > self.config.MAX_ANNOTATION_POINTS:
            self.annotation_points = self.annotation_points[-self.config.MAX_ANNOTATION_POINTS:]

        # 8. Render UI
        self.ui.draw_frame(
            frame         = frame,
            gesture_result= gesture_result,
            is_laser      = self.controller.laser_mode,
            is_annotate   = self.controller.annotation_mode,
            annotation_points = self.annotation_points,
            confidence    = gesture_result.confidence,
            action_fired  = action_fired,
        )

        # 9. FPS update
        self._update_fps()
        return frame

    def _update_fps(self):
        now = time.time()
        self._frame_times.append(now)
        self._frame_times = [t for t in self._frame_times if now - t < 1.0]
        self._fps = len(self._frame_times)

    def _draw_fps(self, frame):
        h = frame.shape[0]
        cv2.putText(frame, f"{self._fps:.0f} fps", (12, h - 40),
                    cv2.FONT_HERSHEY_DUPLEX, 0.42, (100, 120, 130), 1, cv2.LINE_AA)


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    app  = SignFlowApp(args)
    app.run()
