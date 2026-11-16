import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import buildpipeline as bp


def run(title, at, status="completed", conclusion="success", url=None):
    return {"display_title": title, "created_at": at, "status": status, "conclusion": conclusion,
            "html_url": url or f"https://github.com/o/r/actions/runs/{at}"}


PUBLISH = run("feat: something", "2026-11-14T04:00:00Z")


class RunSelection(unittest.TestCase):
    def test_no_publish_run_means_no_dev_test(self):
        self.assertIsNone(bp.pick_dev_test([run(bp.TEST_DEV, "2026-11-14T05:00:00Z")], None))

    def test_runs_before_the_publish_run_belong_to_an_older_commit(self):
        runs = [run(bp.TEST_DEV, "2026-11-14T03:59:59Z")]
        self.assertIsNone(bp.pick_dev_test(runs, PUBLISH))

    def test_latest_run_that_was_not_skipped_wins(self):
        runs = [run(bp.TEST_DEV, "2026-11-14T04:01:00Z", conclusion="failure"),
                run(bp.TEST_DEV, "2026-11-14T04:30:00Z", conclusion="success"),
                run(bp.TEST_DEV, "2026-11-14T04:40:00Z", conclusion="skipped"),
                run(bp.TEST_MAIN, "2026-11-14T04:50:00Z", conclusion="failure"),
                run("Test feature on QEMU", "2026-11-14T04:55:00Z", conclusion="failure")]
        self.assertEqual(bp.pick_dev_test(runs, PUBLISH)["created_at"], "2026-11-14T04:30:00Z")

    def test_only_skipped_runs_give_the_first_one(self):
        runs = [run(bp.TEST_DEV, "2026-11-14T04:20:00Z", conclusion="skipped"),
                run(bp.TEST_DEV, "2026-11-14T04:10:00Z", conclusion="skipped")]
        self.assertEqual(bp.pick_dev_test(runs, PUBLISH)["created_at"], "2026-11-14T04:10:00Z")

    def test_running_test_is_selected(self):
        runs = [run(bp.TEST_DEV, "2026-11-14T04:05:00Z", status="in_progress", conclusion=None)]
        self.assertEqual(bp.run_state(bp.pick_dev_test(runs, PUBLISH)), "running")

    def test_latest_main_test(self):
        runs = [run(bp.TEST_MAIN, "2026-11-13T00:00:00Z"), run(bp.TEST_MAIN, "2026-11-14T00:00:00Z", conclusion="failure"),
                run(bp.TEST_DEV, "2026-11-15T00:00:00Z")]
        self.assertEqual(bp.run_state(bp.pick_main_test(runs)), "failed")
        self.assertIsNone(bp.pick_main_test([run(bp.TEST_DEV, "2026-11-15T00:00:00Z")]))


class States(unittest.TestCase):
    def test_run_state(self):
        self.assertEqual(bp.run_state(None), "none")
        self.assertEqual(bp.run_state(run("x", "t", status="queued", conclusion=None)), "queued")
        self.assertEqual(bp.run_state(run("x", "t", conclusion="timed_out")), "failed")
        self.assertEqual(bp.run_state(run("x", "t", conclusion="cancelled")), "cancelled")

    def test_release_group(self):
        self.assertEqual(bp.release_group([]), bp.UNRELEASED)
        self.assertEqual(bp.release_group([{"prerelease": True}]), bp.TESTING)
        self.assertEqual(bp.release_group([{"prerelease": True}, {"prerelease": False}]), bp.STABLE)
        self.assertEqual(bp.release_group([{"prerelease": False, "draft": True}]), bp.UNRELEASED)

    def test_overall_and_next_step(self):
        self.assertEqual(bp.overall("passed", "passed"), "passed")
        self.assertEqual(bp.overall("failed", "none"), "failed")
        self.assertEqual(bp.overall("passed", "queued"), "running")
        self.assertEqual(bp.overall("passed", "cancelled"), "none")
        pr = [{"number": 1}]
        self.assertEqual(bp.next_step(bp.STABLE, "passed", "passed", pr, [], 3), "Merge the open PR to dev once its checks pass")
        self.assertEqual(bp.next_step(bp.STABLE, "passed", "passed", [], pr, 3), "Release owner merges the PR to main")
        self.assertEqual(bp.next_step(bp.TESTING, "passed", "passed", [], pr, 3), "Merge the PR to main")
        self.assertEqual(bp.next_step(bp.STABLE, "passed", "passed", [], [], 2), "Open the PR to main")
        self.assertEqual(bp.next_step(bp.STABLE, "passed", "passed", [], [], 0), "Nothing to promote")
        self.assertEqual(bp.next_step(bp.STABLE, "passed", "failed", [], [], 0), "Fix the failing QEMU test on dev")
        self.assertEqual(bp.next_step(bp.STABLE, "none", "none", [], [], 0), "Run Publish images on the dev commit")


