import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

import pyautogui

# Check if opencv is available for confidence matching
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# ---------- Config ----------
# Button images in priority order (highest priority first)
BUTTON_CONFIGS = [
    {
        'name': 'Allow',
        'image': Path(__file__).with_name('allow_button.png'),
        'priority': 1,
    },
    {
        'name': 'Continue',
        'image': Path(__file__).with_name('continue_button.png'),
        'priority': 2,
    },
    {
        'name': 'Allow In This Session',
        'image': Path(__file__).with_name('allow_in_this_session_button.png'),
        'priority': 2,
    },
]
CONFIDENCE = 0.85 if OPENCV_AVAILABLE else None  # requires opencv-python
MONITOR_INTERVAL = 0.4 # seconds between scans when monitoring
CLICK_DELAY = 1.0      # click 1 second after button is found

pyautogui.FAILSAFE = True   # move mouse to top-left corner to abort a PyAutoGUI action
pyautogui.PAUSE = 0.05


class ContinueClickerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('VS Code Auto Button Clicker')
        self.root.geometry('460x280')
        self.root.resizable(False, False)

        self.monitoring = False
        self.monitor_thread = None

        self.status_var = tk.StringVar(value='Idle')
        self.last_found_var = tk.StringVar(value='Last found: not yet')

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill='both', expand=True)

        title = ttk.Label(frame, text='VS Code Auto Button Clicker', font=('Segoe UI', 13, 'bold'))
        title.pack(anchor='w', pady=(0, 8))

        desc = ttk.Label(
            frame,
            text=(
                'Test Find: locate the highest priority button and move the mouse there.\n'
                'Start Tracking: scan for buttons and click by priority (Allow > Continue).'
            ),
            justify='left'
        )
        desc.pack(anchor='w', pady=(0, 12))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill='x', pady=(0, 12))

        self.test_btn = ttk.Button(btn_row, text='Test Find Button', command=self.test_find)
        self.test_btn.pack(side='left')

        self.start_btn = ttk.Button(btn_row, text='Start Tracking', command=self.start_tracking)
        self.start_btn.pack(side='left', padx=8)

        self.stop_btn = ttk.Button(btn_row, text='Stop', command=self.stop_tracking)
        self.stop_btn.pack(side='left')

        self.status_label = ttk.Label(frame, textvariable=self.status_var, font=('Segoe UI', 10, 'bold'))
        self.status_label.pack(anchor='w', pady=(4, 6))

        self.last_found_label = ttk.Label(frame, textvariable=self.last_found_var)
        self.last_found_label.pack(anchor='w')

        opencv_status = '✓ OpenCV available' if OPENCV_AVAILABLE else '✗ OpenCV not installed (exact match only)'
        conf_text = f'Confidence: {CONFIDENCE}' if CONFIDENCE else 'Confidence: exact match'
        
        button_list = '\n'.join([
            f'  {i+1}. {cfg["name"]} button ({cfg["image"].name})' 
            for i, cfg in enumerate(BUTTON_CONFIGS)
        ])
        
        note = ttk.Label(
            frame,
            text=(
                f'Button priority order:\n{button_list}\n'
                f'{conf_text} | Scan interval: {MONITOR_INTERVAL}s | Click delay: {CLICK_DELAY}s\n'
                f'{opencv_status}\n'
                'Tip: Move mouse to the top-left corner to trigger PyAutoGUI failsafe.'
            ),
            justify='left'
        )
        note.pack(anchor='w', pady=(14, 0))

    def set_status(self, text: str):
        self.root.after(0, self.status_var.set, text)

    def set_last_found(self, text: str):
        self.root.after(0, self.last_found_var.set, text)

    def locate_button(self, button_config):
        """Locate a button on screen by its configuration."""
        button_image = button_config['image']
        if not button_image.exists():
            raise FileNotFoundError(f'Button image not found: {button_image}')

        try:
            if CONFIDENCE is not None:
                return pyautogui.locateOnScreen(str(button_image), confidence=CONFIDENCE)
            else:
                return pyautogui.locateOnScreen(str(button_image))
        except pyautogui.ImageNotFoundException:
            # When using confidence matching, pyautogui raises exception instead of returning None
            return None
    
    def find_highest_priority_button(self):
        """Scan for buttons in priority order and return the first one found."""
        for button_config in BUTTON_CONFIGS:
            box = self.locate_button(button_config)
            if box:
                return button_config, box
        return None, None

    def test_find(self):
        self.set_status('Testing: locating buttons...')
        self.root.update_idletasks()

        try:
            button_config, box = self.find_highest_priority_button()
            if not box:
                self.set_status('Test result: No buttons found')
                messagebox.showinfo('Not found', 'No buttons were found on screen.')
                return

            center = pyautogui.center(box)
            pyautogui.moveTo(center.x, center.y, duration=0.15)
            button_name = button_config['name']
            self.set_last_found(f'Last found: {button_name} at x={center.x}, y={center.y}')
            self.set_status(f'Test result: mouse moved to {button_name} button')
        except Exception as e:
            self.set_status(f'Error during test: {e}')
            messagebox.showerror('Error', str(e))

    def start_tracking(self):
        if self.monitoring:
            self.set_status('Already tracking')
            return

        self.monitoring = True
        self.set_status('Tracking started')
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_tracking(self):
        self.monitoring = False
        self.set_status('Tracking stopped')

    def _monitor_loop(self):
        while self.monitoring:
            try:
                button_config, box = self.find_highest_priority_button()
                if box:
                    button_name = button_config['name']
                    center = pyautogui.center(box)
                    self.set_last_found(f'Last found: {button_name} at x={center.x}, y={center.y}')
                    self.set_status(f'{button_name} button found, waiting {CLICK_DELAY}s before click...')

                    time.sleep(CLICK_DELAY)
                    if not self.monitoring:
                        break

                    # Re-locate before clicking in case UI shifted slightly.
                    box_again = self.locate_button(button_config)
                    if box_again:
                        center_again = pyautogui.center(box_again)
                        pyautogui.click(center_again.x, center_again.y)
                        self.set_last_found(f'Last found: {button_name} at x={center_again.x}, y={center_again.y}')
                        self.set_status(f'Clicked {button_name} button')
                        time.sleep(1.0)  # Wait after click, then re-scan for next priority button
                    else:
                        self.set_status('Button disappeared before click')
                else:
                    self.set_status('Tracking... no buttons found yet')
                    time.sleep(MONITOR_INTERVAL)
            except Exception as e:
                import traceback
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else '(no error message)'
                full_error = f'{error_type}: {error_msg}'
                
                self.set_status(f'Monitoring error: {full_error}')
                print(f'ERROR: {full_error}')
                print(traceback.format_exc())  # Print full traceback to console
                
                self.root.after(0, messagebox.showerror, 'Monitoring Error', 
                               f'{error_type}: {error_msg}\n\nCheck console for details.')
                self.monitoring = False
                break

    def on_close(self):
        self.monitoring = False
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = ContinueClickerApp(root)
    root.protocol('WM_DELETE_WINDOW', app.on_close)
    root.mainloop()
