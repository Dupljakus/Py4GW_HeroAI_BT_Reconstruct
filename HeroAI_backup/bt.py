"""bt_v1 backup.

Snapshot `HeroAI/bt.py` (BT framework) za HeroAI_v1_follow_bt_foundation.
"""

from enum import Enum
from typing import List


class NodeStatus(Enum):
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3


class BTNode:
    def tick(self) -> "NodeStatus":
        return self.execute()

    def execute(self) -> "NodeStatus":
        raise NotImplementedError


class ConditionNode(BTNode):
    def __init__(self, name: str = ""):
        self.name = name

    def check(self) -> bool:
        raise NotImplementedError

    def execute(self) -> "NodeStatus":
        return NodeStatus.SUCCESS if self.check() else NodeStatus.FAILURE


class ActionNode(BTNode):
    def __init__(self, name: str = ""):
        self.name = name


class SequenceNode(BTNode):
    def __init__(self, children: List[BTNode]):
        self.children = children

    def execute(self) -> "NodeStatus":
        for child in self.children:
            status = child.tick()
            if status != NodeStatus.SUCCESS:
                return status
        return NodeStatus.SUCCESS


class SelectorNode(BTNode):
    def __init__(self, children: List[BTNode]):
        self.children = children

    def execute(self) -> "NodeStatus":
        for child in self.children:
            status = child.tick()
            if status == NodeStatus.SUCCESS:
                return NodeStatus.SUCCESS
        return NodeStatus.FAILURE


class BehaviorTree:
    def __init__(self, root: BTNode):
        self.root = root

    def tick(self) -> "NodeStatus":
        return self.root.tick()
