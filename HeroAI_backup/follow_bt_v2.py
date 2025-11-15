"""follow_bt_v2.py

Backup snapshot (v2) of `HeroAI/follow_bt.py` when:
- `CanFollowNode` handles outpost, leader validity, KD/casting, and distance checks.
- `FollowNode` selects follow target (own flag, leader flag, leader) and uses formation offsets.
- Deadzone logic prevents micro-movements near the follow position.
- Anti-stuck logic tracks lack of progress and probes escape positions around the target.

This file should be a copy of the current `HeroAI/follow_bt.py` at the time of creating v2.
"""

from HeroAI.follow_bt import *  # noqa: F401,F403 - snapshot import for backup reference only
