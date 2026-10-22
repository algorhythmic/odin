"""A synthetic stand-in for the Claude Code CLI used by supervisor tests.

It answers ``--version`` and ``--help``, records each launch's argv, runs the
command hooks named in the inline ``--settings`` value for the events its plan
lists, and on SIGTERM runs SessionEnd hooks and exits 143, as the native CLI's
graceful shutdown path does. It is not evidence of native behaviour.

Plans come from the JSON file in FAKE_CLAUDE_PLAN: a list with one entry per
launch, each a list of steps: ["start"], ["turn", seconds], ["sleep", seconds],
["wait"] (until SIGTERM), ["ignore_term"], ["exit", code].
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

FLAGS = ("--remote-control --tools --mcp-config --session-id --resume --permission-mode --model "
         "--effort --append-system-prompt --system-prompt-snapshot --settings --name "
         "--disallowedTools --dangerously-load-development-channels")


def settings(argv):
    if "--settings" not in argv:
        return {}
    value = argv[argv.index("--settings") + 1]
    if value.startswith("{"):
        return json.loads(value)
    with open(value) as handle:
        return json.load(handle)


def session(argv):
    for flag in ("--resume", "--session-id"):
        if flag in argv:
            return argv[argv.index(flag) + 1]
    return None


def fire(argv, event, **fields):
    for group in settings(argv).get("hooks", {}).get(event, []):
        for hook in group["hooks"]:
            if "odin.executive_turn_hook" not in hook["args"]:
                continue
            body = {"hook_event_name": event, "session_id": session(argv), "cwd": os.getcwd()} | fields
            subprocess.run([hook["command"], *hook["args"]], input=json.dumps(body).encode(),
                           timeout=hook["timeout"] + 5, check=False)


def main():
    argv = sys.argv[1:]
    if argv == ["--version"]:
        print("2.1.308 (Claude Code)")
        return 0
    if argv == ["--help"]:
        print(FLAGS)
        return 0
    with open(os.environ["FAKE_CLAUDE_LOG"], "a") as log:
        log.write(json.dumps(argv) + "\n")
    counter = os.environ["FAKE_CLAUDE_LOG"] + ".count"
    index = int(Path(counter).read_text()) if os.path.exists(counter) else 0
    Path(counter).write_text(str(index + 1))
    plans = json.loads(Path(os.environ["FAKE_CLAUDE_PLAN"]).read_text())
    steps = plans[min(index, len(plans) - 1)]

    def graceful(*_):
        fire(argv, "SessionEnd", reason="other")
        os._exit(143)

    signal.signal(signal.SIGTERM, graceful)
    for step in steps:
        kind = step[0]
        if kind == "start":
            fire(argv, "SessionStart", source="resume")
        elif kind == "turn":
            fire(argv, "UserPromptSubmit")
            time.sleep(step[1])
            fire(argv, "Stop", background_tasks=[])
        elif kind == "sleep":
            time.sleep(step[1])
        elif kind == "ignore_term":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        elif kind == "wait":
            # Bounded so a failing test cannot hang: a distinct exit status.
            deadline = time.monotonic() + float(os.environ.get("FAKE_CLAUDE_MAX_SECONDS", "20"))
            while time.monotonic() < deadline:
                time.sleep(0.05)
            return 99
        elif kind == "exit":
            return step[1]
    return 0


if __name__ == "__main__":
    sys.exit(main())
