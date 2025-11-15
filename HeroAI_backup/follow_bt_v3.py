# follow_bt v3 Backup
# Snapshot of HeroAI/follow_bt.py after:
# - _get_angle_for_slot direktno mapira party_number (1..7) → formation index (0..6)
# - formacije po tipu lidera i melee/ranged slotu
# - ranged leader + ranged follower: formation_scale = 1.6
# - finalna deadzone provera: dist_to_target = Distance(hero_pos, (target_x, target_y))
#   ako dist_to_target <= FOLLOW_DEADZONE_DISTANCE, return SUCCESS bez move
# - anti-stuck: escape probe logika za slucaj da heroj dugo nema progress

# This is a proxy file. Original: HeroAI/follow_bt.py at time of v3 backup.
