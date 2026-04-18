# AirDeck

> Control anything on your screen with just your hand — no clickers, no remotes, nothing extra.

---

## Overview

AirDeck uses your webcam and MediaPipe hand tracking to detect hand gestures and translate them into keyboard shortcuts and mouse actions in real time. Works with anything that responds to keyboard input — presentations, videos, PDFs, music, you name it.

Built for:
- **YouTube / VLC / any video player** — play, pause, and seek with gestures
- **PowerPoint / Keynote / LibreOffice Impress** — flip slides hands-free
- **PDF viewers** — navigate pages with a swipe
- **Spotify / music players** — skip tracks, play/pause
- **Live demos & teaching** — use a virtual laser pointer and draw annotations on screen

---

## Screenshots

```
┌─────────────────────────────────────────────────────────────┐
│ GESTURE                                   MODE              │
│ NEXT  →                                   READY             │
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

| Gesture         | Action                        | Key Sent   |
|-----------------|-------------------------------|------------|
| Swipe Right     | Next slide / Skip forward     | `→`        |
| Swipe Left      | Previous slide / Skip back    | `←`        |
| Open Palm       | Play / Pause                  | `Space`    |
| Pinch           | Laser pointer mode            | Mouse move |
| Two Fingers     | Draw annotation on screen     | —          |
| Thumbs Up 👍    | Start slideshow / Fullscreen  | `F5`       |
| Closed Fist ✊  | Exit / Stop / Close           | `Esc`      |

### Real-world examples

| What you're doing          | Swipe Right      | Open Palm    | Swipe Left       |
|----------------------------|------------------|--------------|------------------|
| YouTube / Netflix          | Seek forward     | Play / Pause | Seek back        |
| PowerPoint / Google Slides | Next slide       | —            | Previous slide   |
| PDF (Acrobat, browser)     | Next page        | —            | Previous page    |
| Spotify / Music            | Next track       | Play / Pause | Previous track   |
| Image gallery              | Next image       | —            | Previous image   |

---

## Installation

### 1. Clone / download

```bash
git clone https://github.com/Adithyaa04/AirDeck.git
cd AirDeck
```

### 2. Create a virtual environment with Python 3.11

```bash
# Windows
py -3.11 -m venv venv
venv\Scripts\activate

# macOS / Linux
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **macOS note:** PyAutoGUI requires screen recording permissions.  
> Go to **System Settings → Privacy & Security → Screen Recording** and enable your terminal.

> **Linux note:** Install `python3-xlib` for PyAutoGUI:  
> `sudo apt install python3-xlib`

> **Windows note:** Use Python 3.11. MediaPipe has compatibility issues with Python 3.12.

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

### How to use with YouTube
1. Open YouTube in your browser and start a video
2. Click on the video so it has focus
3. Run AirDeck in a separate window
4. Swipe right/left to seek, open palm to play/pause

### How to use with PowerPoint
1. Open your presentation and press F5 to start (or use the Thumbs Up gesture)
2. AirDeck's swipe gestures will flip slides
3. Use Pinch to activate the laser pointer during your talk

### In-app keyboard shortcuts

| Key | Action                   |
|-----|--------------------------|
| `Q` | Quit AirDeck             |
| `C` | Clear annotations        |

---

## Project Structure

```
AirDeck/
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

| Setting               | Default | Effect                                   |
|-----------------------|---------|------------------------------------------|
| `PINCH_THRESHOLD`     | `0.06`  | Smaller = harder to trigger pinch        |
| `SWIPE_DISPLACEMENT`  | `0.20`  | Larger = bigger movement required        |
| `SWIPE_SPEED`         | `0.45`  | Larger = faster swipe required           |
| `COOLDOWN_MULTIPLIER` | `1.0`   | Lower = gestures fire more frequently    |
| `POINTER_SPEED`       | `1.2`   | Higher = faster laser pointer            |
| `MIN_DETECTION_CONF`  | `0.72`  | Lower = detects hand in worse lighting   |

---

## Tips for Best Results

- **Lighting:** Face a window or lamp. Avoid backlit environments.
- **Distance:** Keep your hand 40–80 cm from the camera.
- **Background:** A plain, non-skin-coloured background helps MediaPipe.
- **Swipes:** Move your whole hand deliberately — like swiping a large touchscreen.
- **Play/Pause:** Hold your open palm still for half a second — don't swipe it.
- **Annotations:** Hold "Two Fingers" steady; the trail follows your index tip.
- **Focus:** Make sure the app you want to control is in focus before gesturing.

---

## Requirements

- Python 3.11
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
- [ ] Browser extension for tighter YouTube/Netflix integration

---

## Tech Stack

| Library    | Role                              |
|------------|-----------------------------------|
| OpenCV     | Webcam capture & frame rendering  |
| MediaPipe  | Real-time hand landmark detection |
| PyAutoGUI  | Keyboard & mouse control          |
| NumPy      | Numerical operations              |

---

## License

MIT — free to use, modify, and distribute.

---

*Made with 🖐️ and Python.*
