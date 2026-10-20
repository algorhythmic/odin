"""Synthetic execution receipts: real subprocesses and git repositories in temp dirs.

No model, credential, live state or private conversation is used. Fixture
"secrets" are placeholder strings that must never appear in a receipt.
"""

import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from odin.contracts import ROOT, canonical, identifier, strict_loads
from odin.development_loop import DevelopmentLoop
from odin.execution_receipt import (
    RECEIPT_NAME,
    ReceiptError,
    main,
    observe_repository,
    reference,
    run,
    validate,
    validate_references,
)
from odin.store import Store
from test_memory import P, project

PY = sys.executable
SESSION = "11111111-1111-4111-8111-111111111111"
GIT_ENV = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "HOME": "/nonexistent",
    "GIT_AUTHOR_NAME": "Synthetic",
    "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
    "GIT_COMMITTER_NAME": "Synthetic",
    "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
}


def git(repo, *arguments):
    return subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=GIT_ENV,
    ).stdout.strip()


def make_repo(root, branch="real-branch"):
    repo = root / "repo"
    repo.mkdir(mode=0o700)
    git(repo, "init", "--quiet", "-b", branch)
    (repo / "tracked.txt").write_text("one\n")
    (repo / ".gitignore").write_text("ignored-secret.txt\n")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "initial")
    return repo


class ExecutionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = make_repo(self.root)
        self.out = self.root / "evidence"

    def run_receipt(self, argv, out=None, **kwargs):
        return run(argv, out=out or self.out, cwd=str(self.repo), **kwargs)

    def test_successful_command_yields_valid_receipt_from_observations(self):
        receipt = self.run_receipt(
            [PY, "-c", "print('ok'); import sys; sys.stderr.write('warn\\n')"],
            binding={"loop_id": identifier(), "stage_id": identifier()},
            label="synthetic success",
        )
        execution, before = receipt["execution"], receipt["repository"]["before"]
        self.assertEqual(execution["exit_status"], 0)
        self.assertTrue(execution["succeeded"])
        self.assertIsNone(execution["uncertainty"])
        self.assertTrue(before["observed"])
        self.assertEqual(before["branch"], "real-branch")
        self.assertFalse(before["detached"])
        self.assertTrue(before["clean"])
        self.assertEqual(before["head"], git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(before["root"], str(self.repo.resolve()))
        self.assertEqual(receipt["command"]["cwd"], str(self.repo.resolve()))
        self.assertEqual(receipt["command"]["executable"], str(Path(PY).resolve()))
        self.assertTrue(
            receipt["command"]["interpreter"]["version"].startswith("Python")
        )
        self.assertFalse(receipt["repository"]["changed_during_run"])
        self.assertEqual(receipt["collector"]["module"], "odin.execution_receipt")
        self.assertEqual(len(receipt["collector"]["source_sha256"]), 64)
        self.assertEqual((self.out / "stdout.log").read_text(), "ok\n")
        self.assertEqual((self.out / "stderr.log").read_text(), "warn\n")
        self.assertEqual(stat.S_IMODE((self.out / RECEIPT_NAME).stat().st_mode), 0o600)
        result = validate(
            self.out / RECEIPT_NAME,
            {
                "head": before["head"],
                "branch": "real-branch",
                "detached": False,
                "clean": True,
                "exit_status": 0,
                "succeeded": True,
                "loop_id": receipt["binding"]["loop_id"],
                "stage_id": receipt["binding"]["stage_id"],
                "root": str(self.repo.resolve()),
            },
            declared_sha256=reference(self.out / RECEIPT_NAME)["sha256"],
        )
        self.assertEqual(result["outcome"], "valid", result)
        self.assertEqual(result["problems"], [])
        self.assertIn("reference_digest", result["checks"])

    def test_failing_command_is_recorded_and_wrapper_does_not_conceal_it(self):
        receipt = self.run_receipt(
            [PY, "-c", "import sys; print('partial'); sys.exit(7)"]
        )
        self.assertEqual(receipt["execution"]["exit_status"], 7)
        self.assertFalse(receipt["execution"]["succeeded"])
        self.assertEqual((self.out / "stdout.log").read_text(), "partial\n")
        result = validate(self.out / RECEIPT_NAME, {"succeeded": True})
        self.assertEqual(result["outcome"], "mismatched")
        self.assertIn(
            "expected succeeded=True but receipt records False", result["problems"]
        )
        # The CLI exit status follows the wrapped command, not the wrapper.
        out = self.root / "cli"
        with self.assertRaises(SystemExit) as stopped:
            sys.exit(
                main(
                    [
                        "run",
                        "--out",
                        str(out),
                        "--cwd",
                        str(self.repo),
                        "--",
                        PY,
                        "-c",
                        "raise SystemExit(5)",
                    ]
                )
            )
        self.assertEqual(stopped.exception.code, 1)
        self.assertEqual(
            strict_loads((out / RECEIPT_NAME).read_text())["execution"]["exit_status"],
            5,
        )

    def test_timeout_and_spawn_failure_are_explicit_uncertainty(self):
        receipt = self.run_receipt([PY, "-c", "import time; time.sleep(30)"], timeout=1)
        self.assertTrue(receipt["execution"]["timed_out"])
        self.assertIsNone(receipt["execution"]["exit_status"])
        self.assertFalse(receipt["execution"]["succeeded"])
        self.assertIn("outcome unknown", receipt["execution"]["uncertainty"])
        missing = self.run_receipt(
            ["/nonexistent/binary-" + identifier()], out=self.root / "spawn"
        )
        self.assertIsNone(missing["command"]["executable"])
        self.assertIn("spawn failed", missing["execution"]["uncertainty"])
        self.assertFalse(missing["execution"]["succeeded"])

    def test_merge_subject_naming_another_branch_is_not_branch_evidence(self):
        # The observed defect: HEAD's merge subject named a branch that was not
        # checked out. The receipt reports the real branch and keeps the subject
        # as informational text only.
        git(self.repo, "checkout", "--quiet", "-b", "feature")
        (self.repo / "feature.txt").write_text("f\n")
        git(self.repo, "add", "feature.txt")
        git(self.repo, "commit", "--quiet", "-m", "feature work")
        git(self.repo, "checkout", "--quiet", "real-branch")
        (self.repo / "tracked.txt").write_text("two\n")
        git(self.repo, "commit", "--quiet", "-am", "real work")
        git(
            self.repo,
            "merge",
            "--quiet",
            "--no-ff",
            "feature",
            "-m",
            "Merge 'feature' into codex/wrong-branch-name",
        )
        observation = observe_repository(self.repo)
        self.assertEqual(observation["branch"], "real-branch")
        self.assertIn("codex/wrong-branch-name", observation["head_subject"])
        self.assertFalse(observation["head_subject_is_branch_evidence"])
        receipt = self.run_receipt([PY, "-c", "pass"])
        result = validate(
            self.out / RECEIPT_NAME, {"branch": "codex/wrong-branch-name"}
        )
        self.assertEqual(result["outcome"], "mismatched")
        self.assertEqual(
            result["problems"],
            [
                "expected branch='codex/wrong-branch-name' but receipt records 'real-branch'"
            ],
        )
        self.assertEqual(
            receipt["repository"]["before"]["head"], git(self.repo, "rev-parse", "HEAD")
        )

    def test_detached_head_is_explicit(self):
        git(self.repo, "checkout", "--quiet", "--detach")
        receipt = self.run_receipt([PY, "-c", "pass"])
        before = receipt["repository"]["before"]
        self.assertIsNone(before["branch"])
        self.assertTrue(before["detached"])
        self.assertEqual(
            validate(self.out / RECEIPT_NAME, {"detached": True})["outcome"], "valid"
        )
        wrong = validate(
            self.out / RECEIPT_NAME, {"detached": False, "branch": "real-branch"}
        )
        self.assertEqual(wrong["outcome"], "mismatched")
        self.assertEqual(len(wrong["problems"]), 2)

    def test_dirty_tree_coverage_identity_and_privacy(self):
        (self.repo / "tracked.txt").write_text("staged change\n")
        git(self.repo, "add", "tracked.txt")
        (self.repo / "tracked.txt").write_text("unstaged change\n")
        (self.repo / "new.txt").write_text("UNTRACKED-FIXTURE-BODY\n")
        (self.repo / "ignored-secret.txt").write_text("IGNORED-FIXTURE-SECRET\n")
        clean_identity = observe_repository(self.repo)
        self.assertFalse(clean_identity["clean"])
        self.assertEqual(
            clean_identity["staged"], [{"status": "M", "path": "tracked.txt"}]
        )
        self.assertEqual(
            clean_identity["unstaged"], [{"status": "M", "path": "tracked.txt"}]
        )
        self.assertEqual([u["path"] for u in clean_identity["untracked"]], ["new.txt"])
        self.assertEqual(len(clean_identity["untracked"][0]["sha256"]), 64)
        self.assertEqual(clean_identity["untracked_coverage"], "complete")
        raw = canonical(clean_identity)
        self.assertNotIn("UNTRACKED-FIXTURE-BODY", raw)
        self.assertNotIn("IGNORED-FIXTURE-SECRET", raw)
        self.assertNotIn("ignored-secret", raw)
        (self.repo / "new.txt").write_text("UNTRACKED-FIXTURE-BODY-2\n")
        self.assertNotEqual(
            observe_repository(self.repo)["worktree_identity"],
            clean_identity["worktree_identity"],
        )
        # A receipt for a run on this tree cannot be validated as a clean run,
        # and a structured claim of cleanliness disagrees with the observation.
        receipt = self.run_receipt(
            [PY, "-c", "pass"],
            binding={"loop_id": identifier(), "stage_id": identifier()},
        )
        self.assertEqual(
            validate(self.out / RECEIPT_NAME, {"clean": True})["outcome"], "mismatched"
        )
        evidence = {
            "receipts": [reference(self.out / RECEIPT_NAME)],
            "claims": {"clean": True, "head": receipt["repository"]["before"]["head"]},
        }
        outcome = validate_references(evidence, expected=dict(receipt["binding"]))
        self.assertEqual(outcome["status"], "mismatched")
        self.assertTrue(any("clean=True" in p for p in outcome["problems"]))

    def test_command_that_modifies_the_tree_is_detected(self):
        receipt = self.run_receipt(
            [PY, "-c", "open('tracked.txt','a').write('mutated\\n')"]
        )
        self.assertTrue(receipt["repository"]["before"]["clean"])
        self.assertFalse(receipt["repository"]["after"]["clean"])
        self.assertTrue(receipt["repository"]["changed_during_run"])
        result = validate(self.out / RECEIPT_NAME)
        self.assertIn("worktree_changed_during_run", result["checks"])
        self.assertTrue(result["changed_during_run"])
        self.assertEqual(result["outcome"], "mismatched")
        self.assertIn("worktree changed during the run", result["problems"][0])

    def test_tampered_missing_and_changed_artifacts_are_explicit_outcomes(self):
        self.run_receipt([PY, "-c", "print('x')"])
        path = self.out / RECEIPT_NAME
        declared = reference(path)["sha256"]
        self.assertEqual(validate(path, declared_sha256=declared)["outcome"], "valid")
        (self.out / "stdout.log").write_text("y\n")
        changed = validate(path)
        self.assertEqual(changed["outcome"], "mismatched")
        self.assertEqual(changed["problems"], ["artifact bytes changed: stdout"])
        (self.out / "stdout.log").unlink()
        self.assertEqual(validate(path)["outcome"], "missing")
        self.assertEqual(validate(path)["problems"], ["artifact missing: stdout"])
        body = strict_loads(path.read_text())
        body["execution"]["exit_status"] = 9
        path.write_text(canonical(body) + "\n")
        edited = validate(path, declared_sha256=declared)
        self.assertEqual(edited["outcome"], "mismatched")
        self.assertEqual(
            edited["problems"],
            ["receipt bytes differ from the declared reference digest"],
        )
        self.assertNotIn("head", edited)  # tampered content is not echoed
        self.assertEqual(edited["sha256"], reference(path)["sha256"])
        path.write_text("{not json")
        self.assertEqual(validate(path)["outcome"], "invalid")
        path.write_text(canonical({"schema_version": 1}) + "\n")
        self.assertEqual(validate(path)["outcome"], "invalid")
        path.chmod(0o644)
        self.assertEqual(validate(path)["outcome"], "invalid")
        self.assertEqual(validate(self.out / "absent.json")["outcome"], "missing")

    def test_incorrect_revision_or_worktree_attribution_is_mismatched(self):
        self.run_receipt([PY, "-c", "pass"])
        (self.root / "elsewhere").mkdir(mode=0o700)
        other = make_repo(self.root / "elsewhere")
        # Identical fixture content can yield an identical commit id within one
        # second; a distinct commit makes the wrong-revision case unambiguous.
        (other / "tracked.txt").write_text("elsewhere\n")
        git(other, "commit", "--quiet", "-am", "diverge")
        wrong = validate(
            self.out / RECEIPT_NAME,
            {"head": git(other, "rev-parse", "HEAD"), "root": str(other.resolve())},
        )
        self.assertEqual(wrong["outcome"], "mismatched")
        self.assertEqual(len(wrong["problems"]), 2)
        # A receipt for another stage cannot be presented as this stage's evidence.
        bound = validate(self.out / RECEIPT_NAME, {"stage_id": identifier()})
        self.assertEqual(bound["outcome"], "mismatched")

    def test_unobserved_repository_never_asserts_a_clean_tree(self):
        plain = self.root / "plain"
        plain.mkdir(mode=0o700)
        receipt = run([PY, "-c", "pass"], out=self.root / "plain-out", cwd=str(plain))
        before = receipt["repository"]["before"]
        self.assertFalse(before["observed"])
        self.assertNotIn("clean", before)
        result = validate(self.root / "plain-out" / RECEIPT_NAME, {"clean": True})
        self.assertEqual(result["outcome"], "mismatched")
        self.assertIn(
            "cannot be checked: repository not observed", result["problems"][0]
        )
        self.assertIsNone(result["clean"])
        self.assertFalse(result["observed"])
        unobserved = validate_references(
            {"receipts": [reference(self.root / "plain-out" / RECEIPT_NAME)]}
        )
        self.assertEqual(unobserved["status"], "validated_unobserved")

    def test_receipt_records_no_environment_values(self):
        sentinel = "FIXTURE-ENV-SECRET-" + identifier()
        os.environ["ODIN_FIXTURE_SECRET"] = sentinel
        self.addCleanup(os.environ.pop, "ODIN_FIXTURE_SECRET", None)
        self.run_receipt([PY, "-c", "import os; print(len(os.environ))"])
        self.assertNotIn(sentinel, (self.out / RECEIPT_NAME).read_text())
        self.assertNotIn("ODIN_FIXTURE_SECRET", (self.out / RECEIPT_NAME).read_text())

    def test_receipts_refuse_the_repository_and_bad_argv(self):
        with self.assertRaises(PermissionError):
            run(
                [PY, "-c", "pass"],
                out=ROOT / ("should-not-exist-" + identifier()),
                cwd=str(self.repo),
            )
        with self.assertRaises(ReceiptError):
            run([], out=self.out)
        with self.assertRaises(ReceiptError):
            reference(self.out / "nothing.json")

    def test_evidence_reference_validation_outcomes(self):
        loop_id, stage_id = identifier(), identifier()
        self.run_receipt(
            [PY, "-c", "pass"], binding={"loop_id": loop_id, "stage_id": stage_id}
        )
        expected = {"loop_id": loop_id, "stage_id": stage_id}
        ref = reference(self.out / RECEIPT_NAME)
        legacy = validate_references({"summary": "older evidence"}, expected=expected)
        self.assertEqual(legacy["status"], "legacy_no_receipt")
        self.assertEqual(
            validate_references("not an object")["status"], "legacy_no_receipt"
        )
        good = validate_references({"receipts": [ref]}, expected=expected)
        self.assertEqual(good["status"], "validated")
        self.assertEqual(good["receipts"][0]["outcome"], "valid")
        self.assertEqual(
            validate_references({"receipts": []}, expected=expected)["status"],
            "missing",
        )
        malformed = validate_references(
            {"receipts": [{"path": "relative"}]}, expected=expected
        )
        self.assertEqual(malformed["status"], "invalid")
        self.assertEqual(
            validate_references({"receipts": [ref], "claims": 3}, expected=expected)[
                "status"
            ],
            "invalid",
        )
        other_stage = validate_references(
            {"receipts": [ref]}, expected={"loop_id": loop_id, "stage_id": identifier()}
        )
        self.assertEqual(other_stage["status"], "mismatched")
        gone = validate_references(
            {"receipts": [ref | {"path": str(self.out / "gone.json")}]},
            expected=expected,
        )
        self.assertEqual(gone["status"], "missing")
        forged = validate_references(
            {"receipts": [ref | {"sha256": "0" * 64}]}, expected=expected
        )
        self.assertEqual(forged["status"], "mismatched")
        claimed = validate_references(
            {"receipts": [ref], "claims": {"exit_status": 1}}, expected=expected
        )
        self.assertEqual(claimed["status"], "mismatched")
        self.assertTrue(good["commands_succeeded"])
        huge = validate_references(
            {"receipts": [ref], "claims": {"head": "x" * 5000}}, expected=expected
        )
        self.assertEqual(huge["status"], "mismatched")
        self.assertTrue(all(len(p) <= 1400 for p in huge["problems"]))
        stale = validate_references(
            {"receipts": [ref]}, expected=expected, not_before="2999-01-01T00:00:00Z"
        )
        self.assertEqual(stale["status"], "mismatched")
        self.assertIn("predates", stale["problems"][0])
        self.assertEqual(len(canonical(good).encode()) < 4096, True)

    def test_failed_command_is_valid_evidence_but_never_success(self):
        self.run_receipt([PY, "-c", "raise SystemExit(3)"])
        outcome = validate_references(
            {"receipts": [reference(self.out / RECEIPT_NAME)]}
        )
        self.assertEqual(outcome["status"], "validated")
        self.assertFalse(outcome["commands_succeeded"])
        self.assertEqual(outcome["receipts"][0]["exit_status"], 3)
        self.assertFalse(outcome["receipts"][0]["succeeded"])

    def test_renames_and_non_ascii_paths_are_observed_exactly(self):
        git(self.repo, "mv", "tracked.txt", "moved name.txt")
        (self.repo / "ünï.txt").write_text("u\n")
        observation = observe_repository(self.repo)
        self.assertEqual(observation["staged"][0]["status"][0], "R")
        self.assertEqual(observation["staged"][0]["from"], "tracked.txt")
        self.assertEqual(observation["staged"][0]["path"], "moved name.txt")
        self.assertEqual(observation["untracked"][0]["path"], "ünï.txt")
        self.assertEqual(len(observation["untracked"][0]["sha256"]), 64)
        self.assertEqual(observation["untracked_coverage"], "complete")
        (self.repo / "ünï.txt").write_text("changed\n")
        self.assertNotEqual(
            observe_repository(self.repo)["untracked_digest"],
            observation["untracked_digest"],
        )

    def test_timeout_kills_the_whole_process_group_before_hashing(self):
        receipt = self.run_receipt(
            ["sh", "-c", "(while true; do echo tick; sleep 0.05; done) & sleep 30"],
            timeout=1,
        )
        self.assertTrue(receipt["execution"]["timed_out"])
        self.assertIn(
            "retained output may be incomplete", receipt["execution"]["uncertainty"]
        )
        stdout = next(a for a in receipt["artifacts"] if a["name"] == "stdout")
        time.sleep(0.5)
        self.assertEqual((self.out / "stdout.log").stat().st_size, stdout["bytes"])
        self.assertEqual(validate(self.out / RECEIPT_NAME)["outcome"], "valid")

    def test_artifact_privacy_and_hash_budget_are_enforced(self):
        self.run_receipt([PY, "-c", "print('x')"])
        (self.out / "stdout.log").chmod(0o644)
        loose = validate(self.out / RECEIPT_NAME)
        self.assertEqual(loose["outcome"], "mismatched")
        self.assertEqual(
            loose["problems"], ["artifact not a private regular file: stdout"]
        )
        (self.out / "stdout.log").chmod(0o600)
        exhausted = validate(self.out / RECEIPT_NAME, hash_budget={"remaining": 0})
        self.assertEqual(exhausted["outcome"], "invalid")
        self.assertIn("hashing budget exceeded", exhausted["problems"][0])

    def test_hand_written_receipt_is_marked_as_not_matching_the_collector(self):
        self.run_receipt([PY, "-c", "pass"])
        path = self.out / RECEIPT_NAME
        body = strict_loads(path.read_text())
        body["collector"]["source_sha256"] = "0" * 64
        path.write_text(canonical(body) + "\n")
        result = validate(path)
        self.assertEqual(result["outcome"], "valid")  # consistent, self-attested
        self.assertFalse(result["collector_matches_validator"])
        fresh = validate_references({"receipts": [reference(path)]})
        self.assertFalse(fresh["receipts"][0]["collector_matches_validator"])

    def test_output_directory_must_be_fresh(self):
        self.run_receipt([PY, "-c", "pass"])
        with self.assertRaises(FileExistsError):
            self.run_receipt([PY, "-c", "pass"])

    def test_cli_dispatch_only_for_a_leading_receipt_action(self):
        from odin.execution_receipt import dispatch_argv

        self.assertEqual(
            dispatch_argv(["receipt-run", "--out", "x", "--", "ls"]),
            ["run", "--out", "x", "--", "ls"],
        )
        self.assertEqual(
            dispatch_argv(["--state", "/s", "receipt-validate", "--receipt", "r"]),
            ["validate", "--receipt", "r"],
        )
        self.assertIsNone(dispatch_argv(["--reason", "receipt-run", "status"]))
        self.assertIsNone(dispatch_argv(["status"]))
        self.assertIsNone(dispatch_argv([]))

    def edit(self, mutate):
        """Rewrite the retained receipt consistently and return a fresh reference."""
        path = self.out / RECEIPT_NAME
        body = strict_loads(path.read_text())
        mutate(body)
        path.write_text(canonical(body) + "\n")
        return reference(path)

    def assert_never_success(self, outcome):
        self.assertNotIn(outcome["status"], ("validated", "validated_unobserved"))
        self.assertIsNot(outcome["commands_succeeded"], True)
        for item in outcome["receipts"]:
            self.assertIsNot(item["succeeded"], True)
            self.assertIsNone(item["clean"])

    def test_contradictory_execution_fields_are_invalid_with_a_fresh_reference(self):
        self.run_receipt([PY, "-c", "raise SystemExit(9)"])
        ref = self.edit(lambda body: body["execution"].__setitem__("succeeded", True))
        outcome = validate_references({"receipts": [ref]})
        self.assertEqual(outcome["status"], "invalid")
        self.assertIn("succeeded disagrees with exit_status", outcome["problems"][0])
        self.assert_never_success(outcome)
        ref = self.edit(
            lambda body: body["execution"].update(exit_status=None, succeeded=False)
        )
        self.assertIn(
            "exit_status is null without",
            validate_references({"receipts": [ref]})["problems"][0],
        )
        ref = self.edit(
            lambda body: body["execution"].update(
                exit_status=0, succeeded=True, finished_at="2000-01-01T00:00:00Z"
            )
        )
        self.assertIn(
            "finished_at precedes started_at",
            validate_references({"receipts": [ref]})["problems"][0],
        )

    def test_missing_or_duplicate_required_outputs_are_invalid(self):
        self.run_receipt([PY, "-c", "print('x')"])
        ref = self.edit(
            lambda body: body["artifacts"].append(dict(body["artifacts"][0]))
        )
        duplicated = validate_references({"receipts": [ref]})
        self.assertEqual(duplicated["status"], "invalid")
        self.assertTrue(
            any("exactly one stdout artifact" in p for p in duplicated["problems"])
        )
        ref = self.edit(lambda body: body.__setitem__("artifacts", []))
        outcome = validate_references({"receipts": [ref]})
        self.assertEqual(outcome["status"], "invalid")
        self.assertTrue(
            any("exactly one stderr artifact" in p for p in outcome["problems"])
        )
        self.assert_never_success(outcome)

    def test_inconsistent_observations_and_change_flags_are_invalid(self):
        self.run_receipt([PY, "-c", "pass"])
        ref = self.edit(
            lambda body: body["repository"]["after"].__setitem__("head", "0" * 40)
        )
        outcome = validate_references({"receipts": [ref]})
        self.assertEqual(outcome["status"], "invalid")
        self.assertTrue(
            any("worktree_identity does not derive" in p for p in outcome["problems"])
        )
        ref = self.edit(
            lambda body: body["repository"].__setitem__("changed_during_run", None)
        )
        self.assertTrue(
            any(
                "changed_during_run disagrees" in p
                for p in validate_references({"receipts": [ref]})["problems"]
            )
        )
        ref = self.edit(
            lambda body: body["repository"]["before"].__setitem__("clean", False)
        )
        self.assertTrue(
            any(
                "clean flag disagrees" in p
                for p in validate_references({"receipts": [ref]})["problems"]
            )
        )
        ref = self.edit(lambda body: body["repository"]["before"].update(branch=None))
        self.assertTrue(
            any(
                "detached flag disagrees" in p
                for p in validate_references({"receipts": [ref]})["problems"]
            )
        )

    def test_failed_post_run_observation_is_uncertain_not_clean(self):
        # The command destroys the repository metadata, so the collector's
        # post-run observation fails for real.
        receipt = self.run_receipt(
            [PY, "-c", "import shutil; shutil.rmtree('.git')"],
            binding={"loop_id": identifier(), "stage_id": identifier()},
        )
        self.assertTrue(receipt["repository"]["before"]["observed"])
        self.assertFalse(receipt["repository"]["after"]["observed"])
        self.assertIsNone(receipt["repository"]["changed_during_run"])
        result = validate(self.out / RECEIPT_NAME, {"clean": True, "succeeded": True})
        self.assertEqual(result["outcome"], "uncertain")
        self.assertTrue(result["observed_before"])
        self.assertFalse(result["observed_after"])
        self.assertTrue(result["after_reason"])
        self.assertTrue(result["clean_before"])
        self.assertIsNone(result["clean"])
        self.assertIn(
            "post-run repository observation unavailable", result["problems"][0]
        )
        outcome = validate_references(
            {"receipts": [reference(self.out / RECEIPT_NAME)]},
            expected=dict(receipt["binding"]),
        )
        self.assertEqual(outcome["status"], "uncertain")
        self.assertTrue(outcome["commands_succeeded"])  # the command did succeed
        self.assertIsNone(outcome["receipts"][0]["clean"])
        self.assertEqual(
            main(["validate", "--receipt", str(self.out / RECEIPT_NAME)]), 1
        )

    def test_untracked_fifo_cannot_block_observation(self):
        os.mkfifo(self.repo / "pipe.fifo")
        self.addCleanup(lambda: (self.repo / "pipe.fifo").unlink(missing_ok=True))
        script = (
            "import json, sys; sys.path.insert(0, %r); "
            "from odin.execution_receipt import _inspect_file, observe_repository; "
            "print(json.dumps({'fifo': _inspect_file(%r, limit=1024)['status'], "
            "'observation': observe_repository(%r)}))"
            % (str(ROOT / "python"), str(self.repo / "pipe.fifo"), str(self.repo))
        )
        # A hard deadline: a blocking open of the writer-less FIFO would hang here.
        completed = subprocess.run(
            [PY, "-c", script], capture_output=True, text=True, timeout=20, check=False
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = strict_loads(completed.stdout)
        self.assertEqual(result["fifo"], "not_regular")
        observation = result["observation"]
        self.assertTrue(observation["observed"])
        for entry in observation["untracked"]:
            if entry["path"] == "pipe.fifo":
                self.assertIsNone(entry["sha256"])
                self.assertEqual(observation["untracked_coverage"], "partial")
        receipt = self.run_receipt([PY, "-c", "pass"], timeout=20)
        self.assertEqual(receipt["execution"]["exit_status"], 0)

    def test_growing_file_is_bounded_and_reported(self):
        from unittest import mock

        from odin.execution_receipt import _inspect_file

        target = self.root / "growing.log"
        target.write_bytes(b"a" * 100)
        target.chmod(0o600)
        real = os.read

        def grows(fd, size):
            chunk = real(fd, size)
            return chunk + b"b" * 50 if chunk else chunk

        with mock.patch("odin.execution_receipt._read", grows):
            self.assertEqual(_inspect_file(target, limit=120)["status"], "too_large")
            self.assertEqual(_inspect_file(target, limit=10_000)["status"], "changed")
        self.assertEqual(_inspect_file(target, limit=99)["status"], "too_large")
        self.assertEqual(_inspect_file(target, limit=100)["status"], "ok")
        # An artifact that grows between the receipt and validation is reported.
        self.run_receipt([PY, "-c", "print('x')"])
        with mock.patch("odin.execution_receipt._read", grows):
            result = validate(self.out / RECEIPT_NAME)
        self.assertEqual(
            result["outcome"], "invalid"
        )  # the receipt bytes themselves changed
        self.assertIn("changed during inspection", result["problems"][0])

    def test_receipt_is_parsed_from_the_hashed_bytes(self):
        from unittest import mock

        self.run_receipt([PY, "-c", "pass"])
        with (
            mock.patch.object(
                Path, "read_bytes", side_effect=AssertionError("reopened")
            ),
            mock.patch.object(
                Path, "read_text", side_effect=AssertionError("reopened")
            ),
        ):
            result = validate(self.out / RECEIPT_NAME)
        self.assertEqual(result["outcome"], "valid")

    def test_cli_summary_never_reports_clean_without_a_post_observation(self):
        out = self.root / "cli-uncertain"
        with self.assertRaises(SystemExit) as stopped:
            sys.exit(
                main(
                    [
                        "run",
                        "--out",
                        str(out),
                        "--cwd",
                        str(self.repo),
                        "--",
                        PY,
                        "-c",
                        "import shutil; shutil.rmtree('.git')",
                    ]
                )
            )
        self.assertEqual(stopped.exception.code, 0)
        summary = strict_loads((out / RECEIPT_NAME).read_text())
        self.assertFalse(summary["repository"]["after"]["observed"])

    def test_cli_validate_reports_outcome_in_exit_status(self):
        self.run_receipt([PY, "-c", "pass"])
        path = str(self.out / RECEIPT_NAME)
        self.assertEqual(main(["validate", "--receipt", path]), 0)
        self.assertEqual(
            main(["validate", "--receipt", path, "--expect", '{"branch":"other"}']), 1
        )
        self.assertEqual(main(["validate", "--receipt", path, "--sha256", "f" * 64]), 1)


class DevelopmentLoopReceiptTests(unittest.TestCase):
    """Receipt references flow through ready and capture into the evaluator packet."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = make_repo(self.root)
        self.store = Store(self.root / "state")
        self.addCleanup(self.store.close)
        self.store.create(project(P, "Development"))
        self.loops = DevelopmentLoop(self.store)
        started = self.loops.start(P, "Receipt objective", SESSION, identifier())
        job = started["job"]
        self.loops.mark_evaluator_started(
            job["loop_id"], job["id"], job["packet_digest"], identifier()
        )
        verdict = {
            "decision": "continue",
            "assessment": "Synthetic",
            "findings": ["fixture"],
            "next_prompt": "Run a receipted command",
            "evidence_refs": [
                {"ref": "fixture:result", "revision": "1", "digest": "a" * 64}
            ],
        }
        self.stage = self.loops.accept_evaluation(
            job["loop_id"], job["id"], job["packet_digest"], verdict, identifier()
        )["stage"]
        self.loops.claim(self.stage["loop_id"], self.stage["id"], SESSION, identifier())

    def finish(self, evidence):
        ready = self.loops.ready(
            self.stage["loop_id"], self.stage["id"], SESSION, evidence, identifier()
        )
        captured = self.loops.capture_stop(
            SESSION, "Done\n" + ready["completion_marker"], identifier()
        )
        self.assertTrue(captured["captured"])
        return ready, captured["job"]["packet"]

    def test_validated_receipt_reaches_the_evaluator_packet(self):
        out = self.root / "evidence"
        receipt = run(
            [PY, "-c", "print('tested')"],
            out=out,
            cwd=str(self.repo),
            binding={"loop_id": self.stage["loop_id"], "stage_id": self.stage["id"]},
        )
        evidence = {
            "receipts": [reference(out / RECEIPT_NAME)],
            "claims": {
                "head": receipt["repository"]["before"]["head"],
                "exit_status": 0,
                "clean": True,
            },
            "summary": "one receipted command",
        }
        ready, packet = self.finish(evidence)
        self.assertEqual(ready["receipt_validation"]["status"], "validated")
        self.assertEqual(packet["receipt_validation"]["status"], "validated")
        self.assertEqual(
            packet["receipt_validation"]["receipts"][0]["binding"]["stage_id"],
            self.stage["id"],
        )
        self.assertEqual(packet["evidence"]["receipts"], evidence["receipts"])
        self.store.contracts.validate("development-loop-packet", packet)
        self.store.contracts.validate(
            "development-loop-stage", self.loops.stage(self.stage["id"])
        )

    def test_legacy_evidence_is_distinct_from_validated(self):
        ready, packet = self.finish({"repository_revision": "prose only"})
        self.assertEqual(ready["receipt_validation"]["status"], "legacy_no_receipt")
        self.assertEqual(packet["receipt_validation"]["status"], "legacy_no_receipt")

    def test_artifact_changed_between_ready_and_capture_is_mismatched_at_capture(self):
        out = self.root / "evidence"
        run(
            [PY, "-c", "print('before')"],
            out=out,
            cwd=str(self.repo),
            binding={"loop_id": self.stage["loop_id"], "stage_id": self.stage["id"]},
        )
        evidence = {"receipts": [reference(out / RECEIPT_NAME)]}
        ready = self.loops.ready(
            self.stage["loop_id"], self.stage["id"], SESSION, evidence, identifier()
        )
        self.assertEqual(ready["receipt_validation"]["status"], "validated")
        (out / "stdout.log").write_text("after\n")
        captured = self.loops.capture_stop(
            SESSION, "Done\n" + ready["completion_marker"], identifier()
        )
        validation = captured["job"]["packet"]["receipt_validation"]
        self.assertEqual(validation["status"], "mismatched")
        self.assertIn("artifact bytes changed: stdout", validation["problems"][0])

    def test_receipt_for_another_stage_or_a_claim_disagreement_is_reported_not_accepted(
        self,
    ):
        out = self.root / "evidence"
        receipt = run(
            [PY, "-c", "raise SystemExit(2)"],
            out=out,
            cwd=str(self.repo),
            binding={"loop_id": self.stage["loop_id"], "stage_id": identifier()},
        )
        evidence = {
            "receipts": [reference(out / RECEIPT_NAME)],
            "claims": {
                "succeeded": True,
                "head": receipt["repository"]["before"]["head"],
            },
        }
        ready, packet = self.finish(evidence)
        self.assertEqual(ready["receipt_validation"]["status"], "mismatched")
        problems = packet["receipt_validation"]["problems"]
        self.assertTrue(any("stage_id" in p for p in problems))
        self.assertTrue(any("succeeded=True" in p for p in problems))

    def test_uncertain_and_invalid_receipts_reach_ready_and_the_packet(self):
        out = self.root / "uncertain"
        run(
            [PY, "-c", "import shutil; shutil.rmtree('.git')"],
            out=out,
            cwd=str(self.repo),
            binding={"loop_id": self.stage["loop_id"], "stage_id": self.stage["id"]},
        )
        evidence = {
            "receipts": [reference(out / RECEIPT_NAME)],
            "claims": {"clean": True},
        }
        ready, packet = self.finish(evidence)
        for validation in (ready["receipt_validation"], packet["receipt_validation"]):
            self.assertEqual(validation["status"], "uncertain")
            self.assertIsNone(validation["receipts"][0]["clean"])
            self.assertFalse(validation["receipts"][0]["observed_after"])
            self.assertTrue(validation["receipts"][0]["observed_before"])
        self.store.contracts.validate("development-loop-packet", packet)

    def test_contradictory_receipt_is_invalid_through_ready_and_capture(self):
        out = self.root / "contradictory"
        run(
            [PY, "-c", "raise SystemExit(4)"],
            out=out,
            cwd=str(self.repo),
            binding={"loop_id": self.stage["loop_id"], "stage_id": self.stage["id"]},
        )
        path = out / RECEIPT_NAME
        body = strict_loads(path.read_text())
        body["execution"]["succeeded"] = True
        path.write_text(canonical(body) + "\n")
        ready, packet = self.finish(
            {"receipts": [reference(path)], "claims": {"succeeded": True}}
        )
        for validation in (ready["receipt_validation"], packet["receipt_validation"]):
            self.assertEqual(validation["status"], "invalid")
            self.assertIsNone(validation["commands_succeeded"])
            self.assertIsNone(validation["receipts"][0]["succeeded"])

    def test_validator_exception_is_recorded_as_invalid_not_raised(self):
        def broken(evidence, *, expected=None, not_before=None):
            raise OSError("disk unavailable")

        self.loops.validate_receipts = staticmethod(broken)
        ready, packet = self.finish({"receipts": []})
        self.assertEqual(ready["receipt_validation"]["status"], "invalid")
        self.assertIn("OSError", packet["receipt_validation"]["problems"][0])

    def test_oversized_or_malformed_validator_output_is_bounded_not_raised(self):
        def oversized(evidence, *, expected=None, not_before=None):
            return {
                "status": "validated",
                "receipts": [],
                "problems": ["p" * 1400] * 60,  # bounded per item, over 64 KiB in total
                "commands_succeeded": True,
            }

        self.loops.validate_receipts = staticmethod(oversized)
        ready, packet = self.finish({"receipts": []})
        self.assertEqual(ready["receipt_validation"]["status"], "invalid")
        self.assertTrue(
            all(len(p) <= 1400 for p in packet["receipt_validation"]["problems"])
        )

    def test_malformed_validator_output_is_recorded_as_invalid(self):
        def malformed(evidence, *, expected=None, not_before=None):
            return {"status": "bogus", "receipts": [], "problems": []}

        self.loops.validate_receipts = staticmethod(malformed)
        _ready, packet = self.finish({"receipts": []})
        self.assertEqual(packet["receipt_validation"]["status"], "invalid")
        self.assertIn("ValidationError", packet["receipt_validation"]["problems"][0])

    def test_receipt_predating_the_stage_is_mismatched(self):
        out = self.root / "evidence"
        run(
            [PY, "-c", "pass"],
            out=out,
            cwd=str(self.repo),
            binding={"loop_id": self.stage["loop_id"], "stage_id": self.stage["id"]},
        )
        path = out / RECEIPT_NAME
        body = strict_loads(path.read_text())
        # Backdate the whole run consistently; only its age is wrong.
        body["execution"]["started_at"] = "2000-01-01T00:00:01Z"
        body["execution"]["finished_at"] = "2000-01-01T00:00:02Z"
        body["repository"]["before"]["observed_at"] = "2000-01-01T00:00:00Z"
        body["repository"]["after"]["observed_at"] = "2000-01-01T00:00:03Z"
        path.write_text(canonical(body) + "\n")
        ready, packet = self.finish({"receipts": [reference(path)]})
        self.assertEqual(ready["receipt_validation"]["status"], "mismatched")
        self.assertTrue(
            any("predates" in p for p in packet["receipt_validation"]["problems"])
        )


class EvaluatorInstructionTests(unittest.TestCase):
    def test_evaluator_prompt_requires_receipt_inspection(self):
        from odin.development_evaluator import EvaluatorRunner

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("state", "login", "workspace"):
                (root / name).mkdir(mode=0o700)
            store = Store(root / "state")
            try:
                store.create(project(P, "Development"))
                runner = EvaluatorRunner(
                    DevelopmentLoop(store),
                    root / "state",
                    {
                        "schema_version": 1,
                        "enabled": True,
                        "harness": "codex",
                        "binary": PY,
                        "workspace": str(root / "workspace"),
                        "config_dir": str(root / "login"),
                        "model": "synthetic",
                        "timeout_seconds": 30,
                    },
                )
                spec = runner._spec({"id": identifier()}, root / "state" / "job")
            finally:
                store.close()
        prompt = spec["argv"][-1]
        for phrase in (
            "packet.receipt_validation",
            "written the file by hand",
            "commands_succeeded is separate",
            "read the retained receipt.json yourself",
            "recompute artifact SHA256 digests independently",
            "legacy_no_receipt evidence as unverified",
            "A JSON success flag",
        ):
            self.assertIn(phrase, prompt)


if __name__ == "__main__":
    unittest.main()
