# VS Code Auto Button Clicker

A small Python GUI tool that automatically detects and clicks "Allow" and "Continue" buttons in VS Code using image recognition.

## Features

- Scans the screen for button images (Allow, Continue) in priority order
- Configurable confidence threshold, scan interval, and click delay
- Simple Tkinter GUI with Test Find, Start Tracking, and Stop controls
- PyAutoGUI failsafe: move mouse to top-left corner to abort

## Requirements

- Python 3.8+
- `pyautogui`
- `opencv-python` (optional, enables confidence-based matching)

## Usage

```bash
pip install pyautogui opencv-python
python vscode_continue_clicker.py
```

Place `allow_button.png` and `continue_button.png` (screenshots of the buttons) in the same directory as the script.
