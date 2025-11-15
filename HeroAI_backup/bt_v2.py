"""bt_v2.py

Backup snapshot (v2) of `HeroAI/bt.py` (behavior tree framework).

This version defines:
- `NodeStatus` enum (SUCCESS, FAILURE, RUNNING)
- `BTNode`, `ConditionNode`, `ActionNode`
- Composite nodes: `SequenceNode`, `SelectorNode`
- `BehaviorTree` wrapper with `tick()`

This file should mirror the `HeroAI/bt.py` at the time of creating v2.
"""

from HeroAI.bt import *  # noqa: F401,F403 - snapshot import for backup reference only
