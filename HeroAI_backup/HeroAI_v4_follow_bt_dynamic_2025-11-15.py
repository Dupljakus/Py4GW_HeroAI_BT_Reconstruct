import math
import traceback
from enum import Enum

import Py4GW
from HeroAI.cache_data import CacheData
from HeroAI.constants import FOLLOW_DISTANCE_OUT_OF_COMBAT
from HeroAI.constants import MAX_NUM_PLAYERS
from HeroAI.constants import MELEE_RANGE_VALUE
from HeroAI.constants import PARTY_WINDOW_FRAME_EXPLORABLE_OFFSETS
from HeroAI.constants import PARTY_WINDOW_FRAME_OUTPOST_OFFSETS
from HeroAI.constants import PARTY_WINDOW_HASH
from HeroAI.constants import RANGED_RANGE_VALUE
from HeroAI.game_option import UpdateGameOptions
from HeroAI.players import RegisterHeroes
from HeroAI.players import RegisterPlayer
from HeroAI.players import UpdatePlayers
from HeroAI.utils import DistanceFromLeader
from HeroAI.utils import DistanceFromWaypoint
from HeroAI.follow_bt import should_tick_follow_bt, get_follow_bt
from HeroAI.windows import CompareAndSubmitGameOptions
from HeroAI.windows import DrawCandidateWindow
from HeroAI.windows import DrawControlPanelWindow
from HeroAI.windows import DrawFlaggingWindow
from HeroAI.windows import DrawFlags
from HeroAI.windows import DrawMainWindow
from HeroAI.windows import DrawMessagingOptions
from HeroAI.windows import DrawMultiboxTools
from HeroAI.windows import DrawOptions
from HeroAI.windows import DrawPanelButtons
from HeroAI.windows import SubmitGameOptions
from Py4GWCoreLib import GLOBAL_CACHE
from Py4GWCoreLib import ActionQueueManager
from Py4GWCoreLib import IconsFontAwesome5
from Py4GWCoreLib import ImGui
from Py4GWCoreLib import Key
from Py4GWCoreLib import Keystroke
from Py4GWCoreLib import LootConfig
from Py4GWCoreLib import Overlay
from Py4GWCoreLib import PyImGui
from Py4GWCoreLib import Range
from Py4GWCoreLib import Routines
from Py4GWCoreLib import ThrottledTimer
from Py4GWCoreLib import SharedCommandType
from Py4GWCoreLib import UIManager
from Py4GWCoreLib import Utils

MODULE_NAME = "HeroAI"

FOLLOW_COMBAT_DISTANCE = 25.0
LEADER_FLAG_TOUCH_RANGE_THRESHOLD_VALUE = Range.Touch.value * 1.1
LOOT_THROTTLE_CHECK = ThrottledTimer(250)

cached_data = CacheData()


def HandleOutOfCombat(cached_data: CacheData):
	if not cached_data.data.is_combat_enabled:
		return False
	if cached_data.data.in_aggro:
		return False

	return cached_data.combat_handler.HandleCombat(ooc=True)


def HandleCombatFlagging(cached_data: CacheData):
	party_number = GLOBAL_CACHE.Party.GetOwnPartyNumber()
	all_player_struct = cached_data.HeroAI_vars.all_player_struct
	if all_player_struct[party_number].IsFlagged:
		own_follow_x = all_player_struct[party_number].FlagPosX
		own_follow_y = all_player_struct[party_number].FlagPosY
		own_flag_coords = (own_follow_x, own_follow_y)
		if (
			Utils.Distance(own_flag_coords, GLOBAL_CACHE.Agent.GetXY(GLOBAL_CACHE.Player.GetAgentID()))
			>= FOLLOW_COMBAT_DISTANCE
		):
			return True
	elif all_player_struct[0].IsFlagged:
		leader_follow_x = all_player_struct[0].FlagPosX
		leader_follow_y = all_player_struct[0].FlagPosY
		leader_flag_coords = (leader_follow_x, leader_follow_y)
		if (
			Utils.Distance(leader_flag_coords, GLOBAL_CACHE.Agent.GetXY(GLOBAL_CACHE.Player.GetAgentID()))
			>= LEADER_FLAG_TOUCH_RANGE_THRESHOLD_VALUE
		):
			return True
	return False


def HandleCombat(cached_data: CacheData):
	if not cached_data.data.is_combat_enabled:
		return False
	if not cached_data.data.in_aggro:
		return False

	combat_flagging_handled = HandleCombatFlagging(cached_data)
	if combat_flagging_handled:
		return combat_flagging_handled
	return cached_data.combat_handler.HandleCombat(ooc=False)


cached_data.in_looting_routine = False


def LootingRoutineActive():
	account_email = GLOBAL_CACHE.Player.GetAccountEmail()
	index, message = GLOBAL_CACHE.ShMem.PreviewNextMessage(account_email)

	if index == -1 or message is None:
		return False

	if message.Command != SharedCommandType.PickUpLoot:
		return False
	return True


