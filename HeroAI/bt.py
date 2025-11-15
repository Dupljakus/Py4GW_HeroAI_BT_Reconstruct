from enum import Enum
from typing import List


class NodeStatus(Enum):
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3


class BTNode:
    def tick(self) -> "NodeStatus":
        return self.execute()

    def execute(self) -> "NodeStatus":  # pragma: no cover - interface
        raise NotImplementedError


class ConditionNode(BTNode):
    """Base class for simple condition checks."""

    def __init__(self, name: str = ""):
        self.name = name

    def check(self) -> bool:  # pragma: no cover - interface
        """Override in subclasses to implement the condition logic.

        Should return True when the condition is satisfied, False otherwise.
        """
        raise NotImplementedError

    def execute(self) -> "NodeStatus":
        """Default execution for conditions: map bool -> SUCCESS/FAILURE."""
        return NodeStatus.SUCCESS if self.check() else NodeStatus.FAILURE


class ActionNode(BTNode):
    """Base class for actions (movement, casting, etc.)."""

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
    """Runs children until one succeeds (prioritized OR)."""

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
