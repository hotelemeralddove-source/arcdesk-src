"""MCP presets must be servers that can actually start.

The first version of this list was wrong in a way no import check would catch:
three "reference" servers (fetch, time, git) are **Python** upstream, and their
npm names are either unpublished or held by npm's security placeholder
(mcp-server-fetch@0.0.1-security). `npx` therefore failed silently at runtime —
the worst kind of bug, because the app looked fine.

So this test asserts the *runner* for each server, not just that it exists.

Run:  python tests/test_mcp_presets.py
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("ARCDESK_HOME", "arcdesk-test-mcp")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from arcdesk.ai import mcp_presets as mp  # noqa: E402


def main() -> int:
    ok = True

    # ---------- 1. every preset is complete ---------------------------
    broken = []
    for p in mp.PRESETS:
        if not p.command or not p.args or "/" not in p.repo:
            broken.append(p.key)
        if p.command not in ("npx", "uvx", "python", "docker", "node"):
            broken.append(f"{p.key}: odd runner {p.command}")
    print(f"1) presets complete       : {len(mp.PRESETS)} presets, {len(broken)} "
          f"problems  {'OK' if not broken else 'FAIL ' + str(broken)}")
    ok &= not broken

    # ---------- 2. the Python servers use uvx (regression) ------------
    python_ones = {p.key: p.command for p in mp.PRESETS if p.key in ("fetch", "time", "git")}
    correct = all(cmd == "uvx" for cmd in python_ones.values())
    print(f"2) python servers → uvx   : {python_ones}  "
          f"{'OK' if correct else 'FAIL'}")
    ok &= correct

    # ---------- 3. nothing paid sneaks in ----------------------------
    paid = [p.key for p in mp.PRESETS if p.needs_account and not p.needs_account]
    account_only = [p.key for p in mp.PRESETS if p.needs_account]
    allowed = set(account_only) <= {"github"}
    print(f"3) account-free by default: account-only={account_only}  "
          f"{'OK' if allowed and not paid else 'FAIL'}")
    ok &= allowed

    # ---------- 4. enable_all is idempotent --------------------------
    cfg: dict = {}
    first, _ = mp.enable_all(cfg, workspace="/tmp")
    second, _ = mp.enable_all(cfg, workspace="/tmp")
    names = [s["name"] for s in cfg["mcp"]["servers"]]
    idem = len(names) == len(set(names)) and not second and "fetch" in names
    print(f"4) enable_all idempotent  : first={len(first)}, second={len(second)}, "
          f"total={len(names)}  {'OK' if idem else 'FAIL'}")
    ok &= idem

    # ---------- 5. skips are explained, not silent -------------------
    cfg2: dict = {}
    _, skipped = mp.enable_all(cfg2)
    explained = all("(" in s and ")" in s for s in skipped) and len(skipped) >= 2
    print(f"5) skips are explained    : {len(skipped)} skipped  "
          f"{'OK' if explained else 'FAIL ' + str(skipped)}")
    ok &= explained

    # ---------- 6. config shape matches what MCPManager reads -------
    entry = cfg["mcp"]["servers"][0]
    shape = {"name", "command", "args", "enabled"} <= set(entry)
    print(f"6) config shape           : {sorted(entry)[:5]}…  "
          f"{'OK' if shape else 'FAIL'}")
    ok &= shape

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
