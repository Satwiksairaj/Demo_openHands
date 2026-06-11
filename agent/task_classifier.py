"""
Task Classifier Agent - Phase 1 of the 14-phase autonomous engineering workflow.

Classifies the incoming request into one of 7 task types with confidence scoring
and reasoning before any code is generated.
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

TASK_TYPES = [
    "NewApplication",
    "FeatureEnhancement",
    "BugFix",
    "Refactoring",
    "PerformanceOptimization",
    "SecurityImprovement",
    "TestGeneration",
]

KEYWORD_SIGNALS: dict[str, list[str]] = {
    "NewApplication": [
        "create",
        "build",
        "new project",
        "new app",
        "from scratch",
        "bootstrap",
        "initialize",
        "start a",
        "generate a",
        "scaffold",
    ],
    "FeatureEnhancement": [
        "add",
        "implement",
        "enhance",
        "extend",
        "integrate",
        "support",
        "dashboard",
        "chart",
        "filter",
        "search",
        "pagination",
    ],
    "BugFix": [
        "fix",
        "bug",
        "broken",
        "error",
        "crash",
        "not working",
        "fails",
        "incorrect",
        "wrong",
        "issue",
        "problem",
    ],
    "Refactoring": [
        "refactor",
        "clean up",
        "restructure",
        "reorganize",
        "decouple",
        "extract",
        "simplify",
        "improve structure",
        "modularize",
    ],
    "PerformanceOptimization": [
        "slow",
        "performance",
        "optimize",
        "cache",
        "speed up",
        "latency",
        "memory",
        "cpu",
        "bottleneck",
        "efficient",
    ],
    "SecurityImprovement": [
        "security",
        "vulnerability",
        "auth",
        "authentication",
        "authorization",
        "csrf",
        "xss",
        "sql injection",
        "encrypt",
        "hash",
        "jwt",
        "oauth",
        "sanitize",
        "validate input",
    ],
    "TestGeneration": [
        "test",
        "tests",
        "unit test",
        "integration test",
        "coverage",
        "pytest",
        "jest",
        "spec",
        "test suite",
    ],
}


@dataclass
class TaskClassification:
    task_type: str
    confidence: float  # 0.0 – 1.0
    reasoning: str
    secondary_type: Optional[str] = None
    secondary_confidence: float = 0.0
    raw_prompt: str = ""


class TaskClassifierAgent:
    """
    Phase 1 — Classifies a Jira story or natural-language request into a
    structured task type with confidence and reasoning.

    Uses a two-tier approach:
    1. Fast keyword heuristic (always runs, zero cost)
    2. LLM confirmation when confidence < 0.75 or ambiguous
    """

    def __init__(self, config: dict):
        self.config = config
        self._api_key = config.get("openai_api_key", os.getenv("OPENAI_API_KEY", ""))

    def classify_heuristic(self, text: str) -> TaskClassification:
        """Fast keyword-based classification, no LLM cost."""
        lower = text.lower()
        scores: dict[str, float] = {}

        for task_type, keywords in KEYWORD_SIGNALS.items():
            hits = [k for k in keywords if k in lower]
            if hits:
                # Score = matched keywords / total keywords, capped at 1.0
                scores[task_type] = min(len(hits) / max(len(keywords) * 0.3, 1), 1.0)

        if not scores:
            return TaskClassification(
                task_type="FeatureEnhancement",
                confidence=0.3,
                reasoning="No strong keyword signals detected. Defaulting to FeatureEnhancement.",
                raw_prompt=text,
            )

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_type, top_score = sorted_scores[0]
        second_type, second_score = (
            sorted_scores[1] if len(sorted_scores) > 1 else (None, 0.0)
        )

        reasoning_parts = [
            f"Keyword signals detected for '{top_type}': "
            + ", ".join(k for k in KEYWORD_SIGNALS[top_type] if k in lower)
        ]
        if second_type and second_score > 0.2:
            reasoning_parts.append(
                f"Secondary signals for '{second_type}': "
                + ", ".join(k for k in KEYWORD_SIGNALS[second_type] if k in lower)
            )

        return TaskClassification(
            task_type=top_type,
            confidence=round(top_score, 2),
            reasoning=" | ".join(reasoning_parts),
            secondary_type=second_type,
            secondary_confidence=round(second_score, 2),
            raw_prompt=text,
        )

    async def classify(self, story_data: dict) -> TaskClassification:
        """
        Full classification: heuristic first, then LLM confirmation if needed.
        """
        title = story_data.get("title", "")
        requirements = " ".join(story_data.get("requirements", []))
        prompt_text = story_data.get("natural_prompt", "")
        full_text = f"{title} {requirements} {prompt_text}".strip()

        heuristic = self.classify_heuristic(full_text)

        # If confidence is high enough, skip LLM call
        if heuristic.confidence >= 0.75:
            logger.info(
                f"Task classified (heuristic): {heuristic.task_type} "
                f"(confidence={heuristic.confidence})"
            )
            return heuristic

        # Low confidence: use LLM for confirmation
        try:
            llm_result = await self._classify_with_llm(story_data, heuristic)
            logger.info(
                f"Task classified (LLM): {llm_result.task_type} "
                f"(confidence={llm_result.confidence})"
            )
            return llm_result
        except Exception as exc:
            logger.warning(f"LLM classification failed, using heuristic: {exc}")
            return heuristic

    async def _classify_with_llm(
        self, story_data: dict, heuristic: TaskClassification
    ) -> TaskClassification:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)

        prompt = f"""You are a senior software architect classifying a software task.

Task Types (choose exactly one):
{chr(10).join(f"- {t}" for t in TASK_TYPES)}

Input:
Title: {story_data.get("title", "")}
Requirements: {json.dumps(story_data.get("requirements", []))}
Acceptance Criteria: {json.dumps(story_data.get("acceptance_criteria", []))}

Heuristic suggestion: {heuristic.task_type} (confidence={heuristic.confidence})

Return JSON only:
{{
  "task_type": "<one of the task types above>",
  "confidence": <0.0 to 1.0>,
  "reasoning": "<1-2 sentence explanation>",
  "secondary_type": "<second most likely type or null>",
  "secondary_confidence": <0.0 to 1.0>
}}"""

        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = (resp.choices[0].message.content or "").strip()
        # content = resp.choices[0].message.content.strip()
        content = re.sub(r"```(?:json)?\n?", "", content).strip().rstrip("`")
        data = json.loads(content)

        return TaskClassification(
            task_type=data.get("task_type", heuristic.task_type),
            confidence=float(data.get("confidence", heuristic.confidence)),
            reasoning=data.get("reasoning", heuristic.reasoning),
            secondary_type=data.get("secondary_type"),
            secondary_confidence=float(data.get("secondary_confidence", 0.0)),
            raw_prompt=heuristic.raw_prompt,
        )

    def format_report(self, classification: TaskClassification) -> str:
        lines = [
            "── PHASE 1: TASK CLASSIFICATION ─────────────────────────",
            f"  Task Type   : {classification.task_type}",
            f"  Confidence  : {classification.confidence:.0%}",
            f"  Reasoning   : {classification.reasoning}",
        ]
        if classification.secondary_type:
            lines.append(
                f"  Secondary   : {classification.secondary_type} "
                f"({classification.secondary_confidence:.0%})"
            )
        lines.append("─────────────────────────────────────────────────────────")
        return "\n".join(lines)
