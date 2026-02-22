"""
Minecraft Dynamic Click Assist & Sensitivity Damper
Author: Tohm Sachs
"""

import time
import threading
import random
import queue
import sys
import platform
import ctypes
from collections import deque
from typing import List, Tuple, Optional
from ctypes import wintypes

# 3rd Party Imports
try:
    from pynput import mouse
except ImportError:
    print("Error: 'pynput' not found. Please install via: pip install pynput")
    sys.exit(1)

# --- Configuration ---
DEFAULT_CONFIG = {
    # Clicks Per Second Limits
    "HARD_CPS_LIMIT": 18,
    "TARGET_CPS_RANGE": (15, 17),
    
    # Trigger Logic
    "TRIGGER_BUTTONS": [mouse.Button.left, mouse.Button.right],
    "DOUBLE_CLICK_THRESHOLD": 0.15,  # Time between clicks to trigger assist
    
    # Dynamic Sensitivity (Aim Assist)
    "CPS_SLOWDOWN_THRESHOLD": 10,    # CPS required to engage sensitivity damper
    "SENS_MULTIPLIER": 0.5,          # 0.5 = 50% sensitivity when active
    "SENS_RAMP_DOWN_MS": 40,         # Smoothness entering low sens
    "SENS_RAMP_UP_MS": 15,           # Speed of recovery to normal sens
    
    # Internal Logic
    "CPS_WINDOW_SECONDS": 0.3,       # Calculation window
    "STALE_TIMEOUT_MS": 100,         # Reset if no clicks for X ms
    "POLLING_RATE_HZ": 250
}

# --- Windows API Setup ---
if platform.system() != "Windows":
    print("Error: This script is compatible with Windows only.")
    sys.exit(1)

user32 = ctypes.windll.user32

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class SensitivityEngine:
    """
    Adjusts mouse cursor movement in real-time to simulate lower sensitivity
    during high-CPS scenarios (effectively recoil compensation).
    """
    def __init__(self, simulator):
        self.sim = simulator
        self.multiplier = simulator.config["SENS_MULTIPLIER"]
        
        # Calculate steps for asymmetric smoothing
        polling_ms = 1000 / simulator.config["POLLING_RATE_HZ"]
        self.step_down = 1.0 / (simulator.config["SENS_RAMP_DOWN_MS"] / polling_ms)
        self.step_up = 1.0 / (simulator.config["SENS_RAMP_UP_MS"] / polling_ms)
        
        self.current_weight = 1.0 
        self._running = False
        self.last_pos = POINT()
        user32.GetCursorPos(ctypes.byref(self.last_pos))

    def _move_relative(self, dx: int, dy: int):
        # 0x0001 is MOUSEEVENTF_MOVE
        user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)

    def stop(self):
        self._running = False

    def loop(self):
        self._running = True
        while self._running:
            now = time.perf_counter()
            current_cps = self.sim.get_total_cps()
            
            # 1. Logic Check: Is the click stream active and above threshold?
            time_since_last = (now - self.sim.last_click_time) * 1000
            is_over_limit = (current_cps >= self.sim.config["CPS_SLOWDOWN_THRESHOLD"] and 
                             time_since_last < self.sim.config["STALE_TIMEOUT_MS"])

            # 2. Asymmetric Ramping (Smooth transition)
            target_weight = self.multiplier if is_over_limit else 1.0
            
            if self.current_weight > target_weight:
                self.current_weight = max(target_weight, self.current_weight - self.step_down)
            elif self.current_weight < target_weight:
                self.current_weight = min(target_weight, self.current_weight + self.step_up)

            # 3. Apply Counter-Movement
            # We detect how much the mouse moved physically, and move it back 
            # proportionally to simulate lower sensitivity.
            if self.current_weight < 0.995:
                curr_pos = POINT()
                if user32.GetCursorPos(ctypes.byref(curr_pos)):
                    dx = curr_pos.x - self.last_pos.x
                    dy = curr_pos.y - self.last_pos.y
                    
                    if dx != 0 or dy != 0:
                        pull_back = self.current_weight - 1.0
                        rx, ry = dx * pull_back, dy * pull_back
                        
                        # Only apply correction if it registers as at least 1 pixel
                        if abs(rx) >= 1 or abs(ry) >= 1:
                            self._move_relative(rx, ry)
                            # Update last_pos to include our artificial movement
                            self.last_pos.x = curr_pos.x + int(rx)
                            self.last_pos.y = curr_pos.y + int(ry)
                        else:
                            self.last_pos = curr_pos
                    else:
                        self.last_pos = curr_pos
                else:
                    self.last_pos = curr_pos
            else:
                user32.GetCursorPos(ctypes.byref(self.last_pos))

            time.sleep(1.0 / self.sim.config["POLLING_RATE_HZ"])

