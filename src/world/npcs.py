"""NPC definitions and hourly schedules.

Each NPC has waypoints (hour, map_id, x, y). Position between two waypoints
is a linear interpolation of the hour fraction — a simple, robust schedule.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..game.witnesses import WITNESSES

# Sprite keys: (coat, pants, skin, hair, hat, hair_style)
APPEARANCE: dict[str, tuple] = {
    "marta":   ((96, 84, 110), (58, 52, 68), (232, 196, 160), (205, 205, 210), 0, 2),
    "nick":    ((88, 70, 58), (46, 46, 56), (214, 172, 134), (52, 42, 32), 0, 3),
    "boris":   ((150, 128, 102), (62, 60, 70), (244, 214, 178), (92, 68, 46), 0, 0),
    "volkov":  ((70, 84, 110), (48, 52, 64), (214, 172, 134), (34, 30, 28), 0, 0),
    "krylov":  ((96, 112, 140), (48, 52, 64), (214, 172, 134), (168, 148, 118), 0, 0),
    "krylov2": ((88, 100, 128), (48, 52, 64), (232, 196, 160), (58, 44, 34), 0, 0),
    "banker":  ((58, 58, 68), (40, 40, 48), (214, 172, 134), (28, 28, 32), 0, 0),
    "w1":      ((108, 108, 88), (56, 56, 66), (214, 172, 134), (58, 44, 34), 0, 0),
    "w2":      ((118, 90, 108), (52, 52, 62), (244, 214, 178), (150, 110, 70), 0, 2),
    "w3":      ((102, 112, 120), (50, 54, 62), (214, 172, 134), (160, 160, 168), 0, 1),
    "emit":    ((36, 36, 44), (28, 28, 36), (214, 172, 134), (24, 24, 30), 0, 3),
}


@dataclass
class NPC:
    id: str
    schedule: list = field(default_factory=list)   # (hour, map_id, x, y)

    def waypoints_for(self, map_id: str) -> list:
        return [w for w in self.schedule if w[1] == map_id]

    def pos_at(self, hour: float, map_id: str) -> tuple[float, float] | None:
        """Position of the NPC at the given hour, or None if it is not on
        this map. The schedule is a full-day loop; segments crossing between
        maps switch at the midpoint."""
        pts = sorted(self.schedule, key=lambda w: w[0])
        if not pts:
            return None
        if len(pts) == 1:
            _, m, x, y = pts[0]
            return (float(x), float(y)) if m == map_id else None
        seg = None
        for i in range(len(pts) - 1):
            if pts[i][0] <= hour < pts[i + 1][0]:
                seg = (pts[i], pts[i + 1])
                break
        if seg is None:
            seg = (pts[-1], pts[0])          # wrap 24:00 -> 00:00
        (h0, m0, x0, y0), (h1, m1, x1, y1) = seg
        if h1 < h0:
            h1 += 24
        t = (hour - h0) / max(1e-6, (h1 - h0))
        t = max(0.0, min(1.0, t))
        if m0 == map_id and m1 == map_id:
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        if m0 == map_id:
            return (float(x0), float(y0)) if t < 0.5 else None
        if m1 == map_id:
            return (float(x1), float(y1)) if t >= 0.5 else None
        return None


NPC_DATA: dict[str, NPC] = {
    "marta": NPC("marta", [
        (0, "town", 48, 48), (8, "town", 48, 48), (10, "town", 55, 44),
        (13, "town", 43, 36), (16, "town", 55, 44), (19, "town", 48, 48),
        (24, "town", 48, 48),
    ]),
    "nick": NPC("nick", [
        (0, "town", 58, 48), (8, "town", 57, 44), (11, "town", 60, 47),
        (14, "town", 57, 44), (17, "town", 59, 48), (20, "town", 56, 47),
        (24, "town", 58, 48),
    ]),
    "boris": NPC("boris", [
        (0, "town", 73, 45), (8, "shop", 6, 5), (20, "town", 72, 44),
        (22, "town", 73, 45), (24, "town", 73, 45),
    ]),
    "volkov": NPC("volkov", [
        (0, "town", 11, 33), (9, "police", 11, 6), (18, "town", 12, 33),
        (20, "town", 10, 33), (24, "town", 11, 33),
    ]),
    "krylov": NPC("krylov", [
        (0, "victim", 8, 6), (24, "victim", 8, 6),
    ]),
    "krylov2": NPC("krylov2", [
        (0, "victim", 11, 7), (24, "victim", 11, 7),
    ]),
    "banker": NPC("banker", [
        (0, "town", 71, 34), (9, "bank", 6, 5), (17, "town", 70, 33),
        (19, "town", 71, 34), (24, "town", 71, 34),
    ]),
    "w1": NPC("w1", [
        (0, "town", 42, 30), (10, "town", 38, 32), (13, "town", 46, 34),
        (16, "town", 40, 30), (20, "town", 42, 30), (24, "town", 42, 30),
    ]),
    "w2": NPC("w2", [
        (0, "town", 68, 28), (10, "town", 66, 24), (14, "town", 74, 26),
        (18, "town", 68, 28), (24, "town", 68, 28),
    ]),
    "w3": NPC("w3", [
        (0, "town", 46, 36), (11, "town", 45, 36), (15, "town", 46, 36),
        (19, "town", 44, 38), (21, "town", 46, 36), (24, "town", 46, 36),
    ]),
    "emit": NPC("emit", [
        (0, "town", 88, 44), (3, "town", 92, 41), (6, "town", 90, 44),
        (9, "town", 93, 42), (12, "town", 88, 44), (15, "town", 92, 41),
        (18, "town", 90, 44), (21, "town", 93, 42), (24, "town", 88, 44),
    ]),
    "cat": NPC("cat", [
        (0, "town", 45, 34), (4, "town", 50, 36), (8, "town", 42, 32),
        (12, "town", 48, 33), (16, "town", 44, 35), (20, "town", 50, 34),
        (24, "town", 45, 34),
    ]),
}


def visible_npc_ids(state) -> list[str]:
    """NPCs present in the current investigation state."""
    ids = ["marta", "nick", "boris", "volkov", "krylov", "krylov2", "banker",
           "w1", "w2", "w3"]
    if state.flags.get("nick_ran"):
        ids.remove("nick")
    # Boris's cat wanders the park only while the "find the cat" task is active
    # and disappears once Mike has picked it up.
    if state.tasks.get("cat") == "active" and not state.flags.get("cat_carried"):
        ids.append("cat")
    # EMIT walks the town only after his identity is known — and only in the
    # present: meeting him in the past would spoil everything.
    if state.plot_stage >= 4 and state.offset_min == 0 and not state.flags.get("chase_started"):
        ids.append("emit")
    return ids


def npc_on_map(state, map_id: str, hour: float | None = None) -> list[str]:
    """NPC ids currently present on the given map (hour in 0..24)."""
    if hour is None:
        hour = state.minutes / 60.0
    out = []
    for nid in visible_npc_ids(state):
        npc = NPC_DATA[nid]
        if npc.pos_at(hour, map_id) is not None:
            out.append(nid)
    return out


def display_name(nid: str, lang: str) -> str:
    w = WITNESSES.get(nid)
    if not w:
        return nid
    return w["name"].get(lang, w["name"].get("ru", nid))
