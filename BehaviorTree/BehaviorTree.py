# =============================================================
#   BehaviorTree.py — CLEAN TREE STRUCTURE + TIMING
#   Safe for BT viewer, no GW logic yet.
# =============================================================

from __future__ import annotations

import time
from enum import IntEnum
from typing import List, Optional


# =============================================================
#   Node State
# =============================================================

class NodeState(IntEnum):
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3


# =============================================================
#   Base Node
# =============================================================

class Node:
    def __init__(self, name: str = "Node") -> None:
        self.name: str = name
        self.last_state: Optional[NodeState] = None
        self.last_duration_ms: float = 0.0
        self.accumulated_ms: float = 0.0
        self.node_type: str = self.__class__.__name__

    def tick(self) -> NodeState:
        raise NotImplementedError("tick() must be implemented by subclasses")

    def _finish_tick(self, state: NodeState, start_time: float) -> NodeState:
        """Common timing/profiling logic for all nodes."""
        self.last_state = state
        end = time.perf_counter()
        self.last_duration_ms = (end - start_time) * 1000.0
        self.accumulated_ms += self.last_duration_ms
        return state


# =============================================================
#   Composite Nodes
# =============================================================

class Sequence(Node):
    def __init__(self, name: str, children: Optional[List[Node]] = None) -> None:
        super().__init__(name)
        self.children: List[Node] = children or []
        self.index: int = 0

    def tick(self) -> NodeState:
        start = time.perf_counter()
        while self.index < len(self.children):
            child = self.children[self.index]
            state = child.tick()

            if state == NodeState.RUNNING:
                return self._finish_tick(NodeState.RUNNING, start)

            if state == NodeState.FAILURE:
                self.index = 0
                return self._finish_tick(NodeState.FAILURE, start)

            # SUCCESS → next child
            self.index += 1

        # Finished sequence
        self.index = 0
        return self._finish_tick(NodeState.SUCCESS, start)


class Selector(Node):
    def __init__(self, name: str, children: Optional[List[Node]] = None) -> None:
        super().__init__(name)
        self.children: List[Node] = children or []

    def tick(self) -> NodeState:
        start = time.perf_counter()
        for child in self.children:
            state = child.tick()

            if state == NodeState.RUNNING:
                return self._finish_tick(NodeState.RUNNING, start)

            if state == NodeState.SUCCESS:
                return self._finish_tick(NodeState.SUCCESS, start)

        return self._finish_tick(NodeState.FAILURE, start)


# =============================================================
#   Leaf Nodes (abstract)
# =============================================================

class Condition(Node):
    def __init__(self, name: str = "Condition") -> None:
        super().__init__(name)

    def condition(self) -> bool:
        """Override in subclasses."""
        raise NotImplementedError

    def tick(self) -> NodeState:
        start = time.perf_counter()
        result = self.condition()
        state = NodeState.SUCCESS if result else NodeState.FAILURE
        return self._finish_tick(state, start)


class Action(Node):
    def __init__(self, name: str = "Action") -> None:
        super().__init__(name)

    def action(self) -> NodeState:
        """Override in subclasses. Must return NodeState."""
        raise NotImplementedError

    def tick(self) -> NodeState:
        start = time.perf_counter()
        state = self.action()
        if not isinstance(state, NodeState):
            # safety fallback
            state = NodeState.FAILURE
        return self._finish_tick(state, start)


# =============================================================
#   Dummy Leaf Nodes (used for now in the tree)
#   They keep BT working without GW logic.
#   node_type is set so the viewer shows [Condition]/[Action].
# =============================================================

class DummyCondition(Condition):
    def __init__(self, name: str, default_result: bool = True) -> None:
        super().__init__(name)
        self.default_result = default_result
        self.node_type = "Condition"

    def condition(self) -> bool:
        return self.default_result


class DummyAction(Action):
    def __init__(self, name: str, default_state: NodeState = NodeState.SUCCESS) -> None:
        super().__init__(name)
        self.default_state = default_state
        self.node_type = "Action"

    def action(self) -> NodeState:
        return self.default_state


# =============================================================
#   BUILD TREE STRUCTURE (EMPTY LOGIC, BUT TIMED)
# =============================================================

def BuildBehaviorTree() -> Node:
    # ----- HandleLoading -----
    handle_loading = Sequence("HandleLoading", [
        DummyCondition("IsLoadingScreen", default_result=True),
        DummyAction("WaitLoading", default_state=NodeState.RUNNING),
    ])

    # ----- HandleMapNotReady -----
    handle_map_not_ready = Sequence("HandleMapNotReady", [
        DummyCondition("MapNotReady", default_result=False),
        DummyAction("WaitMapReady", default_state=NodeState.RUNNING),
    ])

    # ----- Leader Combat -----
    leader_combat = Sequence("LeaderCombat", [
        DummyCondition("DetectEnemiesInRange", default_result=False),
        DummyAction("SelectBestTarget"),
        DummyAction("MoveIntoCombatPosition"),
        DummyAction("UseSkills"),
        DummyAction("AttackTarget"),
    ])

    # ----- Leader Loot -----
    leader_loot = Sequence("LeaderLoot", [
        DummyCondition("DetectLootNearby", default_result=False),
        DummyAction("MoveAndPickup"),
    ])

    # ----- Leader Movement -----
    leader_movement = Sequence("LeaderMovement", [
        DummyCondition("HasMovementCommand", default_result=False),
        DummyAction("MoveToCommandPoint"),
    ])

    leader_branch = Selector("LeaderBranch", [
        leader_combat,
        leader_loot,
        leader_movement,
    ])

    # ----- Follower Emergency Combat -----
    follower_emergency_combat = Sequence("FollowerEmergencyCombat", [
        DummyCondition("EnemyThreatDetected", default_result=False),
        DummyAction("DefendSelf"),
        DummyAction("UseQuickSkill"),
    ])

    # ----- Follower Formation -----
    follower_formation = Sequence("FollowerFormation", [
        DummyAction("GetLeaderPosition"),
        DummyAction("ComputeFormationOffset"),
        DummyAction("MoveToOffset"),
    ])

    # ----- Follower Recovery -----
    follower_recovery = Sequence("FollowerRecovery", [
        DummyCondition("IsTooFarFromLeader", default_result=False),
        DummyAction("SprintToLeader"),
    ])

    follower_branch = Selector("FollowerBranch", [
        follower_emergency_combat,
        follower_formation,
        follower_recovery,
    ])

    # ----- ROOT -----
    root = Selector("ROOT", [
        handle_loading,
        handle_map_not_ready,
        leader_branch,
        follower_branch,
    ])

    return root


# =============================================================
#   GLOBAL ROOT + Wrapper (used by BTStandalone)
# =============================================================

BT_ROOT: Node = BuildBehaviorTree()


class BehaviorTree:
    def __init__(self) -> None:
        self.root: Node = BT_ROOT

    def tick(self) -> NodeState:
        if self.root:
            return self.root.tick()
        return NodeState.FAILURE


__all__ = [
    "BehaviorTree",
    "BT_ROOT",
    "Node",
    "Sequence",
    "Selector",
    "Condition",
    "Action",
    "DummyCondition",
    "DummyAction",
    "NodeState",
]
