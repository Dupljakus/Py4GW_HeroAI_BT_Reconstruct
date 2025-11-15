"""follow_bt_v1 backup.

Snapshot `HeroAI/follow_bt.py` za verziju HeroAI_v1_follow_bt_foundation.

Koristi se BehaviorTree sa CanFollowNode + FollowNode i ThrottledTimer(333).
"""

from typing import Optional

import Py4GW
from Py4GWCoreLib import ThrottledTimer, GLOBAL_CACHE, Range

from HeroAI.bt import BehaviorTree, SequenceNode, ActionNode, ConditionNode, NodeStatus
from HeroAI.cache_data import CacheData
from HeroAI.globals import hero_formation
from Py4GWCoreLib import Utils, ActionQueueManager


FOLLOW_BT_TICK_MS = 333
FOLLOW_DEADZONE_DISTANCE = 120.0


class CanFollowNode(ConditionNode):
    def __init__(self, cached_data: CacheData):
        super().__init__("CanFollow")
        self.cached_data = cached_data

    def check(self) -> bool:
        if not GLOBAL_CACHE.Map.IsExplorable():
            return False
        if GLOBAL_CACHE.Map.IsInCinematic():
            return False

        player_id = GLOBAL_CACHE.Player.GetAgentID()

        if not GLOBAL_CACHE.Agent.IsAlive(player_id):
            return False

        try:
            leader_id = GLOBAL_CACHE.Party.GetPartyLeaderID()
            player_pos = GLOBAL_CACHE.Agent.GetXY(player_id)
            leader_pos = GLOBAL_CACHE.Agent.GetXY(leader_id)
            dist_leader = Utils.Distance(player_pos, leader_pos)
            if dist_leader > Range.SafeCompass.value:
                return False
        except Exception:
            return False

        if GLOBAL_CACHE.Agent.IsKnockedDown(player_id):
            return False

        if self.cached_data.combat_handler.InCastingRoutine() or GLOBAL_CACHE.Agent.IsCasting(player_id):
            return False

        return True


class FollowNode(ActionNode):
    def __init__(self, cached_data: CacheData):
        super().__init__("Follow")
        self.cached_data = cached_data

    def execute(self) -> NodeStatus:
        try:
            Py4GW.Console.Log("HeroAI", "[FollowBT] Tick FollowNode", Py4GW.Console.MessageType.Debug)
            if GLOBAL_CACHE.Player.GetAgentID() == GLOBAL_CACHE.Party.GetPartyLeaderID():
                return NodeStatus.SUCCESS

            if not self.cached_data.data.is_following_enabled:
                return NodeStatus.SUCCESS

            party_number = GLOBAL_CACHE.Party.GetOwnPartyNumber()

            follow_x = 0.0
            follow_y = 0.0
            follow_angle = -1.0

            all_player_struct = self.cached_data.HeroAI_vars.all_player_struct
            if all_player_struct[party_number].IsFlagged:
                follow_x = all_player_struct[party_number].FlagPosX
                follow_y = all_player_struct[party_number].FlagPosY
                follow_angle = all_player_struct[party_number].FollowAngle
            elif all_player_struct[0].IsFlagged:
                follow_x = all_player_struct[0].FlagPosX
                follow_y = all_player_struct[0].FlagPosY
                follow_angle = all_player_struct[0].FollowAngle
            else:
                follow_x, follow_y = GLOBAL_CACHE.Agent.GetXY(GLOBAL_CACHE.Party.GetPartyLeaderID())
                follow_angle = GLOBAL_CACHE.Agent.GetRotationAngle(GLOBAL_CACHE.Party.GetPartyLeaderID())

            hero_pos = GLOBAL_CACHE.Agent.GetXY(GLOBAL_CACHE.Player.GetAgentID())
            dist = Utils.Distance(hero_pos, (follow_x, follow_y))
            if dist <= FOLLOW_DEADZONE_DISTANCE:
                Py4GW.Console.Log("HeroAI", f"[FollowBT] In deadzone, skipping move (dist={dist:.1f})", Py4GW.Console.MessageType.Debug)
                return NodeStatus.SUCCESS

            hero_grid_pos = (
                party_number
                + GLOBAL_CACHE.Party.GetHeroCount()
                + GLOBAL_CACHE.Party.GetHenchmanCount()
            )
            angle_on_hero_grid = follow_angle + Utils.DegToRad(hero_formation[hero_grid_pos])

            import math

            xx = Range.Touch.value * math.cos(angle_on_hero_grid) + follow_x
            yy = Range.Touch.value * math.sin(angle_on_hero_grid) + follow_y

            Py4GW.Console.Log("HeroAI", f"[FollowBT] Move to ({xx:.1f}, {yy:.1f}) dist={dist:.1f}", Py4GW.Console.MessageType.Debug)

            ActionQueueManager().ResetQueue("ACTION")
            GLOBAL_CACHE.Player.Move(xx, yy)

            return NodeStatus.SUCCESS

        except Exception as e:
            Py4GW.Console.Log("HeroAI", f"[FollowBT][FollowNode] Error: {str(e)}", Py4GW.Console.MessageType.Error)
            return NodeStatus.FAILURE


_follow_bt: Optional[BehaviorTree] = None
_follow_rt: Optional[ThrottledTimer] = None


def should_tick_follow_bt() -> bool:
    global _follow_rt
    if _follow_rt is None:
        _follow_rt = ThrottledTimer(FOLLOW_BT_TICK_MS)
    if not _follow_rt.IsExpired():
        return False
    Py4GW.Console.Log("HeroAI", "[FollowBT] Throttle expired, ticking BT", Py4GW.Console.MessageType.Debug)
    _follow_rt.Reset()
    return True


def get_follow_bt(cached_data: CacheData) -> BehaviorTree:
    global _follow_bt
    if _follow_bt is None:
        Py4GW.Console.Log("HeroAI", "[FollowBT] Initializing BehaviorTree", Py4GW.Console.MessageType.Debug)
        _follow_bt = BehaviorTree(SequenceNode([CanFollowNode(cached_data), FollowNode(cached_data)]))
    return _follow_bt
