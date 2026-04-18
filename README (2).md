# SignFlow

> **Real-time gesture-based presentation & productivity controller**  
> Control slides, media, and your screen — entirely hands-free.

---

## Overview

SignFlow uses your webcam and MediaPipe hand tracking to detect intentional hand gestures and translate them into keyboard shortcuts and mouse actions. No hardware. No wearables. Just your hand in front of a camera.

Built for:
- **PowerPoint / Keynote / LibreOffice Impress** — flip slides hands-free
- **PDF viewers** — navigate pages with a swipe
- **Video players** — play/pause with an open palm
- **Live demos** — use a virtual laser pointer and draw annotations

---

## Screenshots

```
┌─────────────────────────────────────────────────────────────┐
│ GESTURE                                   MODE              │
│ NEXT SLIDE  →                             READY             │
│ ▓▓▓▓▓▓▓▓▓▒▒▒  conf                                          │
│                                                             │
│          [hand skeleton + motion trail]                     │
│                 ●  (laser dot)                              │
│                                                             │
│ Swipe R/L:Next/Prev │ Palm:Play │ Pinch:Laser │ 2F:Draw … │
└─────────────────────────────────────────────────────────────┘
```

---

## Gesture Controls

| Gesture         | Action              | Key Sent   |
|-----------------|---------------------|------------|
| Swipe Right     | Next slide          | `→`        |
| Swipe Left      | Previous slide      | `←`        |
| Open Palm       | Play / Pause        | `Space`    |
| Pinch           | Laser pointer mode  | Mouse move |
| Two Fingers     | Draw annotation     | —          |
| Thumbs Up 👍    | Start slideshow     | `F5`       |
| Closed Fist ✊  | Exit / Stop         | `Esc`      |

---

## Installation

### 1. Clone / download

```bash
git clone https://github.com/your-username/signflow.git
cd signflow
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **macOS note:** PyAutoGUI requires screen recording permissions.  
> Go to **System Settings → Privacy & Security → Screen Recording** and enable your terminal.

> **Linux note:** Install `python3-xlib` for PyAutoGUI:  
> `sudo apt install python3-xlib`

---

## Usage

```bash
# Basic launch
python main.py

# Use a different camera
python main.py --cam 1

# Print gesture debug info to console
python main.py --debug

# Make gestures more responsive (lower cooldowns)
python main.py --cooldown 0.7

# Increase swipe sensitivity
python main.py --sensitivity 1.5
```

### In-app keyboard shortcuts

| Key | Action                  |
|-----|-------------------------|
| `Q` | Quit SignFlow           |
| `C` | Clear annotations       |

---

## Project Structure

```
SignFlow/
│
├── main.py             # Webcam loop, frame processing, app orchestration
├── gesture_detector.py # Gesture classification (finger states, swipe, pinch)
├── controls.py         # System actions via PyAutoGUI + debounce manager
├── ui_overlay.py       # All visual rendering (panels, laser, trail, flash)
├── utils.py            # Smoothing, distance helpers, coordinate mapping
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## Tuning & Sensitivity

All key thresholds live in `main.py → Config` and `gesture_detector.py → GestureDetector`:

| Setting                  | Default | Effect                                  |
|--------------------------|---------|----------------------------------------|
| `PINCH_THRESHOLD`        | `0.06`  | Smaller = harder to trigger pinch      |
| `SWIPE_DISPLACEMENT`     | `0.12`  | Larger = bigger movement required      |
| `SWIPE_SPEED`            | `0.28`  | Larger = faster swipe required         |
| `COOLDOWN_MULTIPLIER`    | `1.0`   | Lower = gestures fire more frequently  |
| `POINTER_SPEED`          | `1.2`   | Higher = faster laser pointer          |
| `MIN_DETECTION_CONF`     | `0.72`  | Lower = detects hand in worse lighting |

---

## Tips for Best Results

- **Lighting:** Face a window or lamp. Avoid backlit environments.
- **Distance:** Keep your hand 40–80 cm from the camera.
- **Background:** A plain, non-skin-coloured background helps MediaPipe.
- **Swipes:** Use your whole forearm — swipes should feel deliberate, not twitchy.
- **Annotations:** Hold "Two Fingers" steady; the trail follows your index tip.

---

## Requirements

- Python 3.10+
- Webcam
- OS: Windows 10+, macOS 12+, Ubuntu 20.04+

---

## Future Improvements

- [ ] Two-hand support (e.g. zoom in/out with both hands)
- [ ] Voice mode toggle overlay
- [ ] Config file (YAML) for persistent settings
- [ ] Virtual whiteboard export (save annotations as PNG)
- [ ] Gesture training mode to customise actions
- [ ] GUI settings panel (Tkinter or PyQt)
- [ ] OBS / screen capture integration

---

## Tech Stack

| Library       | Role                              |
|---------------|-----------------------------------|
| OpenCV        | Webcam capture & frame rendering  |
| MediaPipe     | Real-time hand landmark detection |
| PyAutoGUI     | Keyboard & mouse control          |
| NumPy         | Numerical operations              |

---

## License

MIT — free to use, modify, and distribute.

---

*Made with 🖐️ and Python.*
