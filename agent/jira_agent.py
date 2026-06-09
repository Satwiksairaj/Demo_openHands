"""
Jira Agent - Fetches and structures requirements from Jira stories.
Uses MCP Jira server when available, falls back to REST API.
"""
import json
import logging
import re
from typing import Optional

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

REQUIREMENT_EXTRACTION_PROMPT = """You are an expert software requirements analyst.

Given a Jira story with the following details, extract and structure the requirements:

Story ID: {story_id}
Title: {title}
Description: {description}
Acceptance Criteria: {acceptance_criteria}
Comments: {comments}

Return a JSON object with this exact structure:
{{
  "story_id": "<story_id>",
  "title": "<concise title>",
  "type": "<feature|bug|improvement|task>",
  "requirements": ["<requirement 1>", "<requirement 2>", ...],
  "acceptance_criteria": ["<criterion 1>", "<criterion 2>", ...],
  "technical_hints": ["<hint about implementation>", ...],
  "files_to_modify": ["<likely file paths or patterns>", ...],
  "testing_requirements": ["<test 1>", "<test 2>", ...]
}}

Be specific and actionable. Requirements should be implementable by a developer."""


PROMPT_TO_REQUIREMENTS_PROMPT = """You are an expert software requirements analyst.

Convert this natural language prompt into structured development requirements:

Prompt: {prompt}

Return a JSON object with this exact structure:
{{
  "story_id": "{story_id}",
  "title": "<concise feature title>",
  "type": "feature",
  "requirements": ["<requirement 1>", "<requirement 2>", ...],
  "acceptance_criteria": ["<criterion 1>", "<criterion 2>", ...],
  "technical_hints": ["<hint about implementation>", ...],
  "files_to_modify": [],
  "testing_requirements": ["<test 1>", "<test 2>", ...]
}}"""


class JiraAgent:
    """
    Fetches Jira story details and structures them into
    actionable development requirements using Claude.
    """

    def __init__(self, config: dict):
        self.config = config
        self.jira_config = config.get("jira", {})
        self.client = AsyncOpenAI(api_key=config.get("openai_api_key"))
        self.base_url = self.jira_config.get("base_url", "").rstrip("/")
        self.auth = (
            self.jira_config.get("email", ""),
            self.jira_config.get("api_token", "")
        )

    async def fetch_story(self, story_id: str) -> dict:
        """Fetch a Jira story and extract structured requirements."""
        logger.info(f"Fetching Jira story: {story_id}")

        raw = await self._fetch_raw_story(story_id)
        structured = await self._extract_requirements(raw)
        return structured

    async def _fetch_raw_story(self, story_id: str) -> dict:
        """Fetch raw story data from Jira REST API."""
        url = f"{self.base_url}/rest/api/3/issue/{story_id}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, auth=self.auth)
            resp.raise_for_status()
            data = resp.json()

        fields = data.get("fields", {})

        # Extract description text from Atlassian Document Format
        description = self._extract_adf_text(fields.get("description", {}))

        # Extract acceptance criteria (often in custom field or description)
        acceptance_criteria = self._extract_acceptance_criteria(
            fields.get("customfield_10016", {}),
            description
        )

        # Fetch comments
        comments = await self._fetch_comments(story_id)

        return {
            "story_id": story_id,
            "title": fields.get("summary", ""),
            "description": description,
            "acceptance_criteria": acceptance_criteria,
            "issue_type": fields.get("issuetype", {}).get("name", "Story"),
            "priority": fields.get("priority", {}).get("name", "Medium"),
            "labels": fields.get("labels", []),
            "comments": comments,
            "linked_issues": self._extract_linked_issues(fields),
        }

    async def _fetch_comments(self, story_id: str) -> list[str]:
        """Fetch issue comments."""
        url = f"{self.base_url}/rest/api/3/issue/{story_id}/comment"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, auth=self.auth)
                resp.raise_for_status()
                data = resp.json()
            return [
                self._extract_adf_text(c.get("body", {}))
                for c in data.get("comments", [])
            ]
        except Exception as e:
            logger.warning(f"Could not fetch comments: {e}")
            return []

    def _extract_adf_text(self, adf: dict) -> str:
        """Extract plain text from Atlassian Document Format."""
        if not adf or not isinstance(adf, dict):
            return str(adf) if adf else ""

        texts = []
        if adf.get("type") == "text":
            texts.append(adf.get("text", ""))
        for child in adf.get("content", []):
            texts.append(self._extract_adf_text(child))
        return " ".join(filter(None, texts)).strip()

    def _extract_acceptance_criteria(self, custom_field: dict, description: str) -> str:
        """Extract acceptance criteria from custom field or description."""
        if custom_field:
            return self._extract_adf_text(custom_field)

        # Try to find in description
        patterns = [
            r"acceptance criteria[:\n]+(.*?)(?=\n\n|\Z)",
            r"ac[:\n]+(.*?)(?=\n\n|\Z)",
            r"done when[:\n]+(.*?)(?=\n\n|\Z)",
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return description

    def _extract_linked_issues(self, fields: dict) -> list[str]:
        """Extract linked issue IDs."""
        links = []
        for link in fields.get("issuelinks", []):
            if "inwardIssue" in link:
                links.append(link["inwardIssue"]["key"])
            if "outwardIssue" in link:
                links.append(link["outwardIssue"]["key"])
        return links

    async def _extract_requirements(self, raw: dict) -> dict:
        """Use LLM to extract structured requirements from raw story data."""
        user_message = REQUIREMENT_EXTRACTION_PROMPT.format(
            story_id=raw["story_id"],
            title=raw["title"],
            description=raw["description"],
            acceptance_criteria=raw["acceptance_criteria"],
            comments="\n".join(raw.get("comments", []))
        )
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_message}],
            temperature=0,
        )

        content = response.choices[0].message.content.strip()
        # Strip markdown code blocks if present
        content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("`")
        return json.loads(content)

    async def parse_prompt(self, prompt: str) -> dict:
        """Parse a natural language prompt into structured requirements."""
        from datetime import datetime, timezone
        story_id = f"PROMPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        user_message = PROMPT_TO_REQUIREMENTS_PROMPT.format(prompt=prompt, story_id=story_id)
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_message}],
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("`")
        return json.loads(content)
