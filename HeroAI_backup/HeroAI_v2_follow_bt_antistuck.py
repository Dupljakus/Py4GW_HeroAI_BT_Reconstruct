"""HeroAI_v2_follow_bt_antistuck.py

Backup snapshot (v2) of `Widgets/HeroAI.py` at the time when:
- Follow logic is driven by Behavior Tree (`HeroAI/bt.py`, `HeroAI/follow_bt.py`).
- Follow BT is throttled to ~3 ticks per second via `ThrottledTimer(333)`.
- `CanFollowNode` encapsulates pre-conditions (outpost off, leader validity, KD/casting checks).
- `FollowNode` includes deadzone around follow target and anti-stuck probing logic.

This file is a direct copy of `Widgets/HeroAI.py` corresponding to the v2 follow BT + anti-stuck implementation.
"""

from Widgets.HeroAI import *  # noqa: F401,F403 - snapshot import for backup reference only

