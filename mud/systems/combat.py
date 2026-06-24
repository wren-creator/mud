import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from entities.character import Character
    from entities.npc import NPC

from systems.dice_art import (
    format_attack_roll, format_damage_roll, die_face, roll_line,
    CYAN, WHITE, RESET, DIM, GREEN
)

SPELLS = {
    # name: (damage_dice, damage_sides, flat_bonus, save_type, description)
    "firebolt":       (1, 10, None,  None,           "a bolt of fire"),
    "ray of frost":   (1, 8,  None,  None,           "a ray of freezing cold"),
    "shocking grasp": (1, 8,  None,  None,           "crackling lightning"),
    "sacred flame":   (1, 8,  None,  "dexterity",    "sacred flame"),
    "eldritch blast": (1, 10, None,  None,           "a bolt of eldritch energy"),
    "magic missile":  (3, 4,  1,     None,           "three missiles of magical force"),
    "burning hands":  (3, 6,  None,  "dexterity",    "a cone of flame"),
    "thunderwave":    (2, 8,  None,  "constitution", "a wave of force"),
    "fireball":       (8, 6,  None,  "dexterity",    "a roaring ball of fire"),
    "lightning bolt": (8, 6,  None,  "dexterity",    "a bolt of lightning"),
    "cure wounds":    (1, 8,  None,  None,           "healing light"),
    "inflict wounds": (3, 10, None,  None,           "necrotic energy"),
    "chromatic orb":  (3, 8,  None,  None,           "an orb of raw magical energy"),
    "hex":            (1, 6,  None,  None,           "dark hexing energy"),
}

# Slot level for each spell; 0 = cantrip (unlimited uses)
SPELL_LEVELS: dict = {
    "firebolt":       0,
    "ray of frost":   0,
    "shocking grasp": 0,
    "sacred flame":   0,
    "eldritch blast": 0,
    "magic missile":  1,
    "burning hands":  1,
    "cure wounds":    1,
    "chromatic orb":  1,
    "hex":            1,
    "inflict wounds": 1,
    "thunderwave":    2,
    "fireball":       3,
    "lightning bolt": 3,
}


@dataclass
class AttackResult:
    hit: bool
    damage: int
    narrative: str   # full display string including dice art


def _roll(sides: int, n: int = 1) -> List[int]:
    return [random.randint(1, sides) for _ in range(n)]


def resolve_attack(attacker: "Character", defender: "NPC") -> AttackResult:
    [d20] = _roll(20)
    total = d20 + attacker.attack_mod
    crit = d20 == 20
    fumble = d20 == 1

    parts = [format_attack_roll(d20, attacker.attack_mod, defender.ac)]

    if fumble:
        return AttackResult(hit=False, damage=0, narrative="\n".join(parts))

    if crit or total >= defender.ac:
        n_dice, sides, dmg_mod = attacker.weapon_damage()
        dmg_rolls = _roll(sides, n_dice * (2 if crit else 1))
        dmg = max(1, sum(dmg_rolls) + dmg_mod)
        defender.hp -= dmg

        weapon = attacker.equipment.get("weapon")
        label = f"{weapon.name}" if weapon else "unarmed strike"
        parts.append(format_damage_roll(sides, dmg_rolls, modifier=dmg_mod, label=label))
        parts.append(
            f"  {defender.name} takes {WHITE}{dmg}{RESET} damage.  "
            f"[HP: {_hp_bar(defender.hp, defender.max_hp)}]"
        )
        return AttackResult(hit=True, damage=dmg, narrative="\n".join(parts))
    else:
        return AttackResult(hit=False, damage=0, narrative="\n".join(parts))


def resolve_spell(caster: "Character", spell_name: str, target: "NPC") -> AttackResult:
    spell = SPELLS.get(spell_name.lower())
    if not spell:
        return AttackResult(
            hit=False, damage=0,
            narrative=f"You don't know the spell '{spell_name}'."
        )

    n_dice, sides, flat_bonus, save_type, description = spell

    # ── Cure wounds (self-heal) ──────────────────────────────────────────────
    if spell_name == "cure wounds":
        stat = caster.stats.wisdom if caster.char_class in {"cleric","druid","paladin","ranger"} else caster.stats.charisma
        heal_rolls = _roll(8)
        mod = caster.stats.modifier(stat)
        healed = sum(heal_rolls) + mod
        caster.hp = min(caster.max_hp, caster.hp + healed)
        art = format_damage_roll(8, heal_rolls, modifier=mod, label="healed")
        msg = f"  Healing light washes over you.  [{_hp_bar(caster.hp, caster.max_hp)}]"
        return AttackResult(hit=True, damage=0, narrative=f"{art}\n{msg}")

    parts = [f"  {CYAN}You cast {spell_name}!{RESET}"]

    # ── Save-based spells ────────────────────────────────────────────────────
    if save_type:
        [save_d20] = _roll(20)
        save_bonus = _save_bonus(target, save_type)
        save_total = save_d20 + save_bonus
        saved = save_total >= caster.spell_dc

        parts.append(f"\n  {target.name}'s {save_type} save:")
        parts.append(die_face(20, save_d20))
        parts.append(
            f"  Save: {save_d20}+{save_bonus}={save_total} vs DC {caster.spell_dc}  "
            f"→  {'{'}{GREEN}saved — half damage{RESET}{'}' if saved else f'{DIM}failed{RESET}'}"
            .replace("{", "").replace("}", "")
        )

        dmg_rolls = _roll(sides, n_dice)
        raw = sum(dmg_rolls) + (flat_bonus or 0)
        dmg = raw // 2 if saved else raw
        target.hp -= dmg
        parts.append(format_damage_roll(sides, dmg_rolls, modifier=flat_bonus or 0, label=description))
        if saved:
            parts.append(f"  (halved by save)  Final: {WHITE}{dmg}{RESET}")
        parts.append(
            f"  {target.name} takes {WHITE}{dmg}{RESET} damage.  "
            f"[HP: {_hp_bar(target.hp, target.max_hp)}]"
        )
        return AttackResult(hit=True, damage=dmg, narrative="\n".join(parts))

    # ── Spell attack roll ────────────────────────────────────────────────────
    [atk_d20] = _roll(20)
    atk_total = atk_d20 + caster.attack_mod
    parts.append(format_attack_roll(atk_d20, caster.attack_mod, target.ac))

    if atk_d20 == 1 or (atk_total < target.ac and atk_d20 != 20):
        return AttackResult(hit=False, damage=0, narrative="\n".join(parts))

    dmg_rolls = _roll(sides, n_dice)
    dmg = sum(dmg_rolls) + (flat_bonus or 0)
    target.hp -= dmg
    parts.append(format_damage_roll(sides, dmg_rolls, modifier=flat_bonus or 0, label=description))
    parts.append(
        f"  {target.name} takes {WHITE}{dmg}{RESET} damage.  "
        f"[HP: {_hp_bar(target.hp, target.max_hp)}]"
    )
    return AttackResult(hit=True, damage=dmg, narrative="\n".join(parts))


def _save_bonus(target: "NPC", stat: str) -> int:
    return target.level // 3


def _hp_bar(current: int, maximum: int) -> str:
    if maximum <= 0:
        return "???"
    pct = max(0, current) / maximum
    filled = int(pct * 10)
    empty = 10 - filled
    color = "\033[1;32m" if pct > 0.5 else ("\033[1;33m" if pct > 0.25 else "\033[1;31m")
    bar = f"{color}{'█' * filled}{'░' * empty}{RESET}"
    return f"{bar} {max(0,current)}/{maximum}"
