"""Sidebar groups sessions by profile: active first, rest alphabetical, empty
profiles kept, pinned rows first inside a group (docs/rfcs/profile-sidebar-and-reasoning.md)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = (Path(__file__).parent.parent / "static" / "sessions.js").read_text(encoding="utf-8")
NODE = shutil.which("node")


def _fn(name: str) -> str:
    m = re.search(rf"^function {name}\(", SRC, re.M)
    assert m, f"{name} not found"
    i = SRC.index("{", m.start())
    depth = 0
    for j in range(i, len(SRC)):
        depth += SRC[j] == "{"
        depth -= SRC[j] == "}"
        if depth == 0:
            return SRC[m.start():j + 1]
    raise AssertionError(name)


def _group(sessions, profiles, active, is_default=False):
    script = (
        f"const S={{activeProfileIsDefault:{json.dumps(is_default)}}};\n"
        + _fn("_profileMatchesActiveProfile")
        + _fn("_groupSessionsByProfile")
        + f"\nconsole.log(JSON.stringify(_groupSessionsByProfile({json.dumps(sessions)},{json.dumps(profiles)},{json.dumps(active)})"
        ".map(g=>({key:g.key,active:g.isActive,ids:g.items.map(s=>s.id)}))));"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


@pytest.mark.skipif(not NODE, reason="node required")
def test_order_empty_profile_and_pinned():
    sessions = [  # already time-sorted, newest first
        {"id": "a", "profile": "default"},
        {"id": "b", "profile": "discord-bro"},
        {"id": "c", "profile": "default", "pinned": True},
        {"id": "d", "profile": "ghost"},  # not in profile list: kept
        {"id": "e"},                      # no profile -> default
    ]
    got = _group(sessions, ["default", "discord-bro", "scjournal"], "discord-bro")
    assert [(g["key"], g["ids"]) for g in got] == [
        ("profile:discord-bro", ["b"]),
        ("profile:default", ["c", "a", "e"]),
        ("profile:ghost", ["d"]),
        ("profile:scjournal", []),
    ]
    assert [g["active"] for g in got] == [True, False, False, False]


@pytest.mark.skipif(not NODE, reason="node required")
def test_renamed_root_default_merges_into_active():
    got = _group([{"id": "a", "profile": "default"}], ["root"], "root", is_default=True)
    assert [(g["key"], g["ids"]) for g in got] == [("profile:root", ["a"])]
