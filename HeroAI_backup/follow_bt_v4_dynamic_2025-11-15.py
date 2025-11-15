from typing import Optional

import Py4GW
from Py4GWCoreLib import ThrottledTimer, GLOBAL_CACHE, Range

from HeroAI.bt import BehaviorTree, SequenceNode, ActionNode, ConditionNode, NodeStatus
from HeroAI.cache_data import CacheData
from HeroAI.globals import (
	hero_formation,
	formation_melee_leader_melee,
	formation_melee_leader_ranged,
	formation_ranged_leader_melee,
	formation_ranged_leader_ranged,
	formation_spear_leader_melee,
	formation_spear_leader_ranged,
)
from Py4GWCoreLib import Utils, ActionQueueManager


FOLLOW_BT_TICK_MS = 333
FOLLOW_DEADZONE_DISTANCE = 60.0
STUCK_TICK_THRESHOLD = 45
MIN_PROGRESS_DISTANCE = 40.0
ESCAPE_PROBE_ANGLES_DEG = (-60.0, 60.0, -135.0, 135.0)


class CanFollowNode(ConditionNode):
	def __init__(self, cached_data: CacheData):
		super().__init__("CanFollow")
		self.cached_data = cached_data

	def check(self) -> bool:
		if GLOBAL_CACHE.Map.IsOutpost():
			return False
		if not GLOBAL_CACHE.Map.IsExplorable() or GLOBAL_CACHE.Map.IsInCinematic():
			return False

		player_id = GLOBAL_CACHE.Player.GetAgentID()
		if not GLOBAL_CACHE.Agent.IsAlive(player_id):
			return False

		try:
			leader_id = GLOBAL_CACHE.Party.GetPartyLeaderID()
			if leader_id == 0 or not GLOBAL_CACHE.Agent.IsAlive(leader_id):
				return False
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
		self._last_dist: float = 0.0
		self._no_progress_ticks: int = 0
		self._in_escape_mode: bool = False
		self._follower_count: int = 0

	def _get_leader_type(self) -> str:
		leader_id = GLOBAL_CACHE.Party.GetPartyLeaderID()
		if leader_id == 0:
			return "ranged"
		if GLOBAL_CACHE.Agent.IsMelee(leader_id):
			return "melee"
		return "ranged"

	def _is_melee_hero(self) -> bool:
		return GLOBAL_CACHE.Agent.IsMelee(GLOBAL_CACHE.Player.GetAgentID())

	def _get_relative_slot(self) -> int:
		leader_id = GLOBAL_CACHE.Party.GetPartyLeaderID()
		player_id = GLOBAL_CACHE.Player.GetAgentID()

		all_player_struct = self.cached_data.HeroAI_vars.all_player_struct
		follower_index = 0
		follower_count = 0

		for i in range(len(all_player_struct)):
			player_struct = all_player_struct[i]
			if not player_struct.IsActive:
				continue
			if player_struct.PlayerID == leader_id or player_struct.PlayerID == 0:
				continue

			if player_struct.PlayerID == player_id:
				hero_slot = follower_index
			follower_index += 1
			follower_count += 1

		self._follower_count = follower_count

		try:
			return hero_slot  # type: ignore[name-defined]
		except NameError:
			return 0

	def _get_angle_for_slot(self) -> float:
		leader_type = self._get_leader_type()
		is_melee_hero = self._is_melee_hero()

		hero_index = self._get_relative_slot()
		follower_count = max(self._follower_count, 1)

		if leader_type == "melee":
			formation = formation_melee_leader_melee if is_melee_hero else formation_melee_leader_ranged
		elif leader_type == "spear":
			formation = formation_spear_leader_melee if is_melee_hero else formation_spear_leader_ranged
		else:
			formation = formation_ranged_leader_melee if is_melee_hero else formation_ranged_leader_ranged

		if follower_count == 1:
			mapped_index = len(formation) // 2
		elif follower_count == 2:
			center = len(formation) // 2
			if hero_index == 0:
				mapped_index = max(center - 1, 0)
			else:
				mapped_index = min(center + 1, len(formation) - 1)
		elif follower_count <= 4:
			center = len(formation) // 2
			offset_map = [-1, 0, 1, 2]
			if hero_index >= len(offset_map):
				hero_index = len(offset_map) - 1
			mapped_index = center + offset_map[hero_index]
			mapped_index = max(0, min(mapped_index, len(formation) - 1))
		else:
			mapped_index = hero_index

		if 0 <= mapped_index < len(formation):
			return formation[mapped_index]

		if 0 <= hero_index < len(hero_formation):
			return hero_formation[hero_index]
		return 0.0

	def execute(self) -> NodeStatus:
		try:
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

			if self._last_dist == 0.0:
				self._last_dist = dist
				self._no_progress_ticks = 0
			else:
				progress = self._last_dist - dist
				if progress < MIN_PROGRESS_DISTANCE:
					self._no_progress_ticks += 1
				else:
					self._no_progress_ticks = 0
				self._last_dist = dist

			formation_angle_deg = self._get_angle_for_slot()
			angle_on_hero_grid = follow_angle + Utils.DegToRad(formation_angle_deg)

			import math

			formation_scale = 1.0
			leader_type = self._get_leader_type()

			if leader_type == "melee":
				base_radius = 200.0
			else:
				if not self._is_melee_hero():
					formation_scale = 1.8
				base_radius = Range.Touch.value * formation_scale

			try:
				if dist < Range.Nearby.value:
					base_radius *= 0.6
				if dist < Range.Adjacent.value:
					base_radius *= 0.4
			except Exception:
				pass

			base_x = base_radius * math.cos(angle_on_hero_grid) + follow_x
			base_y = base_radius * math.sin(angle_on_hero_grid) + follow_y

			target_x, target_y = base_x, base_y

			if self._no_progress_ticks >= STUCK_TICK_THRESHOLD:
				self._in_escape_mode = True
				hero_x, hero_y = hero_pos
				angle_to_target = math.atan2(follow_y - hero_y, follow_x - hero_x)

				best_probe = (base_x, base_y)
				best_probe_dist = dist

				for angle_deg in ESCAPE_PROBE_ANGLES_DEG:
					probe_angle = angle_to_target + Utils.DegToRad(angle_deg)
					probe_x = Range.Spellcast.value * 0.7 * math.cos(probe_angle) + hero_x
					probe_y = Range.Spellcast.value * 0.7 * math.sin(probe_angle) + hero_y
					probe_dist = Utils.Distance((probe_x, probe_y), (follow_x, follow_y))

					if probe_dist < best_probe_dist:
						best_probe = (probe_x, probe_y)
						best_probe_dist = probe_dist

				target_x, target_y = best_probe
			else:
				self._in_escape_mode = False

			dist_to_target = Utils.Distance(hero_pos, (target_x, target_y))
			if dist_to_target <= FOLLOW_DEADZONE_DISTANCE:
				return NodeStatus.SUCCESS

			ActionQueueManager().ResetQueue("ACTION")
			GLOBAL_CACHE.Player.Move(target_x, target_y)

			return NodeStatus.SUCCESS

		except Exception:
			return NodeStatus.FAILURE


_follow_bt: Optional[BehaviorTree] = None
_follow_rt: Optional[ThrottledTimer] = None


def should_tick_follow_bt() -> bool:
	global _follow_rt
	if _follow_rt is None:
		_follow_rt = ThrottledTimer(FOLLOW_BT_TICK_MS)
	if not _follow_rt.IsExpired():
		return False
	_follow_rt.Reset()
	return True


def get_follow_bt(cached_data: CacheData) -> BehaviorTree:
	global _follow_bt
	if _follow_bt is None:
		_follow_bt = BehaviorTree(SequenceNode([CanFollowNode(cached_data), FollowNode(cached_data)]))
	return _follow_bt
