"""Additive catalogue entries delivered by signed script updates.

Cosmo's kit: Supercell release notes, August 2026.
Ranges: 69.230 skills.csv, AttractorWeapon (27), AttractorUlti (28),
both Attractor gadgets (22); one tile is three game units / 64 reference pixels.
The 80% spacing floor is a bot policy, not an in-game damage threshold.
"""

BUILT_IN_BRAWLERS = {
    'cosmo': {
        'actual_name': 'Cosmo',
        'rarity': 'Mythic',
        'attack_range': 576,
        'safe_range': 460.8,
        'super_range': 597,
        'super_type': 'damage',
        'ignore_walls_for_attacks': False,
        'ignore_walls_for_supers': False,
        'hold_attack': 0,
        'attack_pattern': 'expanding_orbit',
        'gadget_range': 469,
    },
}


def with_built_in_brawlers(saved):
    """Fill absent defaults in memory; retain every saved user override."""
    result = {name: dict(info) for name, info in saved.items()}
    for name, defaults in BUILT_IN_BRAWLERS.items():
        result[name] = {**defaults, **result.get(name, {})}
    return result