class ClickSimulator:
    def __init__(self, config: Optional[dict] = None):
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
            
        self.mouse_controller = mouse.Controller()
        self._is_listening = False
        self._simulating = False
        self._work_queue = queue.Queue()
        self.total_click_history = deque()
        self.last_click_time = 0
        self.sens_engine = SensitivityEngine(self)
        self._listener = None

    def get_total_cps(self) -> float:
        now = time.perf_counter()
        # Clean old clicks based on the window
        while self.total_click_history and (now - self.total_click_history[0] > self.config["CPS_WINDOW_SECONDS"]):
            self.total_click_history.popleft()
        
        if not self.total_click_history: 
            return 0.0
            
        # Extrapolate window count to a 1-second CPS value
        return len(self.total_click_history) / self.config["CPS_WINDOW_SECONDS"]

    def register_click_event(self):
        self.last_click_time = time.perf_counter()
        self.total_click_history.append(self.last_click_time)

    def start(self):
        print(f"[-] Starting engine...")
        print(f"[-] Target CPS: {self.config['TARGET_CPS_RANGE']}")
        print(f"[-] Sensitivity Damping: Active > {self.config['CPS_SLOWDOWN_THRESHOLD']} CPS")
        
        self._is_listening = True
        
        # Start Threads
        threading.Thread(target=self.sens_engine.loop, daemon=True).start()
        threading.Thread(target=self._worker_loop, daemon=True).start()
        
        # Start Input Listener
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.start()
        print("[+] Ready. Press Ctrl+C to exit.")

    def stop(self):
        self._is_listening = False
        self.sens_engine.stop()
        if self._listener:
            self._listener.stop()

    def _on_click(self, x, y, button, pressed):
        if not pressed or button not in self.config["TRIGGER_BUTTONS"]: 
            return
            
        self.register_click_event()
        
        if self._simulating: 
            return

        # Trigger simulation on double-click (butterfly click detection)
        if len(self.total_click_history) > 1:
            prev_time = self.total_click_history[-2]
            if (time.perf_counter() - prev_time) <= self.config["DOUBLE_CLICK_THRESHOLD"]:
                if self._work_queue.empty():
                    self._work_queue.put((button, time.perf_counter()))

    def _worker_loop(self):
        while self._is_listening:
            try:
                button, _ = self._work_queue.get(timeout=0.05)
            except queue.Empty:
                continue
                
            self._simulating = True
            try:
                # Add random extra clicks (2 to 4) to boost CPS
                clicks_to_add = random.randint(2, 4)
                for _ in range(clicks_to_add):
                    if not self._is_listening: 
                        break
                        
                    # Calculate human-like delay
                    min_delay = 1.0 / self.config["TARGET_CPS_RANGE"][1]
                    max_delay = 1.0 / self.config["TARGET_CPS_RANGE"][0]
                    delay = random.uniform(min_delay, max_delay)
                    
                    time.sleep(max(0, delay - 0.015)) # Offset for processing time
                    
                    self.mouse_controller.press(button)
                    self.register_click_event()
                    time.sleep(random.uniform(0.01, 0.02)) # Hold time
                    self.mouse_controller.release(button)
            finally:
                self._simulating = False

if __name__ == "__main__":
    sim = ClickSimulator()
    try:
        sim.start()
        # Keep main thread alive
        while True: 
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopping...")
        sim.stop()
        print("[+] Exited cleanly.")