def Loot(cached_data: CacheData):
	global LOOT_THROTTLE_CHECK

	if not cached_data.data.is_looting_enabled:
		return False

	if cached_data.data.in_aggro:
		return False

	if LootingRoutineActive():
		return True

	if not LOOT_THROTTLE_CHECK.IsExpired():
		cached_data.in_looting_routine = True
		return True

	if GLOBAL_CACHE.Inventory.GetFreeSlotCount() < 1:
		return False

	loot_array = LootConfig().GetfilteredLootArray(
		Range.Earshot.value,
		multibox_loot=True,
		allow_unasigned_loot=False,
	)
	if len(loot_array) == 0:
		cached_data.in_looting_routine = False
		return False

	cached_data.in_looting_routine = True
	self_account = GLOBAL_CACHE.ShMem.GetAccountDataFromEmail(cached_data.account_email)
	if not self_account:
		cached_data.in_looting_routine = False
		return False

	if LOOT_THROTTLE_CHECK.IsExpired():
		GLOBAL_CACHE.ShMem.SendMessage(
			self_account.AccountEmail,
			self_account.AccountEmail,
			SharedCommandType.PickUpLoot,
			(0, 0, 0, 0),
		)
		LOOT_THROTTLE_CHECK.Reset()

	return True


following_flag = False


def Follow(cached_data: CacheData):
	global FOLLOW_DISTANCE_ON_COMBAT, following_flag

	if GLOBAL_CACHE.Player.GetAgentID() == GLOBAL_CACHE.Party.GetPartyLeaderID():
		cached_data.follow_throttle_timer.Reset()
		return False

	party_number = GLOBAL_CACHE.Party.GetOwnPartyNumber()
	if not cached_data.data.is_following_enabled:
		return False

	follow_x = 0.0
	follow_y = 0.0
	follow_angle = -1.0

	all_player_struct = cached_data.HeroAI_vars.all_player_struct
	if all_player_struct[party_number].IsFlagged:
		follow_x = all_player_struct[party_number].FlagPosX
		follow_y = all_player_struct[party_number].FlagPosY
		follow_angle = all_player_struct[party_number].FollowAngle
		following_flag = True
	elif all_player_struct[0].IsFlagged:
		follow_x = all_player_struct[0].FlagPosX
		follow_y = all_player_struct[0].FlagPosY
		follow_angle = all_player_struct[0].FollowAngle
		following_flag = False
	else:
		following_flag = False
		follow_x, follow_y = GLOBAL_CACHE.Agent.GetXY(GLOBAL_CACHE.Party.GetPartyLeaderID())
		follow_angle = GLOBAL_CACHE.Agent.GetRotationAngle(GLOBAL_CACHE.Party.GetPartyLeaderID())

	if following_flag:
		FOLLOW_DISTANCE_ON_COMBAT = FOLLOW_COMBAT_DISTANCE
	elif GLOBAL_CACHE.Agent.IsMelee(GLOBAL_CACHE.Player.GetAgentID()):
		FOLLOW_DISTANCE_ON_COMBAT = MELEE_RANGE_VALUE
	else:
		FOLLOW_DISTANCE_ON_COMBAT = RANGED_RANGE_VALUE

	if cached_data.data.in_aggro:
		follow_distance = FOLLOW_DISTANCE_ON_COMBAT
	else:
		follow_distance = FOLLOW_DISTANCE_OUT_OF_COMBAT if not following_flag else 0.0

	angle_changed_pass = False
	if cached_data.data.angle_changed and (not cached_data.data.in_aggro):
		angle_changed_pass = True

	close_distance_check = DistanceFromWaypoint(follow_x, follow_y) <= follow_distance

	if not angle_changed_pass and close_distance_check:
		return False

	hero_grid_pos = party_number + GLOBAL_CACHE.Party.GetHeroCount() + GLOBAL_CACHE.Party.GetHenchmanCount()
	angle_on_hero_grid = follow_angle

	if following_flag:
		xx = follow_x
		yy = follow_y
	else:
		xx = Range.Touch.value * math.cos(angle_on_hero_grid) + follow_x
		yy = Range.Touch.value * math.sin(angle_on_hero_grid) + follow_y

	cached_data.data.angle_changed = False
	ActionQueueManager().ResetQueue("ACTION")
	GLOBAL_CACHE.Player.Move(xx, yy)
	return True


def draw_Targeting_floating_buttons(cached_data: CacheData):
	if not cached_data.option_show_floating_targets:
		return
	if not GLOBAL_CACHE.Map.IsExplorable():
		return
	player_pos = GLOBAL_CACHE.Player.GetXY()
	enemy_array = Routines.Agents.GetFilteredEnemyArray(player_pos[0], player_pos[1], Range.SafeCompass.value)

	if len(enemy_array) == 0:
		return

	Overlay().BeginDraw()
	for agent_id in enemy_array:
		x, y, z = GLOBAL_CACHE.Agent.GetXYZ(agent_id)
		screen_x, screen_y = Overlay.WorldToScreen(x, y, z + 25)
		if ImGui.floating_button(
			f"{IconsFontAwesome5.ICON_CROSSHAIRS}", name=agent_id, x=screen_x - 12, y=screen_y - 12, width=25, height=25
		):
			GLOBAL_CACHE.Player.ChangeTarget(agent_id)
			GLOBAL_CACHE.Player.Interact(agent_id, True)
			ActionQueueManager().AddAction("ACTION", Keystroke.PressAndReleaseCombo, [Key.Ctrl.value, Key.Space.value])
	Overlay().EndDraw()
