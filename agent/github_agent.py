"""
GitHub Agent - Handles all Git operations and Pull Request creation.
Uses GitPython for local operations and PyGithub for API interactions.
"""

import logging
import subprocess
from datetime import datetime, timezone

# from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GitHubAgent:
    """
    Manages git operations (commit, push, branch) and creates
    Pull Requests via the GitHub API with rich context.
    """

    def __init__(self, config: dict):
        self.config = config
        self.github_config = config.get("github", {})
        self.token = self.github_config.get("token", "")
        self.repo_owner = self.github_config.get("owner", "")
        self.repo_name = self.github_config.get("repo", "")
        self.base_branch = self.github_config.get("base_branch", "main")
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def commit_and_push(self, workspace: str, branch: str, message: str) -> None:
        """Stage all changes, commit, and push to remote."""
        logger.info("Staging all changes...")
        self._run(["git", "add", "--all"], workspace)

        # Check if there are changes to commit
        status = self._run(["git", "status", "--porcelain"], workspace)
        if status.strip():
            logger.info(f"Committing: {message}")
            self._run(["git", "commit", "-m", message], workspace)
        else:
            logger.info("No file changes — creating empty commit to establish branch")
            self._run(["git", "commit", "--allow-empty", "-m", message], workspace)

        logger.info(f"Pushing branch: {branch}")
        self._run(
            ["git", "push", "--set-upstream", "origin", branch, "--force"], workspace
        )

    async def create_pull_request(
        self,
        branch: str,
        story: dict,
        test_results: dict,
        generated_files: list,
        repo_analysis: dict,
    ) -> str:
        """Create a rich Pull Request via GitHub API."""
        story_id = story.get("story_id", "FEATURE")
        title = story.get("title", "Feature implementation")

        pr_title = f"[{story_id}] {title}"
        pr_body = self._build_pr_body(
            story, test_results, generated_files, repo_analysis
        )

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/pulls",
                headers=self.headers,
                json={
                    "title": pr_title,
                    "body": pr_body,
                    "head": branch,
                    "base": self.base_branch,
                    "draft": False,
                },
            )

            # 422 = PR already exists or no commits between branches
            if resp.status_code == 422:
                # err = resp.json()
                resp.json()
                # errors = err.get("errors", [])
                # Check if PR already open for this branch
                existing = await client.get(
                    f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/pulls",
                    headers=self.headers,
                    params={"head": f"{self.repo_owner}:{branch}", "state": "open"},
                )
                existing_prs = existing.json()
                if existing_prs:
                    pr_url = existing_prs[0]["html_url"]
                    logger.info(f"PR already exists: {pr_url}")
                    return pr_url
                # Otherwise surface the original error
                resp.raise_for_status()

            resp.raise_for_status()
            pr_data = resp.json()

        pr_url = pr_data["html_url"]
        pr_number = pr_data["number"]

        # Add labels if possible
        await self._add_labels(pr_number, story)

        logger.info(f"✅ PR #{pr_number} created: {pr_url}")
        return pr_url

    def _build_pr_body(
        self,
        story: dict,
        test_results: dict,
        generated_files: list,
        repo_analysis: dict,
    ) -> str:
        """Build a detailed, structured PR description."""
        story_id = story.get("story_id", "")
        requirements = story.get("requirements", [])
        acceptance_criteria = story.get("acceptance_criteria", [])

        # Test results badge
        if test_results.get("passed"):
            test_badge = "✅ **All tests passing**"
            test_count = test_results.get("test_count", 0)
            test_detail = f"- {test_count} tests executed, 0 failures"
        else:
            test_badge = "❌ **Tests failed**"
            test_detail = f"- {test_results.get('failed_count', '?')} failures"

        # Files changed list
        files_md = (
            "\n".join(f"- `{f}`" for f in generated_files)
            if generated_files
            else "- No files tracked"
        )

        # Requirements list
        req_md = (
            "\n".join(f"- [x] {r}" for r in requirements)
            if requirements
            else "- See story description"
        )

        # Acceptance criteria
        ac_md = (
            "\n".join(f"- [x] {c}" for c in acceptance_criteria)
            if acceptance_criteria
            else "- See story"
        )

        body = f"""## 🤖 Autonomous AI Developer Agent

> This PR was automatically generated by the AI Development Agent.

---

## 📋 Story Reference

| Field | Value |
|-------|-------|
| **Story ID** | `{story_id}` |
| **Title** | {story.get('title', 'N/A')} |
| **Type** | {story.get('type', 'feature')} |
| **Framework** | {repo_analysis.get('framework', 'N/A')} |

---

## ✅ Requirements Implemented

{req_md}

---

## 🎯 Acceptance Criteria

{ac_md}

---

## 🧪 Test Results

{test_badge}

{test_detail}

```
{test_results.get('output', 'No output captured')[-2000:]}
```

---

## 📁 Files Changed

{files_md}

---

## 🏗️ Implementation Notes

- **Architecture**: {repo_analysis.get('architecture', 'N/A')}
- **Language**: {repo_analysis.get('language', 'N/A')}
- **Test Framework**: {repo_analysis.get('test_framework', 'N/A')}
- **Coding Style**: {repo_analysis.get('coding_style', {})}

### Patterns Followed
{chr(10).join(f"- {p}" for p in repo_analysis.get('existing_patterns', []))}

---

*Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC by AI Dev Agent*
*Branch: `{repo_analysis.get('workspace', '').split('/')[-1]}`*
"""
        return body

    async def _add_labels(self, pr_number: int, story: dict) -> None:
        """Add relevant labels to the PR."""
        labels = []
        story_type = story.get("type", "").lower()

        type_labels = {
            "feature": "enhancement",
            "bug": "bug",
            "improvement": "improvement",
            "task": "task",
        }
        if story_type in type_labels:
            labels.append(type_labels[story_type])

        labels.append("ai-generated")

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # First ensure labels exist
                for label in labels:
                    await client.post(
                        f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/labels",
                        headers=self.headers,
                        json={"name": label, "color": "0075ca"},
                    )

                # Add labels to PR
                await client.post(
                    f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}"
                    f"/issues/{pr_number}/labels",
                    headers=self.headers,
                    json={"labels": labels},
                )
        except Exception as e:
            logger.debug(f"Could not add labels: {e}")

    def _run(self, cmd: list, cwd: str) -> str:
        """Run a git command."""
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Git command failed: {' '.join(cmd)}\n"
                f"STDERR: {result.stderr}\n"
                f"STDOUT: {result.stdout}"
            )
        return result.stdout
