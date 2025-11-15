from typing import Optional

import Py4GW
from Py4GWCoreLib import ThrottledTimer, GLOBAL_CACHE, Range

from .bt import BehaviorTree, SequenceNode, ActionNode, ConditionNode, NodeStatus
from .cache_data import CacheData
from .globals import (
    hero_formation,
    formation_melee_leader_melee,
    formation_melee_leader_ranged,
    formation_ranged_leader_melee,
    formation_ranged_leader_ranged,
    formation_spear_leader_melee,
    formation_spear_leader_ranged,
)
from Py4GWCoreLib import Utils, ActionQueueManager


FOLLOW_BT_TICK_MS = 333  # ~3 ticka u sekundi
# Manja deadzona da se heroji pozicioniraju blize slotu pre nego sto stanu
FOLLOW_DEADZONE_DISTANCE = 60.0

# Anti-stuck parametri (izrazeni u BT tickovima i distanci)
STUCK_TICK_THRESHOLD = 45  # ~15 sekundi ako je BT na 3 Hz
MIN_PROGRESS_DISTANCE = 40.0  # minimalno smanjenje distance da kazemo da smo napredovali
ESCAPE_PROBE_ANGLES_DEG = (-60.0, 60.0, -135.0, 135.0)


class CanFollowNode(ConditionNode):
    """Proverava da li je bezbedno i smisleno pokrenuti follow logiku.

    Ovo zamjenjuje deo if-ova iz UpdateStatus kako bi BT bio deklarativniji.
    """

    def __init__(self, cached_data: CacheData):
        super().__init__("CanFollow")
        self.cached_data = cached_data

    def check(self) -> bool:
        # Ne radimo follow u outpostu uopšte
        if GLOBAL_CACHE.Map.IsOutpost():
            Py4GW.Console.Log(
                "HeroAI",
                "[FollowBT][CanFollow] Outpost detected, skipping follow",
                Py4GW.Console.MessageType.Debug,
            )
            return False

        # Mapa mora biti explorable i ne u cinematic
        if not GLOBAL_CACHE.Map.IsExplorable():
            return False
        if GLOBAL_CACHE.Map.IsInCinematic():
            return False

        player_id = GLOBAL_CACHE.Player.GetAgentID()

        # Player mora biti živ
        if not GLOBAL_CACHE.Agent.IsAlive(player_id):
            return False

        # Lider mora postojati i biti živ, i ne previše daleko
        try:
            leader_id = GLOBAL_CACHE.Party.GetPartyLeaderID()
            if leader_id == 0 or not GLOBAL_CACHE.Agent.IsAlive(leader_id):
                Py4GW.Console.Log(
                    "HeroAI",
                    "[FollowBT][CanFollow] Leader invalid or dead, skipping follow",
                    Py4GW.Console.MessageType.Debug,
                )
                return False
            player_pos = GLOBAL_CACHE.Agent.GetXY(player_id)
            leader_pos = GLOBAL_CACHE.Agent.GetXY(leader_id)
            dist_leader = Utils.Distance(player_pos, leader_pos)
            if dist_leader > Range.SafeCompass.value:
                return False
        except Exception:
            # Ako nešto pođe po zlu sa pozicijama, bolje je preskočiti follow ovaj tik
            return False

        # Ne pomeraj se dok si KD
        if GLOBAL_CACHE.Agent.IsKnockedDown(player_id):
            return False

        # Ne pomeraj se dok castaš/AI combat handler radi cast
        if self.cached_data.combat_handler.InCastingRoutine() or GLOBAL_CACHE.Agent.IsCasting(player_id):
            return False

        return True


