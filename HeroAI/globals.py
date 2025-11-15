from Py4GWCoreLib import ImGui, PyImGui, Timer
from .constants import MODULE_NAME, MAX_NUM_PLAYERS, NUMBER_OF_SKILLS
from .types import PlayerStruct, CandidateStruct, GameOptionStruct
from .shared_memory_manager import SharedMemoryManager

class HeroAI_varsClass:
    global MAX_NUM_PLAYERS, NUMBER_OF_SKILLS
    def __init__(self):
        self.shared_memory_handler = SharedMemoryManager()
        self.all_candidate_struct = [CandidateStruct() for _ in range(MAX_NUM_PLAYERS)]
        self.submit_candidate_struct = CandidateStruct()
        self.all_player_struct = [PlayerStruct() for _ in range(MAX_NUM_PLAYERS)]
        self.submit_player_struct = PlayerStruct()
        self.all_game_option_struct = [GameOptionStruct() for _ in range(MAX_NUM_PLAYERS)]
        self.global_control_game_struct = GameOptionStruct()
        self.submit_game_option_struct = GameOptionStruct()
        self.global_control_game_struct.Following = True
        self.global_control_game_struct.Avoidance = True
        self.global_control_game_struct.Looting = True
        self.global_control_game_struct.Targeting = True
        self.global_control_game_struct.Combat = True
        self.global_control_game_struct.WindowVisible = True
        
        for i in range(NUMBER_OF_SKILLS):
            self.global_control_game_struct.Skills[i].Active = True


class HeroAI_Window_varsClass:
    global MODULE_NAME
    def __init__(self):
        self.main_window = ImGui.WindowModule(MODULE_NAME, "HeroAI", window_size=(100, 100), window_flags=PyImGui.WindowFlags.AlwaysAutoResize)
        self.control_window = ImGui.WindowModule(MODULE_NAME, "HeroAI - Control Panel", window_size=(100, 100), window_flags=PyImGui.WindowFlags.AlwaysAutoResize)
        self.tools_window = ImGui.WindowModule(MODULE_NAME, "Multibox Tools", window_size=(100, 100), window_flags=PyImGui.WindowFlags.AlwaysAutoResize)

class DebugWindowClass:
    global MODULE_NAME
    def __init__(self, name):
        self.name = name
        self.visible = False
        self.window = ImGui.WindowModule(MODULE_NAME, name, window_size=(100, 100), window_flags=PyImGui.WindowFlags.AlwaysAutoResize)


class DebugWindowListClass:
    def __init__(self):
        self.main_window = DebugWindowClass("Debug Menu")
        self.candidate_window = DebugWindowClass("Candidates Debug")


""" Helper Variables """

oldAngle = 0.0  # used for angle change

# Osnovna formacija (legacy) – koristi se kao fallback
hero_formation = [
    0.0,
    45.0,
    -45.0,
    90.0,
    -90.0,
    135.0,
    -135.0,
    180.0,
    -180.0,
    225.0,
    -225.0,
    270.0,
]  # position on the grid of heroes

# Nove formacije po tipu lidera i tipu heroja (ugao u stepenima oko lidera)

# Lider melee: polumesec iza lidera (7 slotova od leve do desne strane)
formation_melee_leader_melee = [
    210.0,  # slot 1: levo iza
    195.0,  # slot 2: blize centru levo
    180.0,  # slot 3: direktno iza
    165.0,  # slot 4: blize centru desno
    150.0,  # slot 5: desno iza
    225.0,  # slot 6: krajnje levo
    135.0,  # slot 7: krajnje desno
]

# Ranged followeri za melee lidera takođe stoje u istom polumesecu iza
formation_melee_leader_ranged = [
    210.0,
    195.0,
    180.0,
    165.0,
    150.0,
    225.0,
    135.0,
]

# Lider ranged: melee "štit" ispred, ranged polu-krug pozadi
formation_ranged_leader_melee = [
    350.0,  # slot 1: malo desno ispred
    10.0,   # slot 2: malo levo ispred
    330.0,  # slot 3: desno više napred
    30.0,   # slot 4: levo više napred
    0.0,    # slot 5: centralno ispred
    320.0,
    40.0,
]

formation_ranged_leader_ranged = [
    # unutrašnji prsten (bliže lideru, zadnja linija)
    200.0,  # slot 1: malo desno iza
    160.0,  # slot 2: malo levo iza
    180.0,  # slot 3: centralno iza
    # spoljašnji prsten (dalje, širi luk)
    220.0,  # slot 4: desno šire
    140.0,  # slot 5: levo šire
    240.0,  # slot 6: krajnje desno
    120.0,  # slot 7: krajnje levo
]

# Lider spear (paragon): melee malo šire ispred, ranged zadnja linija kao kod ranged lidera
formation_spear_leader_melee = [
    340.0,  # slot 1: desno ispred
    20.0,   # slot 2: levo ispred
    315.0,
    45.0,
    0.0,
    300.0,
    60.0,
]

formation_spear_leader_ranged = formation_ranged_leader_ranged

overlay_explorable_initialized = False
show_area_rings = True
show_hero_follow_grid = True
show_distance_on_followers = True

capture_flag_all = False
capture_hero_flag = False
capture_hero_index = 0
capture_mouse_timer = Timer()

option_show_floating_targets = True
