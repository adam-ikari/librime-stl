#!/usr/bin/env python3
"""End-to-end test of this fork's plugin surface.

CI proves librime-lua compiles and links against this fork's librime. It cannot
prove the shipped binary works, because the fork replaced three things the
plugin depends on at runtime: the dlopen loader (boost::dll ->
rime/shared_library.hpp), boost::regex (-> std::regex plus the PCRE
translation), and boost::signals2 (-> rime::signal, which had to grow a grouped
connect for the plugin's notifier binding). Loading the real librime-lua.so into
the real engine and driving it through rime_console is what answers that.

Four checks:

  1. the loader must accept librime-lua.so and rime.lua must run. Standalone
     plugins built against a Boost-bearing librime used to link fine and die at
     dlopen on undefined boost symbols -- invisible until something loaded them;
  2. rime_api.regex_match/search/replace must work through
     cmake/plugin-shim/boost/regex.hpp, including the \\l/\\u translation;
  3. notifier:connect(fn, group) must emit in ascending group order, and in
     connection order inside one group -- the semantics
     src/rime/signal.hpp:connect(group, slot) claims. test/signal_test.cc pins
     that in C++; this pins it through the Lua binding that actually calls it;
  4. a pattern ECMAScript cannot express (lookbehind) must not be accepted
     silently. Measured policy: the shim throws std::regex_error at
     construction, the plugin's binding has no try/catch, and a C++ exception
     cannot cross the Lua VM's C frames -- so Lua's pcall does NOT contain it
     and the process aborts. Upstream aborts the same way for any pattern
     boost::regex itself rejects; the divergence is exactly the patterns boost
     accepts and ECMAScript does not.

Deployment notes, both learned from a failed first run:

  - rime.lua goes in the directory the console is pointed at, because that
    argument becomes deployer.user_data_dir (src/rime/setup.cc:50-52), which is
    what plugins/lua/src/modules.cc:43 reads. <deployment>/user/ is not it;
  - a <schema>.custom.yaml patch is NOT applied to luna_pinyin.schema.yaml. The
    schema has a root-level `__patch` (data/minimal/luna_pinyin.schema.yaml:21),
    and upstream's AutoPatchConfigPlugin skips auto-patch when one is already
    present (src/rime/config/auto_patch_config_plugin.cc:23-26). So the lua
    components are written into the harness's own copy of the schema text.

Usage:
    python3 test/e2e_lua.py [--keep]

Needs a tree built with -DENABLE_EXTERNAL_PLUGINS=ON -DBUILD_MERGED_PLUGINS=OFF
and plugins/lua present (bash install-plugins.sh hchunhui/librime-lua).
Exit status: 0 all green, 1 a check failed, 2 the harness prerequisites missing.
"""

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "dict" / "tools"))
import smoke  # reuse the deployment wiring the dictionary gate already proves

CONSOLE = REPO / "build" / "bin" / "rime_console"
PLUGIN_DIR = REPO / "build" / "lib" / "rime-plugins"

# Written as data, not as a Python string with escapes: Lua reads these patterns
# literally, and \\l inside a Lua long string is what the shim has to translate.
RIME_LUA = r"""
local ud = rime_api.get_user_data_dir()

local function w(name, text)
  local f = io.open(ud .. "/" .. name, "w")
  if f then f:write(text); f:close() end
end

local function a(name, text)
  local f = io.open(ud .. "/" .. name, "a")
  if f then f:write(text); f:close() end
end

local connected = false

function e2e_translator(input, seg, env)
  if input == "luaprobe" then
    local m = rime_api.regex_match("abc", [[\l+]])
    local mu = rime_api.regex_match("Abc", [[\u\l+]])
    local s = rime_api.regex_search("rime2026x", [[(\l+)\d+]])
    local r = rime_api.regex_replace("hello world", [[(\w+) (\w+)]], "$2 $1")
    w("e2e.regex", table.concat({
      "match_lower=" .. tostring(m),
      "match_upper=" .. tostring(mu),
      "search=" .. (s and table.concat(s, "|") or "nil"),
      "replace=" .. r,
    }, "\n"))
    local ctx = env.engine and env.engine.context
    if not connected and ctx then
      connected = true
      -- Connect out of order on purpose: what lands in the file has to be the
      -- emission order signals2 promises, not the order the calls were made.
      ctx.commit_notifier:connect(function(_) a("e2e.groups", "g2a\n") end, 2)
      ctx.commit_notifier:connect(function(_) a("e2e.groups", "g0a\n") end, 0)
      ctx.commit_notifier:connect(function(_) a("e2e.groups", "g0b\n") end, 0)
      ctx.commit_notifier:connect(function(_) a("e2e.groups", "g1a\n") end, 1)
    end
    yield(Candidate("e2e", seg.start, seg._end, "E2E-LUA-OK", " lua"))
  end
  if input == "luabad" then
    w("e2e.bad", "before")
    local ok, err = pcall(function()
      return rime_api.regex_match("ab", [[(?<=a)b]])
    end)
    a("e2e.bad", " pcall=" .. tostring(ok) .. " err=" .. tostring(err))
    yield(Candidate("e2e", seg.start, seg._end, "E2E-BAD-RAN", " lua"))
  end
end

function e2e_filter(input)
  for cand in input:iter() do
    -- Logged as each candidate passes, not after the loop: the consumer may
    -- stop at the first page, and then the tail of this coroutine never runs.
    a("e2e.filter", cand.text .. "\n")
    yield(cand)
  end
end
"""

