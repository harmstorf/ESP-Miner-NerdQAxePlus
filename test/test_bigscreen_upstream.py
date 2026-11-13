import unittest
from upstream_candidate import decision

SHA = "a" * 40


def run(conclusion="success", status="completed", sha=SHA):
    return dict(headSha=sha, conclusion=conclusion, status=status)


class CandidateTests(unittest.TestCase):
    def test_missing_build_is_dispatched(self):
        self.assertEqual(decision([], SHA), "retry")

    def test_old_commit_success_does_not_count(self):
        self.assertEqual(decision([run(sha="b" * 40)], SHA), "retry")

    def test_running_build_is_not_duplicated(self):
        self.assertEqual(decision([run("", "in_progress")], SHA), "wait")
        self.assertEqual(decision([run("", "queued")], SHA), "wait")

    def test_success(self):
        self.assertEqual(decision([run()], SHA), "passed")

    def test_failed_run_is_retried_not_reported_as_pass(self):
        self.assertEqual(decision([run("failure")], SHA), "retry")
        self.assertEqual(decision([run("failure"), run()], SHA), "retry")

    def test_repeated_failure_requires_review(self):
        self.assertEqual(decision([run("failure")] * 3, SHA), "blocked")

    def test_successful_retry_clears_block(self):
        self.assertEqual(decision([run()] + [run("failure")] * 3, SHA), "passed")

    def test_invalid_sha_is_rejected(self):
        with self.assertRaises(ValueError):
            decision([], "invalid")
