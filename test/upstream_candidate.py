"""Decide whether a candidate needs a build; never infer success from existence."""
import json
import re
import sys


def decision(runs, sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid candidate commit")
    matching = [run for run in runs if run["headSha"] == sha]
    if any(run["status"] != "completed" for run in matching):
        return "wait"
    if matching and matching[0]["conclusion"] == "success":
        return "passed"
    if sum(run["conclusion"] not in ("success", "cancelled", "skipped")
           for run in matching) >= 3:
        return "blocked"
    return "retry"


if __name__ == "__main__":
    print(decision(json.load(sys.stdin), sys.argv[1]))