# Anchored on the exact engine lists of the schema this harness deploys, so a
# future edit to that file fails loudly instead of silently untesting the plugin.
SCHEMA_EDITS = [
    ("  translators:\n", "  translators:\n    - lua_translator@e2e_translator\n"),
    ("  filters:\n", "  filters:\n    - lua_filter@e2e_filter\n"),
]

GROUPS_EXPECTED = "g0a\ng0b\ng1a\ng2a\n"
REGEX_EXPECTED = (
    "match_lower=true\n"
    "match_upper=true\n"
    "search=rime2026|rime\n"
    "replace=world hello"  # table.concat joins, it does not terminate the last row
)


def fail(msg):
    print(f"FAIL {msg}")
    return 1


def run(console, root, keys, extra=()):
    return subprocess.run([str(console), *extra, str(root)], cwd=root,
                          input=f"{keys}\n", capture_output=True, text=True)


def patch_schema(schema_path):
    text = schema_path.read_text(encoding="utf-8")
    for anchor, replacement in SCHEMA_EDITS:
        if text.count(anchor) != 1:
            return f"{schema_path}: expected exactly one {anchor!r}, found " \
                   f"{text.count(anchor)}"
        text = text.replace(anchor, replacement, 1)
    schema_path.write_text(text, encoding="utf-8")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="keep the deployment")
    args = parser.parse_args()

    if not CONSOLE.exists():
        return fail(f"no engine binary at {CONSOLE}")
    plugin = PLUGIN_DIR / "librime-lua.so"
    if not plugin.exists():
        return fail(f"no {plugin}; build with -DENABLE_EXTERNAL_PLUGINS=ON "
                    "-DBUILD_MERGED_PLUGINS=OFF after install-plugins.sh")

    root = pathlib.Path(tempfile.mkdtemp(prefix="e2e-lua-"))
    rc = 0
    try:
        err = smoke.build_deployment(root)
        if not err:
            err = patch_schema(root / "luna_pinyin.schema.yaml")
        if err:
            return fail(err)
        (root / "rime.lua").write_text(RIME_LUA, encoding="utf-8")

        deploy = subprocess.run([str(CONSOLE), "--build", str(root)], cwd=root,
                                capture_output=True, text=True)
        log = deploy.stdout + deploy.stderr
        errors = smoke.GLOG_ERROR.findall(log)
        if errors or deploy.returncode != 0:
            rc = fail("deployment did not build cleanly: "
                      + f"exit={deploy.returncode} output={log[-400:]}")
        if not rc:
            print("OK   deployment builds with zero error lines")

        # 1, 2 and 3: one committing run. The commit is what fires the notifier,
        # and the E2E-LUA-OK candidate is what proves the .so was dlopened and
        # rime.lua executed -- the loader's own messages go to the glog files,
        # not to anything this process captures.
        for name in ("e2e.regex", "e2e.groups", "e2e.filter"):
            (root / name).unlink(missing_ok=True)
        committed = run(CONSOLE, root, "luaprobe")
        if "E2E-LUA-OK" not in committed.stdout:
            rc = rc or fail(f"librime-lua.so did not produce a lua candidate "
                            f"(not loaded, or rime.lua not run): "
                            f"{committed.stdout[-300:]}{committed.stderr[-300:]}")
        else:
            print("OK   librime-lua.so loads and rime.lua registers a translator")

        got = (root / "e2e.regex").read_text(encoding="utf-8") \
            if (root / "e2e.regex").exists() else "<missing>"
        if got != REGEX_EXPECTED:
            rc = rc or fail(f"regex through the shim:\n"
                            f"  want {REGEX_EXPECTED!r}\n  got  {got!r}")
        else:
            print("OK   rime_api.regex_* works via cmake/plugin-shim (\\l, \\u, $1)")

        groups = (root / "e2e.groups").read_text(encoding="utf-8") \
            if (root / "e2e.groups").exists() else "<missing>"
        if groups != GROUPS_EXPECTED:
            rc = rc or fail(f"grouped connect emission:\n"
                            f"  want {GROUPS_EXPECTED!r}\n  got  {groups!r}")
        else:
            print("OK   commit_notifier emits in group order, connection order per group")

        filtered = (root / "e2e.filter").read_text(encoding="utf-8") \
            if (root / "e2e.filter").exists() else ""
        if "E2E-LUA-OK" not in filtered:
            rc = rc or fail("lua_filter never wrapped the translation")
        else:
            print(f"OK   lua_filter passed {len(filtered.splitlines())} candidates")

        # 4: lookbehind. Either the process aborts on the throw (measured) or a
        # later shim makes the failure catchable; what must never happen is the
        # pattern being accepted and matching something.
        (root / "e2e.bad").unlink(missing_ok=True)
        bad = run(CONSOLE, root, "luabad")
        state = (root / "e2e.bad").read_text(encoding="utf-8") \
            if (root / "e2e.bad").exists() else "<missing>"
        if "before" not in state:
            rc = rc or fail(f"the invalid-pattern probe never ran "
                            f"(exit={bad.returncode})")
        elif "pcall=true" in state:
            rc = rc or fail(f"an ECMAScript-invalid pattern was accepted: {state}")
        else:
            print(f"OK   invalid pattern is not accepted silently "
                  f"(exit={bad.returncode}, {state!r})")

        if args.keep:
            print(f"kept deployment at {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)
    finally:
        if not args.keep:
            shutil.rmtree(root, ignore_errors=True)

    print("e2e plugin test passed" if not rc else "e2e plugin test FAILED")
    return rc


if __name__ == "__main__":
    sys.exit(main())
