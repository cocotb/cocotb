# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Close PRs from new contributors unless they link an assigned issue."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# Let GitHub recognize closing keywords, Markdown, and issue references.
CLOSING_ISSUES_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      closingIssuesReferences(first: 100, after: $endCursor) {
        nodes {
          state
          repository { nameWithOwner }
          assignees(first: 100) { nodes { login } }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""


def main() -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    owner, name = repository.split("/")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    number = event["number"]
    endpoint = f"repos/{repository}/pulls/{number}"
    # Read current state so queued events cannot act on stale labels or PR data.
    pull_request = json.loads(
        subprocess.check_output(["gh", "api", endpoint], text=True)
    )
    if pull_request["state"] != "open" or any(
        label["name"] == "override-requires-issue" for label in pull_request["labels"]
    ):
        return

    author = pull_request["user"]["login"]
    search = json.loads(
        subprocess.check_output(
            [
                "gh",
                "api",
                "search/issues",
                "--method",
                "GET",
                "-f",
                f"q=repo:{repository} is:pr is:merged author:{author}",
                "-F",
                "per_page=1",
            ],
            text=True,
        )
    )
    # API failures must leave the PR open for a maintainer to retry the check.
    if search["incomplete_results"]:
        raise RuntimeError("Merged-PR search was incomplete; leaving the PR open.")
    if search["total_count"] >= 3:
        return

    pages = json.loads(
        subprocess.check_output(
            [
                "gh",
                "api",
                "graphql",
                "--paginate",
                "--slurp",
                "-f",
                f"query={CLOSING_ISSUES_QUERY}",
                "-f",
                f"owner={owner}",
                "-f",
                f"name={name}",
                "-F",
                f"number={number}",
            ],
            text=True,
        )
    )
    for page in pages:
        issues = page["data"]["repository"]["pullRequest"]["closingIssuesReferences"]
        for issue in issues["nodes"]:
            if (
                issue["state"] == "OPEN"
                and issue["repository"]["nameWithOwner"].lower() == repository.lower()
                and any(
                    assignee["login"].lower() == author.lower()
                    for assignee in issue["assignees"]["nodes"]
                )
            ):
                return

    message = (
        "Thanks for your contribution. "
        f"Contributors with fewer than three merged PRs in {repository} must first open or comment on an issue and wait for a maintainer to assign it to them. "
        "The PR description must link that open issue using `Closes #NUMBER`, `Fixes #NUMBER`, or another "
        "[GitHub closing keyword](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue). "
        "Once you are assigned an issue, update the description and reopen this PR.\n\n"
        f"See the [contribution guidelines](https://github.com/{repository}/blob/{event['repository']['default_branch']}/CONTRIBUTING.md)."
    )
    subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repository}/issues/{number}/comments",
            "--input",
            "-",
            "--silent",
        ],
        input=json.dumps({"body": message}),
        text=True,
        check=True,
    )
    subprocess.run(
        ["gh", "api", endpoint, "--method", "PATCH", "-f", "state=closed", "--silent"],
        check=True,
    )


if __name__ == "__main__":
    main()
