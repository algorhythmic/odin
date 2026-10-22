"""Local admission paths, relaxed permits and the content-free audit (ODIN-ADR-034)."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

from odin import executive_runtime as runtime
from odin.contracts import ROOT, Contracts, identifier, strict_loads
from odin.executive_admission import (AUDIT_FILE, interpreter, interpreter_name, read_only,
                                     registered_script, registered_scripts, script_digest)
from odin.executive_intervention import delegation_guard
from odin.executive_intervention_hook import REFUSAL, handle
from odin.executive_mcp import ExecutiveBridge, ToolFailure
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway, error_result
from odin.service import Service

ACCEPT = [
    "git status", "git status --short", "git log --oneline -5", "git diff HEAD~1 -- docs",
    "git show --stat HEAD", "git rev-parse HEAD", "git rev-list --count HEAD",
    "git merge-base main HEAD", "git ls-files python", "git cat-file -p HEAD",
    "git blame README.md", "git describe --always", "git cherry -v main",
    "git shortlog -sn", "git grep -n intervention", "git for-each-ref refs/heads",
    "git worktree list", "git stash list", "git branch", "git branch -a -vv",
    "git branch --show-current", "git branch --list 'codex/*'", "git branch --contains=HEAD",
    "git reflog", "git reflog show -n 5", "git remote -v", "git remote",
    "git -C /home/x/repo log -1", "git --no-pager log -1", "git -C /a -C b status",
    "ls -la", "cat README.md", "head -n 5 AGENTS.md", "tail -n 20 x.log", "wc -l a b",
    "stat README.md", "du -sh docs", "df -h", "find . -name '*.py' -type f",
    "grep -rn 'ODIN-ADR-034' docs", "rg -n permit python", "jq '.scripts' f.json",
    "sort -u f", "uniq -c", "cut -d: -f1 /etc/passwd", "ps aux", "pgrep -af odin",
    "date -u +%Y-%m-%d", "uptime", "id", "whoami", "which git", "pwd",
    "systemctl --user status odin-executive-pilot-service",
    "systemctl --user show -p MainPID odin-executive-pilot-service",
    "systemctl --user is-active x", "systemctl --user is-enabled x",
    "systemctl --user list-units", "systemctl --user cat x",
    "journalctl --user -u odin-executive-pilot-service -n 50 --no-pager",
    "journalctl --user --since=-1h",
    "git log --oneline | head -3", "ps aux | grep odin | sort | uniq -c",
    'grep -n "two words" README.md', "cat ~/notes.md",
]

REJECT = [
    # Injection and shell syntax.
    "git log; rm -rf x", "git log && rm x", "git log || rm x", "git log & rm x",
    "git log $(rm x)", "echo $(id)", "git log `rm x`", "cat '$(x)'", "git log\nrm x",
    "cat <(rm x)", "cat > out", "cat < in", "ls >> out", "ls 2>&1", "git log > /tmp/x",
    "git log | rm x", "git log | sh", "git log |", "| git log", "git log | | cat",
    "cat $HOME/x", 'cat "$HOME"', "cat ${x}", "ls *.py", "ls ?", "ls [a]", "git branch {-D,x}",
    "ls # comment", "(ls)", "! ls", "ls 'unterminated", "ls \\", "x=1 ls", "FOO=bar git status",
    # find, grep and rg.
    "find . -exec rm {} +", "find . -execdir rm x", "find . -delete", "find . -ok rm",
    "find . -okdir rm", "find . -fprint out", "find . -fprintf out x", "find . -fls out",
    "rg --pre cat x", "rg --pre=cat x", "rg --pre-glob '*' x", "rg --hostname-bin=x x",
    "rg -z x", "rg --search-zip x", "grep --pre x",
    # git writes and dangerous options.
    "git branch -D x", "git branch -d x", "git branch -m a b", "git branch newbranch",
    "git branch -f x", "git branch --set-upstream-to=o/x", "git reflog expire --all",
    "git reflog delete HEAD@{0}", "git reflog drop", "git stash", "git stash pop",
    "git stash drop", "git worktree add x", "git worktree remove x", "git remote add o u",
    "git remote remove o", "git commit -m x", "git checkout x", "git reset --hard",
    "git push", "git fetch", "git -c core.pager=sh log", "git --git-dir=x status",
    "git log --output=x", "git diff --output x", "git diff --outp=x", "git log --ext-diff",
    "git grep -O vim x", "git grep --open-files-in-pager=vim x", "git grep -nO x", "git",
    # systemctl and journalctl.
    "systemctl --user restart odin", "systemctl --user stop odin", "systemctl --user start x",
    "systemctl --user daemon-reload", "systemctl status x", "systemctl --user",
    "systemctl --user status -H host x", "systemctl --user status --host=h x",
    "journalctl --user -f", "journalctl --user --follow", "journalctl --user -nf",
    "journalctl --user --fol", "journalctl --user --vacuum-size=1M", "journalctl --user --vacuum",
    "journalctl --user --rotate", "journalctl --user --flush", "journalctl --user --sync",
    "journalctl --user --cursor-file=x", "journalctl -u x",
    # Other allowlisted programs used to write or follow.
    "sort -o out f", "sort -uo out f", "sort --output=out f", "sort --compress-program=sh f",
    "uniq a b", "uniq -f 1 a", "tail -f x", "tail -F x", "tail --follow x", "date -s now",
    "date --set=now",
    # Not on the allowlist.
    "rm -rf x", "touch x", "python3 -c 1", "sh -c ls", "bash", "xargs ls", "tee x", "env",
    "sudo ls", "/bin/ls", "command ls", "ls; ", "",
]


def prepared(test):
    temp = tempfile.TemporaryDirectory(); test.addCleanup(temp.cleanup)
    test.temp = Path(temp.name)
    test.state = test.temp / 'state'
    test.project = prepare_project(test.state)
    runtime.prepare(test.state, config_dir=test.temp / 'login', project=test.project,
                    claude_binary=sys.executable, python_executable=sys.executable)
    runtime.enable_development(test.state)
    with runtime._owned_runtime(test.state): pass
    runtime.configure_execution_role(test.state, implementation_mode='delegated')
    with runtime._owned_runtime(test.state): pass
    test.manifest = runtime._load(test.state)[0]
    test.native = test.manifest['native_session_id']


def event(test, command=None, kind='PreToolUse', tool='Bash', tool_input=None, tool_use='synthetic-1'):
    return {'hook_event_name': kind, 'session_id': test.native, 'cwd': test.manifest['repository_root'],
            'tool_name': tool, 'tool_use_id': tool_use,
            'tool_input': tool_input if tool_input is not None else {'command': command, 'timeout': 1000}}


def unavailable(command):
    raise AssertionError('the service must not be called')


class ReadOnlyTableTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.state = Path(temp.name) / 'state'; self.state.mkdir(mode=0o700)

    def test_accept_table(self):
        for command in ACCEPT:
            with self.subTest(command=command):
                self.assertTrue(read_only({'command': command, 'timeout': 1000, 'description': 'x'},
                                          state=self.state))

    def test_reject_table(self):
        for command in REJECT:
            with self.subTest(command=command):
                self.assertFalse(read_only({'command': command}, state=self.state))

    def test_background_sandbox_and_unknown_inputs_are_not_read_only(self):
        for inputs in [{'command': 'git status', 'run_in_background': True},
                       {'command': 'git status', 'dangerouslyDisableSandbox': True},
                       {'command': 'git status', 'unexpected': 1},
                       {'command': 7}, {'command': '   '}, 'git status']:
            with self.subTest(inputs=inputs):
                self.assertFalse(read_only(inputs, state=self.state))
        self.assertTrue(read_only({'command': 'git status', 'run_in_background': False},
                                  state=self.state))

    def test_pilot_launcher_status_actions_only(self):
        launcher = self.state.parent / 'run'
        launcher.write_text('#!/bin/sh\n'); launcher.chmod(0o700)
        project = identifier()
        for args in ['executive-status', 'status', f'development-status --project {project}',
                     f'usage-status --project={project} --loop {project}', f'context-status --project {project}']:
            with self.subTest(args=args):
                self.assertTrue(read_only({'command': f'{launcher} {args}'}, state=self.state))
        for args in ['executive-start --resume-session', 'executive-register-script --path /x',
                     'executive-configure-memory-directory --memory-directory /x', 'stop',
                     'command --request /x', 'status --request /x', 'status --state /x',
                     'development-status --proj x', 'development-status --project',
                     'development-status --project -x', 'development-control --project x', '']:
            with self.subTest(args=args):
                self.assertFalse(read_only({'command': f'{launcher} {args}'}, state=self.state))
        self.assertFalse(read_only({'command': 'run executive-status'}, state=self.state))
        launcher.chmod(0o770)
        self.assertFalse(read_only({'command': f'{launcher} executive-status'}, state=self.state))
        launcher.chmod(0o700)
        real = self.state.parent / 'real-run'; launcher.rename(real); os.symlink(real, launcher)
        self.assertFalse(read_only({'command': f'{launcher} executive-status'}, state=self.state))


class RegisteredScriptTests(unittest.TestCase):
    def setUp(self):
        prepared(self)
        self.bin = self.temp / 'bin'; self.bin.mkdir()
        self.script = self.bin / 'diagnose.sh'
        self.script.write_text('#!/bin/sh\necho synthetic\n'); self.script.chmod(0o700)
        runtime.register_script(self.state, path=str(self.script))

    def admits(self, command, **inputs):
        return registered_script({'command': command} | inputs, scripts=registered_scripts(self.state),
                                 state=self.state)

    def test_registration_records_path_and_hash_privately(self):
        path = self.state / 'executive-pilot' / 'registered-scripts.json'
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        record = strict_loads(path.read_text())
        Contracts().validate('executive-registered-scripts', record)
        self.assertEqual(record['scripts'][0]['path'], str(self.script))
        self.assertEqual(len(record['scripts'][0]['sha256']), 64)

    def test_admitted_forms(self):
        for command in [str(self.script), f'{self.script} --flag value plain-arg',
                        f"{self.script} 'quoted arg'", f'{self.script} > /tmp/out.log 2>&1',
                        f'{self.script} >> /tmp/out.log', f'{self.script} 2> /tmp/err.log',
                        f'{self.script} 1>/tmp/out.log 2>/tmp/err.log', f'{self.script} < /tmp/in']:
            with self.subTest(command=command):
                self.assertTrue(self.admits(command))
        self.assertTrue(self.admits(str(self.script), run_in_background=True, timeout=5))

    def test_extra_shell_operators_refused(self):
        for suffix in ['; rm x', '&& rm x', '|| rm x', '| cat', '&', '2>&1 | cat', '> out',
                       '> ../out', '> /tmp/../etc/x', '&> /tmp/x', '>&2', '2>&-', '$(id)', '`id`',
                       '$HOME', '*', '{a,b}', '<< EOF', '>', '\nrm x', '# x']:
            with self.subTest(suffix=suffix):
                self.assertFalse(self.admits(f'{self.script} {suffix}'))
        self.assertFalse(self.admits(str(self.script), dangerouslyDisableSandbox=True))
        self.assertFalse(self.admits(f'FOO=1 {self.script}'))

    def test_hash_mismatch_refused_until_registered_again(self):
        self.script.write_text('#!/bin/sh\nrm -rf /\n')
        self.assertFalse(self.admits(str(self.script)))
        runtime.register_script(self.state, path=str(self.script))
        self.assertTrue(self.admits(str(self.script)))

    def test_symlink_and_relative_paths_refused(self):
        link = self.bin / 'link.sh'; os.symlink(self.script, link)
        with self.assertRaises(ValueError):
            runtime.register_script(self.state, path=str(link))
        linked_dir = self.temp / 'linked'; os.symlink(self.bin, linked_dir)
        for value in [str(linked_dir / 'diagnose.sh'), 'diagnose.sh', 'bin/diagnose.sh',
                      str(self.bin) + '/../bin/diagnose.sh', str(self.bin) + '//diagnose.sh',
                      str(self.bin), str(self.bin / 'missing.sh')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                runtime.register_script(self.state, path=value)
        self.assertFalse(self.admits(str(link)))
        os.chdir(self.bin); self.addCleanup(os.chdir, ROOT)
        self.assertFalse(self.admits('./diagnose.sh'))
        self.assertFalse(self.admits('diagnose.sh'))
        # A registered file later replaced by a symlink to identical bytes is refused.
        copy = self.bin / 'copy.sh'; copy.write_bytes(self.script.read_bytes())
        self.script.unlink(); os.symlink(copy, self.script)
        self.assertFalse(self.admits(str(self.script)))

    def test_redirections_cannot_rewrite_admission_inputs(self):
        # Bash reads a script as it runs, so appending to it would add commands.
        other = self.bin / 'other.sh'; other.write_text('#!/bin/sh\n')
        runtime.register_script(self.state, path=str(other))
        registry = self.state / 'executive-pilot' / 'registered-scripts.json'
        (self.temp / 'repo' / '.git').mkdir(parents=True)
        os.symlink(self.temp / 'out', self.temp / 'out-link')
        for target in [self.script, other, registry, self.state / 'executive-pilot' / AUDIT_FILE,
                       self.temp / 'repo' / '.git' / 'config', self.temp / 'repo' / '.GIT' / 'x',
                       self.temp / 'out-link', self.temp / 'out-link' / 'x']:
            for operator in ['>', '>>', '2>', '<']:
                with self.subTest(target=target, operator=operator):
                    self.assertFalse(self.admits(f'{self.script} hello {operator} {target}'))
        self.assertTrue(self.admits(f'{self.script} hello >> {self.temp / "out.log"} 2>&1'))

    def test_removed_registration_refused(self):
        result = runtime.register_script(self.state, path=str(self.script), remove=True)
        self.assertEqual(result['registered_scripts'], [])
        self.assertFalse(self.admits(str(self.script)))
        with self.assertRaises(ValueError):
            runtime.register_script(self.state, path='relative', remove=True)

    def test_unreadable_registry_admits_nothing(self):
        path = self.state / 'executive-pilot' / 'registered-scripts.json'
        path.write_text('{"schema_version":1,"scripts":[{"path":"x","sha256":"0"}]}')
        self.assertIsNone(registered_scripts(self.state))
        self.assertFalse(self.admits(str(self.script)))

    def test_operator_cli_registers_and_refuses(self):
        def run(*args):
            return subprocess.run([sys.executable, '-m', 'odin', '--state', str(self.state),
                                   'executive-register-script', *args], capture_output=True, text=True,
                                  env=os.environ | {'PYTHONPATH': str(ROOT / 'python')})
        other = self.bin / 'other.sh'; other.write_text('#!/bin/sh\n')
        done = run('--path', str(other))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(str(other), [s['path'] for s in strict_loads(done.stdout)['registered_scripts']])
        self.assertEqual(run('--path', 'relative.sh').returncode, 2)
        self.assertEqual(run().returncode, 2)
        removed = run('--path', str(other), '--remove')
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertNotIn(str(other), removed.stdout)


class HookLocalPathTests(unittest.TestCase):
    def setUp(self):
        prepared(self)
        self.script = self.temp / 'check.sh'
        self.script.write_text('#!/bin/sh\n'); self.script.chmod(0o700)
        runtime.register_script(self.state, path=str(self.script))

    def decide(self, ev, gateway=unavailable):
        return handle(ev, state=self.state, project=self.project, session=self.native,
                      gateway=gateway, scripts=registered_scripts(self.state))

    def test_read_only_and_script_paths_decide_without_the_service(self):
        for ev, reason in [(event(self, 'git status'), 'Read-only diagnostic allowlist.'),
                           (event(self, f'{self.script} > /tmp/x 2>&1'),
                            'Operator-registered script with matching SHA-256.'),
                           (event(self, tool_input={'command': str(self.script), 'run_in_background': True}),
                            'Operator-registered script with matching SHA-256.')]:
            with self.subTest(command=ev['tool_input']['command']):
                allowed = self.decide(ev)['hookSpecificOutput']
                self.assertEqual(allowed['permissionDecision'], 'allow')
                self.assertEqual(allowed['permissionDecisionReason'], reason)
                self.assertEqual(self.decide(ev | {'hook_event_name': 'PostToolUse'}), {})
                self.assertEqual(self.decide(ev | {'hook_event_name': 'PostToolUseFailure'}), {})

    def test_unmatched_calls_go_to_the_permit_path(self):
        calls = []
        def refuse(command):
            calls.append(command['action']); return {'error': 'refused'}
        for ev in [event(self, 'git log; rm -rf x'), event(self, 'git status', tool_input={
                'command': 'git status', 'run_in_background': True}), event(self, 'make check')]:
            with self.subTest(ev=ev['tool_input']), self.assertRaises(ValueError):
                self.decide(ev, gateway=refuse)
        self.assertEqual(calls, ['intervention_authorize'] * 3)

    def test_audit_records_hold_no_command_text(self):
        secretish = 'synthetic-marker-7c1f'
        commands = [f'grep -rn {secretish} docs', f'{self.script} {secretish}']
        for index, command in enumerate(commands):
            self.decide(event(self, command, tool_use=f'tool-{index}'))
        self.decide(event(self, commands[0], kind='PostToolUse'))
        path = self.state / 'executive-pilot' / AUDIT_FILE
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        raw = path.read_text()
        for fragment in [secretish, 'grep', 'docs', str(self.script), 'tool-0', 'timeout']:
            self.assertNotIn(fragment, raw)
        records = [strict_loads(line) for line in raw.splitlines()]
        self.assertEqual([r['path'] for r in records], ['read_only', 'registered_script'])
        for record in records:
            Contracts().validate('executive-intervention-audit', record)
            self.assertEqual(set(record), {'schema_version', 'time', 'path', 'tool', 'input_digest'})
        with self.assertRaises(ValidationError):
            Contracts().validate('executive-intervention-audit', records[0] | {'command': 'ls'})

    def test_git_never_starts_inside_the_memory_directory(self):
        # The executive writes the memory directory without a permit; a planted
        # git configuration there could name a program for read-only git to run.
        memory = self.temp / 'memory'; (memory / 'sub').mkdir(parents=True)
        runtime.configure_memory_directory(self.state, directory=str(memory))
        configured = str(memory)
        def decide(command, cwd=None):
            ev = event(self, command) | ({'cwd': cwd} if cwd else {})
            return handle(ev, state=self.state, project=self.project, session=self.native,
                          gateway=lambda c: {'error': 'refused'}, memory=configured)
        for command, cwd in [(f'git -C {memory} status', None), (f'git -C {memory}/sub log', None),
                             (f'git -C /tmp -C {memory} status', None), (f'git -C {self.temp} -C memory status', None),
                             ('git status', str(memory)), ('git -C sub status', str(memory)),
                             (f'git -C {memory}/sub/.. diff', None), ('git log', 'relative/cwd')]:
            with self.subTest(command=command, cwd=cwd), self.assertRaises(ValueError):
                decide(command, cwd)
        for command in ['git status', f'git -C {self.temp} status', f'ls {memory}', f'cat {memory}/n.md']:
            with self.subTest(command=command):
                self.assertEqual(decide(command)['hookSpecificOutput']['permissionDecision'], 'allow')
        (memory / '.git').mkdir()
        for target in [memory / '.git' / 'config', memory / '.git', memory / 'sub' / '.GIT']:
            with self.subTest(target=target), self.assertRaises(ValueError):
                handle(event(self, tool='Write', tool_input={'file_path': str(target), 'content': 'x'}),
                       state=self.state, project=self.project, session=self.native,
                       gateway=lambda c: {'error': 'refused'}, memory=configured)

    def test_unwritable_audit_refuses_admission(self):
        path = self.state / 'executive-pilot' / AUDIT_FILE
        os.symlink(self.temp / 'elsewhere', path)
        with self.assertRaises(OSError):
            self.decide(event(self, 'git status'))
        self.assertFalse((self.temp / 'elsewhere').exists())

    def test_hook_process_with_service_unavailable(self):
        # No service runs for this state: the read-only call must still be admitted,
        # and a refused call names the three paths.
        self.assertFalse((self.state / 'executive.sock').exists())
        def run(ev):
            return subprocess.run(
                [sys.executable, '-m', 'odin.executive_intervention_hook', '--state', str(self.state),
                 '--project', self.project, '--session-id', self.native],
                input=json.dumps(ev), capture_output=True, text=True, timeout=30,
                env=os.environ | {'PYTHONPATH': str(ROOT / 'python')})
        allowed = run(event(self, 'git log --oneline -1'))
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual(strict_loads(allowed.stdout)['hookSpecificOutput']['permissionDecision'], 'allow')
        script = run(event(self, str(self.script)))
        self.assertEqual(script.returncode, 0, script.stderr)
        refused = run(event(self, 'git log; rm -rf x'))
        self.assertEqual(refused.returncode, 2)
        self.assertTrue(refused.stderr.startswith(REFUSAL))
        for phrase in ['three admission paths', '(1) Read-only', '(2) An operator-registered script',
                       '(3) An exact permit', 'delegate implementation']:
            self.assertIn(phrase, refused.stderr)
        self.assertNotIn('rm -rf', refused.stderr)


class InterpreterRefusalTests(unittest.TestCase):
    """Item 10: an interpreter or shell is never a registered script."""

    def setUp(self):
        prepared(self)
        self.bin = self.temp / 'bin'; self.bin.mkdir()

    def register(self, path):
        return runtime.register_script(self.state, path=str(path))

    def refused(self, path):
        with self.assertRaises(ValueError) as caught:
            self.register(path)
        self.assertEqual(str(caught.exception), 'script_is_interpreter')

    def test_interpreter_names_with_versions(self):
        for name in ['sh', 'bash', 'zsh', 'fish', 'dash', 'python', 'python3', 'python3.14',
                     'Python3.14t', 'pypy3.10', 'node', 'node22', 'perl', 'perl5.40', 'ruby3.3',
                     'env', 'uv', 'uvx', 'npx', 'npx-cli.js', 'deno', 'bun', 'bunx', 'xargs',
                     'sudo', 'awk', 'busybox']:
            with self.subTest(name=name):
                self.assertTrue(interpreter_name(name))
        for name in ['diagnose.sh', 'check', 'bashful', 'shellcheck', 'python-report',
                     'envoy', 'node-health.py', 'make-check']:
            with self.subTest(name=name):
                self.assertFalse(interpreter_name(name))

    def test_versioned_and_plain_names_refused(self):
        for name in ['python3.14', 'bash', 'perl5.40', 'uvx']:
            path = self.bin / name
            path.write_text('#!/bin/sh\n'); path.chmod(0o700)
            with self.subTest(name=name):
                self.refused(path)

    def test_symlinked_interpreter_refused(self):
        real = Path(os.path.realpath('/bin/sh'))
        link = self.bin / 'diagnose'; os.symlink(real, link)
        self.refused(link)
        self.assertTrue(interpreter(str(link)))

    def test_renamed_copy_of_an_elf_interpreter_refused(self):
        # /usr/bin/env is an ELF interpreter on the standard path; a renamed
        # copy keeps its identity (size and SHA-256).
        source = Path('/usr/bin/env')
        if not source.is_file():
            self.skipTest('no /usr/bin/env on this host')
        copy = self.bin / 'mytool'; copy.write_bytes(source.read_bytes()); copy.chmod(0o700)
        self.assertEqual(copy.read_bytes()[:4], b'\x7fELF')
        self.refused(copy)

    def test_script_with_an_interpreter_shebang_is_allowed(self):
        for name, body in [('diagnose.py', '#!/usr/bin/python3\nprint(1)\n'),
                           ('check.sh', '#!/bin/bash\necho ok\n'),
                           ('report', '#!/usr/bin/env python3\nprint(1)\n')]:
            path = self.bin / name
            path.write_text(body); path.chmod(0o700)
            with self.subTest(name=name):
                self.assertFalse(interpreter(str(path)))
                self.register(path)
        self.assertTrue(registered_script({'command': str(self.bin / 'report')},
                                          scripts=registered_scripts(self.state), state=self.state))

    def test_earlier_registration_of_an_interpreter_is_refused_at_admission(self):
        source = Path('/usr/bin/env')
        if not source.is_file():
            self.skipTest('no /usr/bin/env on this host')
        copy = self.bin / 'mytool'; copy.write_bytes(source.read_bytes()); copy.chmod(0o700)
        # A registry written before the check existed.
        registry = self.state / 'executive-pilot' / 'registered-scripts.json'
        registry.write_text(json.dumps({'schema_version': 1, 'scripts': [
            {'path': str(copy), 'sha256': script_digest(str(copy))}]}))
        registry.chmod(0o600)
        scripts = registered_scripts(self.state)
        self.assertIsNotNone(scripts)
        self.assertFalse(registered_script({'command': f'{copy} ls'}, scripts=scripts, state=self.state))
        calls = []
        def service(command):
            calls.append(command['action'])
            return {'error': 'AccessRefused', 'label': 'x', 'detail': 'intervention_permit_required'}
        with self.assertRaises(ValueError) as caught:
            handle(event(self, f'{copy} ls'), state=self.state, project=self.project,
                   session=self.native, gateway=service, scripts=scripts)
        self.assertEqual(str(caught.exception), 'script_is_interpreter')
        # An exact permit, a separate path, is still asked for first.
        self.assertEqual(calls, ['intervention_authorize'])

    def test_operator_cli_reports_the_code(self):
        path = self.bin / 'bash'; path.write_text('#!/bin/sh\n'); path.chmod(0o700)
        done = subprocess.run([sys.executable, '-m', 'odin', '--state', str(self.state),
                               'executive-register-script', '--path', str(path)],
                              capture_output=True, text=True,
                              env=os.environ | {'PYTHONPATH': str(ROOT / 'python')})
        self.assertEqual(done.returncode, 2)
        self.assertIn('script_is_interpreter', done.stderr)


class RefusalCodeTests(unittest.TestCase):
    """An unmatched call is refused with the service's code, distinct from an
    unreachable service."""

    def setUp(self):
        prepared(self)
        self.service = Service(self.state); self.addCleanup(self.service.close)
        self.gateway = Gateway(self.service)

    def socket_like(self, command):
        # The socket server's own error mapping, without a socket.
        try:
            return submit_executive(self.gateway, {'command': command}, self.project)
        except Exception as error:  # noqa: BLE001 - mirrors the server
            return error_result(error, 'synthetic')

    def code(self, gateway, command='make check'):
        with self.assertRaises(ValueError) as caught:
            handle(event(self, command), state=self.state, project=self.project,
                   session=self.native, gateway=gateway)
        return str(caught.exception)

    def test_no_match_is_not_reported_as_unavailable(self):
        self.assertEqual(self.code(self.socket_like), 'intervention_permit_required')

    def test_unreachable_and_invalid_responses_have_their_own_codes(self):
        def down(command):
            raise ToolFailure('Executive service unavailable.')
        def garbled(command):
            raise ToolFailure('Invalid executive service response.')
        self.assertEqual(self.code(down), 'intervention_service_unreachable')
        self.assertEqual(self.code(garbled), 'intervention_service_response_invalid')
        self.assertEqual(self.code(lambda c: ['not', 'a', 'receipt']), 'intervention_service_response_invalid')
        # A refusal without a fixed code is still a refusal, not unavailability.
        self.assertEqual(self.code(lambda c: {'error': 'ValueError', 'label': 'x'}), 'intervention_not_admitted')
        self.assertEqual(self.code(lambda c: {'error': 'ValueError', 'detail': 'has spaces in it'}),
                         'intervention_not_admitted')

    def test_busy_project_is_relayed(self):
        from unittest.mock import patch
        with patch('odin.executive_intervention._busy', return_value=True):
            self.assertEqual(self.code(self.socket_like), 'delegated_work_active')

    def test_hook_process_reports_unreachable(self):
        refused = subprocess.run(
            [sys.executable, '-m', 'odin.executive_intervention_hook', '--state', str(self.state),
             '--project', self.project, '--session-id', self.native],
            input=json.dumps(event(self, 'make check')), capture_output=True, text=True, timeout=30,
            env=os.environ | {'PYTHONPATH': str(ROOT / 'python')})
        self.assertEqual(refused.returncode, 2)
        self.assertTrue(refused.stderr.rstrip().endswith('Code: intervention_service_unreachable.'))


class RelaxedPermitTests(unittest.TestCase):
    def setUp(self):
        prepared(self)
        self.service = Service(self.state); self.addCleanup(self.service.close)
        self.gateway = Gateway(self.service)
        self.bridge = ExecutiveBridge(self.project, self.send, development_loop=True, session_id=self.native)

    def send(self, command):
        return submit_executive(self.gateway, {'command': command}, self.project)

    def begin(self, calls, ttl=60):
        args = {'operation_id': identifier(), 'purpose': 'Synthetic repair', 'ttl_seconds': ttl, 'calls': calls}
        try:
            return self.bridge.call('odin_intervention_begin', args)
        except ValidationError:
            # The bridge rejects out-of-bounds arguments before dispatch.
            return {'isError': True, 'schema': True}

    def service_refuses(self, calls, ttl=60):
        """The service's own command schema enforces the same bounds."""
        command = {'schema_version': 1, 'operation_id': identifier(), 'action': 'intervention_begin',
                   'payload': {'project': self.project, 'session_id': self.native,
                               'purpose': 'Synthetic repair', 'ttl_seconds': ttl, 'calls': calls}}
        try:
            self.send(command)
        except (ValidationError, ValueError):
            return True
        return False

    def ok(self, result):
        self.assertFalse(result['isError'], result)
        return strict_loads(result['content'][0]['text'])['result']

    def hook(self, ev):
        return handle(ev, state=self.state, project=self.project, session=self.native, gateway=self.send)

    def status(self):
        return self.ok(self.bridge.call('odin_intervention_status', {}))

    def test_lifetime_and_count_bounds(self):
        call = {'tool': 'Bash', 'input': {'command': 'make check'}}
        self.ok(self.begin([call], ttl=3600))
        self.ok(self.bridge.call('odin_intervention_end', {
            'operation_id': identifier(), 'intervention_id': self.status()['intervention']['id']}))
        for ttl in (0, 3601):
            self.assertTrue(self.begin([call], ttl=ttl)['isError'])
            self.assertTrue(self.service_refuses([call], ttl=ttl))
        many = [{'tool': 'Bash', 'input': {'command': f'make check-{i}'}} for i in range(32)]
        item = self.ok(self.begin(many))['intervention']
        self.assertEqual(len(item['permits']), 32)
        self.ok(self.bridge.call('odin_intervention_end', {'operation_id': identifier(), 'intervention_id': item['id']}))
        self.assertTrue(self.begin(many + [call])['isError'])
        self.assertTrue(self.service_refuses(many + [call]))
        for uses in (0, 21):
            self.assertTrue(self.begin([call | {'uses': uses}])['isError'])
            self.assertTrue(self.service_refuses([call | {'uses': uses}]))
        item = self.ok(self.begin([call | {'uses': 20}] * 32))['intervention']
        self.assertEqual(len(item['permits']), 640)

    def test_uses_repeat_an_identical_call(self):
        command = {'command': 'make check', 'timeout': 1000}
        self.ok(self.begin([{'tool': 'Bash', 'input': command, 'uses': 3}]))
        for index in range(3):
            ev = event(self, tool_input=command, tool_use=f'use-{index}')
            self.assertEqual(self.hook(ev)['hookSpecificOutput']['permissionDecision'], 'allow')
            self.assertEqual(self.hook(ev | {'hook_event_name': 'PostToolUse'}), {})
        with self.assertRaises(PermissionError):
            self.hook(event(self, tool_input=command, tool_use='use-3'))
        self.assertEqual(self.status()['intervention']['state'], 'closed')

    def test_background_is_bound_into_the_digest_and_closes_at_launch(self):
        command = {'command': 'make serve', 'timeout': 1000}
        item = self.ok(self.begin([{'tool': 'Bash', 'input': command, 'background': True}]))['intervention']
        self.assertTrue(item['permits'][0]['background'])
        # The same command in the foreground does not match a background permit.
        with self.assertRaises(PermissionError):
            self.hook(event(self, tool_input=command, tool_use='fg'))
        ev = event(self, tool_input=command | {'run_in_background': True}, tool_use='bg')
        self.assertEqual(self.hook(ev)['hookSpecificOutput']['permissionDecision'], 'allow')
        view = self.status()
        self.assertEqual(view['intervention']['permits'][0]['state'], 'launched')
        self.assertEqual(view['intervention']['state'], 'closed')
        self.assertFalse(view['in_flight_unknown'])
        self.assertEqual(view['background_outcome'], 'not_observed_by_odin')
        self.assertIn('does not observe the outcome', view['background_note'])
        delegation_guard(self.service.store, self.project)
        self.assertEqual(self.hook(ev | {'hook_event_name': 'PostToolUse'}), {})
        self.assertEqual(self.status()['intervention']['permits'][0]['state'], 'launched')
        with self.assertRaises(Exception):
            self.hook(ev | {'tool_use_id': 'bg-again'})

    def test_foreground_permit_does_not_admit_background(self):
        command = {'command': 'make serve'}
        self.ok(self.begin([{'tool': 'Bash', 'input': command}]))
        with self.assertRaises(PermissionError):
            self.hook(event(self, tool_input=command | {'run_in_background': True}))
        self.assertNotIn('background_outcome', self.status())

    def test_background_flag_rules(self):
        write = {'tool': 'Write', 'input': {'file_path': '/tmp/x', 'content': 'x'}, 'background': True}
        self.assertTrue(self.begin([write])['isError'])
        implicit = {'tool': 'Bash', 'input': {'command': 'make serve', 'run_in_background': True}}
        self.assertTrue(self.begin([implicit])['isError'])
        sandbox = {'tool': 'Bash', 'input': {'command': 'make', 'dangerouslyDisableSandbox': True}}
        self.assertTrue(self.begin([sandbox])['isError'])
        self.ok(self.begin([{'tool': 'Bash', 'input': {'command': 'make', 'run_in_background': False}}]))

    def test_busy_guard_still_applies_to_permits_not_local_paths(self):
        from unittest.mock import patch
        with patch('odin.executive_intervention._busy', return_value=True):
            self.assertTrue(self.begin([{'tool': 'Bash', 'input': {'command': 'make'}}])['isError'])
            allowed = self.hook(event(self, 'git status'))
            self.assertEqual(allowed['hookSpecificOutput']['permissionDecision'], 'allow')


if __name__ == '__main__':
    unittest.main()
