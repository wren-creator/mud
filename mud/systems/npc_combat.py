import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from entities.npc import NPC
    from entities.character import Character

from systems.dice_art import (
    format_attack_roll, format_damage_roll,
    WHITE, RESET, RED, YELLOW, GREEN, DIM, CYAN,
)

# Behavior constants
COWARDLY  = "cowardly"   # flees at 35% HP
BERSERKER = "berserker"  # never flees; bonus damage below 50% HP
UNDEAD    = "undead"     # never flees, no morale
GUARDIAN  = "guardian"   # holds position; flees at 10% HP
TACTICAL  = "tactical"   # may call allies; flees at 20% HP


@dataclass
class NPCTurnResult:
    narrative: str
    player_hp_after: int
    npc_fled: bool = False
    npc_called_help: bool = False


def npc_take_turn(npc: "NPC", player: "Character", is_aggro: bool = False) -> NPCTurnResult:
    behavior = getattr(npc, "behavior", UNDEAD)
    flee_threshold = getattr(npc, "flee_threshold", 0.25)
    hp_pct = npc.hp / npc.max_hp if npc.max_hp > 0 else 0

    # Check if NPC should flee
    if _should_flee(behavior, hp_pct, flee_threshold):
        msg = _flee_message(npc)
        npc.hp = -1  # mark as gone (fled, not dead — no XP)
        return NPCTurnResult(narrative=msg, player_hp_after=player.hp, npc_fled=True)

    # Build attack
    atk_mod  = getattr(npc, "attack_mod", npc.level // 2 + 2)
    dmg_dice = getattr(npc, "damage_dice", [1, 6])
    dmg_mod  = getattr(npc, "damage_mod", 0)
    n_dice, sides = dmg_dice

    # Berserker enrage: +2 dmg mod when below 50% HP
    if behavior == BERSERKER and hp_pct < 0.5:
        dmg_mod += 2
        enraged = True
    else:
        enraged = False

    d20 = random.randint(1, 20)
    total = d20 + atk_mod
    crit = d20 == 20

    opener = "attacks you!" if is_aggro else "strikes back!"
    lines = [f"\n  {RED}{npc.name}{RESET} {opener}"]
    if enraged:
        lines.append(f"  {RED}(ENRAGED — low HP!){RESET}")

    lines.append(format_attack_roll(d20, atk_mod, player.ac))

    if d20 == 1:
        lines.append(f"  {npc.name} fumbles the attack!")
        return NPCTurnResult(narrative="\n".join(lines), player_hp_after=player.hp)

    if crit or total >= player.ac:
        rolls = [random.randint(1, sides) for _ in range(n_dice * (2 if crit else 1))]
        dmg = max(1, sum(rolls) + dmg_mod)
        player.hp -= dmg

        lines.append(format_damage_roll(sides, rolls, modifier=dmg_mod, label=f"{npc.name}'s attack"))
        lines.append(_player_hp_line(player))
    else:
        lines.append(f"  {npc.name}'s attack glances off you.")

    return NPCTurnResult(narrative="\n".join(lines), player_hp_after=player.hp)


def resolve_flee(player: "Character", npc: "NPC") -> tuple[bool, str]:
    """Player attempts to flee. Returns (success, narrative)."""
    dex_mod = player.stats.modifier(player.stats.dexterity)
    flee_roll = random.randint(1, 20) + dex_mod
    dc = 12

    lines = [f"\n  {CYAN}You attempt to flee!{RESET}"]
    lines.append(format_attack_roll(flee_roll - dex_mod, dex_mod, dc)
                 .replace("d20", "DEX").replace("AC", "DC").replace("HIT", "ESCAPED").replace("MISS", "CAUGHT"))

    if flee_roll >= dc:
        lines.append(f"  {GREEN}You break away and run!{RESET}")
        return True, "\n".join(lines)
    else:
        # Opportunity attack
        lines.append(f"  {RED}You fail to escape — {npc.name} cuts you down as you turn!{RESET}")
        atk_mod  = getattr(npc, "attack_mod", npc.level // 2 + 2)
        dmg_dice = getattr(npc, "damage_dice", [1, 6])
        dmg_mod  = getattr(npc, "damage_mod", 0)
        n_dice, sides = dmg_dice

        opp_rolls = [random.randint(1, sides) for _ in range(n_dice)]
        opp_dmg = max(1, sum(opp_rolls) + dmg_mod)
        player.hp -= opp_dmg

        lines.append(format_damage_roll(sides, opp_rolls, modifier=dmg_mod, label="opportunity attack"))
        lines.append(_player_hp_line(player))
        return False, "\n".join(lines)


# ── Internals ───────────────────────────────────────────────────────────────

def _should_flee(behavior: str, hp_pct: float, threshold: float) -> bool:
    if behavior in (UNDEAD, BERSERKER):
        return False
    return hp_pct <= threshold


def _flee_message(npc: "NPC") -> str:
    lines = [
        f"  {YELLOW}{npc.name} looks around wildly and bolts for the nearest exit!{RESET}",
    ]
    # Flavor by race
    if "goblin" in npc.race.lower():
        lines.append(f"  {DIM}\"{npc.name}: 'Not worth dying for Gragnok! Not worth it!'\"  (flees){RESET}")
    elif "skeleton" in npc.race.lower():
        lines.append(f"  {DIM}The skeleton's bones scatter as it retreats into the darkness.{RESET}")
    else:
        lines.append(f"  {DIM}{npc.name} has fled. (No XP — it escaped.){RESET}")
    return "\n".join(lines)


def _player_hp_line(player: "Character") -> str:
    hp = player.hp
    mx = player.max_hp
    pct = max(0, hp) / mx if mx > 0 else 0
    filled = int(pct * 10)
    color = GREEN if pct > 0.5 else (YELLOW if pct > 0.25 else RED)
    bar = f"{color}{'█' * filled}{'░' * (10 - filled)}{RESET}"
    status = ""
    if hp <= 0:
        status = f"  {RED}YOU HAVE FALLEN!{RESET}"
    elif pct <= 0.25:
        status = f"  {RED}(critically wounded){RESET}"
    elif pct <= 0.5:
        status = f"  {YELLOW}(badly hurt){RESET}"
    return f"  Your HP: {bar} {max(0,hp)}/{mx}{status}"
