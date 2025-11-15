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

"""HeroAI_v1_follow_bt_foundation backup.

Ovo je kompletna kopija `Widgets/HeroAI.py` u trenutku kada je:
- uveden behavior tree za follow (HeroAI/bt.py, HeroAI/follow_bt.py),
- follow BT koristi ThrottledTimer(333) za ~3Hz tikove,
- CanFollowNode preuslov je prebačen u BT,
- uvedena deadzone logika za follow (~120 range).

Ovaj fajl se NE koristi direktno u runtime-u; služi samo kao backup.
"""

MODULE_NAME = "HeroAI"

FOLLOW_COMBAT_DISTANCE = 25.0  # if body blocked, we get close enough.
LEADER_FLAG_TOUCH_RANGE_THRESHOLD_VALUE = Range.Touch.value * 1.1
LOOT_THROTTLE_CHECK = ThrottledTimer(250)

cached_data = CacheData()
