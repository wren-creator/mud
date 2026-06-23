from typing import Optional

# ANSI colors
RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[1;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[1;36m"
WHITE  = "\033[1;37m"
DIM    = "\033[2m"
GREEN  = "\033[1;32m"
BLUE   = "\033[1;34m"


def _color_for_d20(result: int) -> str:
    if result == 20:
        return RED      # nat 20
    if result == 1:
        return BLUE     # nat 1
    if result >= 15:
        return GREEN
    if result <= 5:
        return DIM
    return YELLOW


# ── Die face templates ──────────────────────────────────────────────────────
# Each template has a {val} slot for the number.

_D4 = """\
     /\\
    /{v:^2}\\
   /    \\
  /  d4  \\
 /________\\"""

_D6 = """\
 +-------+
 |       |
 |  {v:^3}  |
 |  d6   |
 +-------+"""

_D8 = """\
    /\\
   /{v:^2}\\
  / d8 \\
 <     >
  \\   /
   \\ /
    V"""

_D10 = """\
    /\\
   /{v:^2}\\
  / d10\\
  \\    /
   \\  /
    \\/"""

_D12 = """\
  .-----.
 / {v:^3}  \\
/ d12   \\
\\       /
 \\.___./"""

_D20 = """\
     /\\
    /{v:^2}  \\
   / d20  \\
  /        \\
 /          \\
/____________\\"""

_D100 = """\
 .---------.
 |  {v:^3}    |
 |  d100   |
 '---------'"""

_DIE_TEMPLATES = {
    4:   _D4,
    6:   _D6,
    8:   _D8,
    10:  _D10,
    12:  _D12,
    20:  _D20,
    100: _D100,
}


def die_face(sides: int, result: int, color: Optional[str] = None) -> str:
    template = _DIE_TEMPLATES.get(sides, _D20)
    if color is None:
        color = _color_for_d20(result) if sides == 20 else YELLOW
    face = template.format(v=str(result))
    lines = face.split("\n")
    colored = "\n".join(f"  {color}{line}{RESET}" for line in lines)
    return colored


def roll_line(die: int, result: int, modifier: int = 0, total: Optional[int] = None) -> str:
    color = _color_for_d20(result) if die == 20 else YELLOW
    mod_str = f" {'+' if modifier >= 0 else ''}{modifier}" if modifier != 0 else ""
    tot_str = f" = {WHITE}{total}{RESET}" if total is not None else ""
    label = f"{color}d{die}{RESET}"
    return f"  {label} rolled {color}{result}{RESET}{mod_str}{tot_str}"


def crit_banner() -> str:
    return f"\n  {RED}{'★ CRITICAL HIT ★':^30}{RESET}\n"


def fumble_banner() -> str:
    return f"\n  {BLUE}{'✗ NATURAL 1 ✗':^30}{RESET}\n"


def format_attack_roll(d20_result: int, modifier: int, target_ac: int) -> str:
    total = d20_result + modifier
    hit = total >= target_ac or d20_result == 20
    crit = d20_result == 20
    fumble = d20_result == 1

    lines = [die_face(20, d20_result)]

    if crit:
        lines.append(crit_banner())
    elif fumble:
        lines.append(fumble_banner())

    status = f"{RED}CRIT!{RESET}" if crit else (f"{GREEN}HIT{RESET}" if hit else f"{DIM}MISS{RESET}")
    lines.append(f"  Roll: {_color_for_d20(d20_result)}{d20_result}{RESET} + {modifier} = {WHITE}{total}{RESET}  vs AC {target_ac}  →  {status}")
    return "\n".join(lines)


def format_damage_roll(sides: int, rolls: list[int], modifier: int = 0, label: str = "damage") -> str:
    total = sum(rolls) + modifier
    mod_str = f" + {modifier}" if modifier > 0 else (f" - {abs(modifier)}" if modifier < 0 else "")
    dice_str = " + ".join(str(r) for r in rolls)
    lines = []
    if len(rolls) <= 2:
        # Show full die face(s) for 1-2 dice
        for r in rolls:
            lines.append(die_face(sides, r))
    else:
        # Compact inline summary for 3+ dice (e.g. 8d6 fireball)
        lines.append(f"  {YELLOW}[{len(rolls)}d{sides}: {dice_str}]{RESET}")
    lines.append(f"  {CYAN}{label}{RESET}: {dice_str}{mod_str} = {WHITE}{total}{RESET}")
    return "\n".join(lines)