class FollowNode(ActionNode):
    """BT action node that performs follow movement.

    Zasad koristi jednostavnu logiku: flag > leader, formacija po hero grid poziciji.
    """

    def __init__(self, cached_data: CacheData):
        super().__init__("Follow")
        self.cached_data = cached_data
        # Anti-stuck interno stanje, ne diramo shared/cached strukture
        self._last_dist: float = 0.0
        self._no_progress_ticks: int = 0
        self._in_escape_mode: bool = False
        # Broj aktivnih followera u trenutnom partyju (dinamicka formacija)
        self._follower_count: int = 0

    def _get_leader_type(self) -> str:
        """Vraca tip lidera: 'melee', 'spear', 'ranged'."""
        leader_id = GLOBAL_CACHE.Party.GetPartyLeaderID()
        if leader_id == 0:
            return "ranged"

        # Ako imamo direktan helper za Paragona, ovde ga mozemo dodati;
        # za sada koristimo jednostavnu heuristiku: spear/paragon se ponasa kao ranged.

        if GLOBAL_CACHE.Agent.IsMelee(leader_id):
            return "melee"
        return "ranged"

    def _is_melee_hero(self) -> bool:
        """Da li je ovaj heroj melee (koristi Agent.IsMelee)."""
        return GLOBAL_CACHE.Agent.IsMelee(GLOBAL_CACHE.Player.GetAgentID())

    def _get_relative_slot(self) -> int:
        """Vraca relativni slot index (0..N) za trenutnog heroja medu svim aktivnim followerima.
        
        Prolazi kroz all_player_struct, broji samo aktivne followere (ne lidera),
        i vraca indeks trenutnog igraca u toj listi.
        """
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
            
            # Ovo je aktivan follower
            if player_struct.PlayerID == player_id:
                # sacuvaj ukupni broj followera (bice poznat tek kad prodjemo kroz ceo niz)
                # privremeno zapamti slot koji odgovara ovom heroju
                hero_slot = follower_index
            follower_index += 1
            follower_count += 1

        # sacuvaj broj aktivnih followera za dinamicku formaciju
        self._follower_count = follower_count

        # Ako nismo nasli sebe, fallback na 0
        try:
            return hero_slot  # type: ignore[name-defined]
        except NameError:
            return 0
        
        # Fallback: ako nismo nasli sebe, vrati 0
        return 0

    def _get_angle_for_slot(self) -> float:
        """Odabir ugla iz odgovarajuce formacije za trenutnog heroja.

        Koristi relativni slot (0..N) medu svim aktivnim followerima,
        tako da formacija radi i ako party brojevi preskaču ili ako se party sastav menja.
        """
        leader_type = self._get_leader_type()
        is_melee_hero = self._is_melee_hero()

        # Dobij relativni index ovog heroja medu followerima
        hero_index = self._get_relative_slot()
        follower_count = max(self._follower_count, 1)

        # Za svaki tip koristimo odgovarajucu listu; ako je index van opsega – fallback na hero_formation
        if leader_type == "melee":
            formation = formation_melee_leader_melee if is_melee_hero else formation_melee_leader_ranged
        elif leader_type == "spear":
            formation = formation_spear_leader_melee if is_melee_hero else formation_spear_leader_ranged
        else:
            formation = formation_ranged_leader_melee if is_melee_hero else formation_ranged_leader_ranged

        # Dinamicko mapiranje hero_index -> indeks u formaciji na osnovu broja followera
        # 1 follower  -> koristi centralnu poziciju (sredina niza)
        # 2 followera -> levo/desno oko centra
        # 3-4         -> koriste centralne slotove, ignorišu ekstremne
        # 5+          -> pune formacije, koristi direktan indeks
        if follower_count == 1:
            mapped_index = len(formation) // 2
        elif follower_count == 2:
            center = len(formation) // 2
            if hero_index == 0:
                mapped_index = max(center - 1, 0)
            else:
                mapped_index = min(center + 1, len(formation) - 1)
        elif follower_count <= 4:
            # sabij u sredinu formacije
            center = len(formation) // 2
            offset_map = [-1, 0, 1, 2]  # do 4 slota oko centra
            if hero_index >= len(offset_map):
                hero_index = len(offset_map) - 1
            mapped_index = center + offset_map[hero_index]
            mapped_index = max(0, min(mapped_index, len(formation) - 1))
        else:
            # puni party – koristi direktan indeks
            mapped_index = hero_index

        if 0 <= mapped_index < len(formation):
            return formation[mapped_index]

        # Fallback na legacy hero_formation ako nemamo definisan ugao
        if 0 <= hero_index < len(hero_formation):
            return hero_formation[hero_index]
        return 0.0

    def execute(self) -> NodeStatus:
        try:
            Py4GW.Console.Log(
                "HeroAI",
                "[FollowBT] Tick FollowNode",
                Py4GW.Console.MessageType.Debug,
            )
            # Ako smo party leader, ne radimo follow logiku
            if GLOBAL_CACHE.Player.GetAgentID() == GLOBAL_CACHE.Party.GetPartyLeaderID():
                return NodeStatus.SUCCESS

            # Ako je follow globalno isključen, BT uspešno "ne radi ništa"
            if not self.cached_data.data.is_following_enabled:
                return NodeStatus.SUCCESS

            party_number = GLOBAL_CACHE.Party.GetOwnPartyNumber()

            follow_x = 0.0
            follow_y = 0.0
            follow_angle = -1.0

            all_player_struct = self.cached_data.HeroAI_vars.all_player_struct
            if all_player_struct[party_number].IsFlagged:  # my own flag
                follow_x = all_player_struct[party_number].FlagPosX
                follow_y = all_player_struct[party_number].FlagPosY
                follow_angle = all_player_struct[party_number].FollowAngle
                Py4GW.Console.Log(
                    "HeroAI",
                    "[FollowBT] Following OWN flag",
                    Py4GW.Console.MessageType.Debug,
                )
            elif all_player_struct[0].IsFlagged:  # leader's flag
                follow_x = all_player_struct[0].FlagPosX
                follow_y = all_player_struct[0].FlagPosY
                follow_angle = all_player_struct[0].FollowAngle
                Py4GW.Console.Log(
                    "HeroAI",
                    "[FollowBT] Following LEADER flag",
                    Py4GW.Console.MessageType.Debug,
                )
            else:  # follow leader
                follow_x, follow_y = GLOBAL_CACHE.Agent.GetXY(GLOBAL_CACHE.Party.GetPartyLeaderID())
                follow_angle = GLOBAL_CACHE.Agent.GetRotationAngle(GLOBAL_CACHE.Party.GetPartyLeaderID())
                Py4GW.Console.Log(
                    "HeroAI",
                    "[FollowBT] Following LEADER",
                    Py4GW.Console.MessageType.Debug,
                )

            # Distance check sa "deadzone" – da se ne tresemo previše
            hero_pos = GLOBAL_CACHE.Agent.GetXY(GLOBAL_CACHE.Player.GetAgentID())
            dist = Utils.Distance(hero_pos, (follow_x, follow_y))

            # --- Anti-stuck detekcija napretka ---
            if self._last_dist == 0.0:
                # Prvi put samo inicijalizujemo
                self._last_dist = dist
                self._no_progress_ticks = 0
            else:
                progress = self._last_dist - dist
                if progress < MIN_PROGRESS_DISTANCE:
                    self._no_progress_ticks += 1
                else:
                    # Napravili smo realan napredak, resetujemo brojac
                    self._no_progress_ticks = 0
                self._last_dist = dist

            # Ugao u formaciji zavisi od tipa lidera i da li je heroj melee/ranged
            formation_angle_deg = self._get_angle_for_slot()
            angle_on_hero_grid = follow_angle + Utils.DegToRad(formation_angle_deg)

            # Py4GW Utils nema Cos/Sin, koristimo math.cos/sin
            import math

            # Osnovna formacijska distanca
            formation_scale = 1.0

            # Tip lidera utiče na osnovni radius formacije
            leader_type = self._get_leader_type()

            # Melee lider: followeri u polumesecu iza
            if leader_type == "melee":
                base_radius = 200.0
            else:
                # Ranged lider + ranged followeri stoje malo dalje da se ne guraju
                if not self._is_melee_hero():
                    formation_scale = 1.8
                base_radius = Range.Touch.value * formation_scale

            # Ako smo vec blizu lideru, agresivnije sabij formaciju da se brze "zakucaju" u slot
            try:
                if dist < Range.Nearby.value:
                    base_radius *= 0.6
                if dist < Range.Adjacent.value:
                    base_radius *= 0.4
            except Exception:
                pass

            # Osnovna formacijska pozicija
            base_x = base_radius * math.cos(angle_on_hero_grid) + follow_x
            base_y = base_radius * math.sin(angle_on_hero_grid) + follow_y

            target_x, target_y = base_x, base_y

            # Ako smo predugo bez napretka, probaj "escape" probe oko cilja
            if self._no_progress_ticks >= STUCK_TICK_THRESHOLD:
                self._in_escape_mode = True
                Py4GW.Console.Log(
                    "HeroAI",
                    f"[FollowBT] Detected potential stuck (dist={dist:.1f}, ticks={self._no_progress_ticks}), probing escape offsets",
                    Py4GW.Console.MessageType.Debug,
                )

                # Uzimamo ugao ka cilju i probamo nekoliko offset-ovanih pravaca
                hero_x, hero_y = hero_pos
                angle_to_target = math.atan2(follow_y - hero_y, follow_x - hero_x)

                best_probe = (base_x, base_y)
                best_probe_dist = dist

                for angle_deg in ESCAPE_PROBE_ANGLES_DEG:
                    probe_angle = angle_to_target + Utils.DegToRad(angle_deg)
                    probe_x = Range.Spellcast.value * 0.7 * math.cos(probe_angle) + hero_x
                    probe_y = Range.Spellcast.value * 0.7 * math.sin(probe_angle) + hero_y
                    probe_dist = Utils.Distance((probe_x, probe_y), (follow_x, follow_y))

                    Py4GW.Console.Log(
                        "HeroAI",
                        f"[FollowBT] Probe angle={angle_deg:+.0f} -> ({probe_x:.1f}, {probe_y:.1f}) dist_to_target={probe_dist:.1f}",
                        Py4GW.Console.MessageType.Debug,
                    )

                    if probe_dist < best_probe_dist:
                        best_probe = (probe_x, probe_y)
                        best_probe_dist = probe_dist

                target_x, target_y = best_probe

                Py4GW.Console.Log(
                    "HeroAI",
                    f"[FollowBT] Escape move to ({target_x:.1f}, {target_y:.1f}) new_dist_to_target={best_probe_dist:.1f}",
                    Py4GW.Console.MessageType.Debug,
                )
            else:
                self._in_escape_mode = False

            # Finalna deadzone provera: da li smo vec dovoljno blizu krajnje formacijske pozicije?
            dist_to_target = Utils.Distance(hero_pos, (target_x, target_y))
            if dist_to_target <= FOLLOW_DEADZONE_DISTANCE:
                Py4GW.Console.Log(
                    "HeroAI",
                    f"[FollowBT] Already in formation deadzone (dist_to_target={dist_to_target:.1f}), skipping move",
                    Py4GW.Console.MessageType.Debug,
                )
                return NodeStatus.SUCCESS

            Py4GW.Console.Log(
                "HeroAI",
                f"[FollowBT] Move to ({target_x:.1f}, {target_y:.1f}) dist_to_target={dist_to_target:.1f}",
                Py4GW.Console.MessageType.Debug,
            )

            ActionQueueManager().ResetQueue("ACTION")
            GLOBAL_CACHE.Player.Move(target_x, target_y)

            return NodeStatus.SUCCESS

        except Exception as e:
            Py4GW.Console.Log(
                "HeroAI",
                f"[FollowBT][FollowNode] Error: {str(e)}",
                Py4GW.Console.MessageType.Error,
            )
            return NodeStatus.FAILURE


_follow_bt: Optional[BehaviorTree] = None
_follow_rt: Optional[ThrottledTimer] = None


def should_tick_follow_bt() -> bool:
    """Global throttle za follow BT na ~3 ticka u sekundi."""
    global _follow_rt
    if _follow_rt is None:
        _follow_rt = ThrottledTimer(FOLLOW_BT_TICK_MS)
    # Canonical pattern used across the codebase:
    # if not timer.IsExpired(): skip; else Reset() and run logic once
    if not _follow_rt.IsExpired():
        return False

    Py4GW.Console.Log(
        "HeroAI",
        "[FollowBT] Throttle expired, ticking BT",
        Py4GW.Console.MessageType.Debug,
    )
    _follow_rt.Reset()
    return True


def get_follow_bt(cached_data: CacheData) -> BehaviorTree:
    global _follow_bt
    if _follow_bt is None:
        Py4GW.Console.Log(
            "HeroAI",
            "[FollowBT] Initializing BehaviorTree",
            Py4GW.Console.MessageType.Debug,
        )
        _follow_bt = BehaviorTree(SequenceNode([CanFollowNode(cached_data), FollowNode(cached_data)]))
    return _follow_bt