class FakeGitHub:
    """Answers module_row calls from fixture data, without any network."""

    def __init__(self, answers):
        self.answers = answers
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        for prefix, answer in self.answers.items():
            if path.split("?")[0].endswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        return None


class ModuleRow(unittest.TestCase):
    SHA = "a" * 40

    def answers(self):
        return {
            "/actions/workflows/test-module.yml/runs": {"workflow_runs": [
                run(bp.TEST_DEV, "2026-11-14T04:10:00Z", conclusion="failure"), run(bp.TEST_MAIN, "2026-11-13T00:00:00Z")]},
            "/releases": [{"tag_name": "1.0.0-testing.1", "prerelease": True, "html_url": "https://x/r"}],
            "/compare/main...dev": {"ahead_by": 2, "commits": [{"sha": "b" * 40}, {"sha": self.SHA}]},
            "/actions/workflows/publish-images.yml/runs": {"workflow_runs": [dict(PUBLISH, head_sha=self.SHA)]},
            "/pulls": [{"number": 7, "html_url": "https://x/7", "title": "t", "base": {"ref": "main"}, "head": {"ref": "dev"}},
                       {"number": 8, "html_url": "https://x/8", "title": "t", "base": {"ref": "main"}, "head": {"ref": "other"}}],
        }

    def test_row_from_fixture(self):
        gh = FakeGitHub(self.answers())
        row = bp.module_row(gh, "o", {"name": "ns8-demo", "html_url": "https://github.com/o/ns8-demo"})
        self.assertEqual(len(gh.paths), 5)
        self.assertEqual((row["group"], row["dev_sha"], row["dev_ahead_of_main"]), (bp.TESTING, self.SHA, 2))
        self.assertEqual((row["dev_publish"]["status"], row["dev_test"]["status"], row["main_test"]["status"]), ("passed", "failed", "passed"))
        self.assertEqual([p["number"] for p in row["prs_to_main"]], [7])
        self.assertEqual((row["status"], row["next_step"]), ("failed", "Fix the failing QEMU test on dev"))
        self.assertIn("head_sha=" + self.SHA, gh.paths[3])

    def test_repository_without_test_workflow_is_skipped(self):
        self.assertIsNone(bp.module_row(FakeGitHub({}), "o", {"name": "ns8-tool"}))

    def test_api_error_is_recorded_on_the_row(self):
        answers = self.answers()
        answers["/pulls"] = bp.ApiError("HTTP 502 on /pulls")
        row = bp.safe_row(FakeGitHub(answers), "o", {"name": "ns8-demo"})
        self.assertEqual((row["status"], row["error"]), ("error", "HTTP 502 on /pulls"))
        answers["/actions/workflows/test-module.yml/runs"] = bp.ApiError("HTTP 500")
        self.assertEqual(bp.safe_row(FakeGitHub(answers), "o", {"name": "ns8-demo"})["status"], "error")

    def test_candidates_skip_tools_and_archives(self):
        cfg = {"forge_repo": "ns8-genforge", "tools": ["ns8-ui-lib"], "exclude": ["ns8-hidden"]}
        repos = [{"name": n} for n in ("ns8-b", "ns8-A", "ns8-ui-lib", "ns8-genforge", "ns8-hidden", "other")]
        repos.append({"name": "ns8-old", "archived": True})
        self.assertEqual([r["name"] for r in bp.candidates(repos, cfg)], ["ns8-A", "ns8-b"])


if __name__ == "__main__":
    unittest.main()
