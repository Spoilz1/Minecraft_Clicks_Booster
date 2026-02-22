# ClickBooster: Minecraft Dynamic Click Assist and Sensitivity Damper

Have you ever felt like people are clicking a little too fast? Too fast that it doesn't match what it sounds like? Well, now you can too, getting upwards of 25 cps with butterfly clicking that would have otherwise given you 10.

ClickBooster is a specialized utility designed to enhance clicking performance in Minecraft while providing a sensitivity damper to maintain aim stability during high-CPS bursts.

## Files Included

1. ClickAssist.exe: A standalone Windows executable for immediate use.
2. ClickBooster.py: The Python source code for transparency and manual execution.

## Features

- Dynamic Click Injection: Detects butterfly clicking patterns and adds human-like clicks to reach target CPS ranges.
- Sensitivity Damper: Automatically lowers mouse sensitivity when CPS exceeds a specific threshold to act as recoil compensation.
- Randomized Latency: Uses varying delays and hold times to simulate natural human clicking behavior.
- Asymmetric Ramping: Smoothly transitions into and out of the lowered sensitivity state.

## How to Run

### Option 1: Executable
Simply run "ClickAssist.exe". A console window will open to show the program status.

### Option 2: Python Script
If you are uncomfortable running downloaded exe files, you can just run 'python ClickBooster.py' for the same program.

Requirements:
- Windows OS
- Python 3.x
- pynput library (install via: pip install pynput)

## Configuration

Custom settings can be modified within the "DEFAULT_CONFIG" section of the ClickBooster.py file:

- HARD_CPS_LIMIT: The maximum allowed clicks per second.
- TARGET_CPS_RANGE: The desired CPS window (e.g., 15 to 17).
- SENS_MULTIPLIER: The sensitivity reduction factor (0.5 equals 50% sensitivity).
- TRIGGER_BUTTONS: Defines which mouse buttons trigger the assist.

## Disclaimer

This tool is intended for educational and single-player use. Using click macros or sensitivity modifiers on competitive multiplayer servers may result in account bans. Use responsibly and at your own risk.

Author: Tohm Sachs
