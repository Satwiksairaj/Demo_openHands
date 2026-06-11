"""
IntentClassifier
Location: agent/intent_classifier.py

Classifies every incoming prompt as either:
  - NEW_PROJECT   → scaffold a brand-new repository
  - ENHANCEMENT   → modify the existing active project
  - AMBIGUOUS     → not enough signal; orchestrator decides

Called as the very first step in orchestrator.py, before any repo work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


class Intent(str, Enum):
    NEW_PROJECT = "NEW_PROJECT"
    ENHANCEMENT = "ENHANCEMENT"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class ClassificationResult:
    intent: Intent
    confidence: float  # 0.0 – 1.0
    project_hint: Optional[str]  # snake_case project name if detectable
    reasoning: str


# ---------------------------------------------------------------------------
# Signal lists
# ---------------------------------------------------------------------------

_NEW_VERBS = [
    r"\bcreate\b",
    r"\bbuild\b",
    r"\bscaffold\b",
    r"\binitiali[sz]e\b",
    r"\binit\b",
    r"\bbootstrap\b",
    r"\bstart\b",
    r"\bgenerate\b",
    r"\bsetup\b",
    r"\bset\s+up\b",
    r"\bmake\b",
    r"\bnew\b",
    r"\blaunch\b",
    r"\bdevelop\b",
]

_NEW_NOUNS = [
    r"\bapp(?:lication)?\b",
    r"\bproject\b",
    r"\bplatform\b",
    r"\bwebsite\b",
    r"\bservice\b",
    r"\bmicroservice\b",
    r"\bapi\b",
    r"\bbackend\b",
    r"\bfrontend\b",
    r"\bsystem\b",
    r"\brepo(?:sitory)?\b",
    r"\bserver\b",
    r"\bportal\b",
    r"\bboilerplate\b",
    r"\btemplate\b",
    r"\bclone\b",
    r"\bstarter\b",
]

_ENH_VERBS = [
    r"\badd\b",
    r"\bimplement\b",
    r"\bfix\b",
    r"\bupdate\b",
    r"\brefactor\b",
    r"\bimprove\b",
    r"\bextend\b",
    r"\bintegrate\b",
    r"\binclude\b",
    r"\bsupport\b",
    r"\benable\b",
    r"\bdebug\b",
    r"\boptimis[ez]\b",
    r"\bmigrate\b",
    r"\bconnect\b",
    r"\bwire\b",
    r"\bwrite\s+tests?\b",
    r"\btest\b",
    r"\bpatch\b",
    r"\bremove\b",
    r"\bdelete\b",
    r"\bdeploy\b",
    r"\bcover\b",
    r"\bsecure\b",
]

_FRAMEWORKS = {
    "flask",
    "django",
    "fastapi",
    "express",
    "nextjs",
    "next.js",
    "react",
    "vue",
    "angular",
    "rails",
    "laravel",
    "spring",
    "gin",
    "fiber",
    "nestjs",
    "svelte",
    "nuxt",
    "hono",
    "fastify",
    "sveltekit",
}


def _any(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _detect_framework(prompt: str) -> Optional[str]:
    low = prompt.lower()
    for fw in _FRAMEWORKS:
        if fw in low:
            return fw
    return None


def _project_slug(prompt: str) -> Optional[str]:
    """
    Try to extract a project name from the prompt and return it as snake_case.
    "Create Flask Task Manager" → "task_manager"
    "Build Ecommerce Platform"  → "ecommerce_platform"
    """
    # Pattern: verb [framework?] <Title Words>
    patterns = [
        r"(?:create|build|scaffold|init(?:iali[sz]e)?|make|start|new|generate|setup)"
        r"\s+(?:\w+\s+)?([A-Z][A-Za-z ]{2,40}?)(?:\s+(?:app|application|platform|project|api|service|system|backend|website))?$",
        r"(?:create|build|scaffold|setup)\s+(?:a\s+)?(?:\w+\s+)?([A-Z][A-Za-z ]+)",
    ]
    for pat in patterns:
        m = re.search(pat, prompt.strip(), re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            slug = re.sub(r"\s+", "_", name.lower())
            slug = re.sub(r"[^a-z0-9_]", "", slug).strip("_")
            if 2 <= len(slug) <= 50:
                return slug
    return None


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


class IntentClassifier:
    """
    Rule-based prompt classifier.  Fast, no LLM call required.
    Upgrade path: call an LLM for AMBIGUOUS cases when needed.
    """

    def classify(
        self,
        prompt: str,
        has_active_project: bool = False,
    ) -> ClassificationResult:

        low = prompt.strip().lower()

        new_verb = _any(low, _NEW_VERBS)
        new_noun = _any(low, _NEW_NOUNS)
        enh_verb = _any(low, _ENH_VERBS)
        framework = _detect_framework(prompt)

        # ── Strong NEW signals ──────────────────────────────────────
        # creation verb + (framework name OR project noun)
        if new_verb and (framework or new_noun):
            return ClassificationResult(
                intent=Intent.NEW_PROJECT,
                confidence=0.93,
                project_hint=_project_slug(prompt),
                reasoning=f"Creation verb + {'framework: ' + framework if framework else 'project noun'}",
            )

        # ── Strong ENHANCEMENT signals ──────────────────────────────
        if enh_verb and has_active_project:
            return ClassificationResult(
                intent=Intent.ENHANCEMENT,
                confidence=0.91,
                project_hint=None,
                reasoning="Enhancement verb + active project exists",
            )

        # ── Enhancement verb but no active project ──────────────────
        if enh_verb and not has_active_project:
            return ClassificationResult(
                intent=Intent.AMBIGUOUS,
                confidence=0.55,
                project_hint=None,
                reasoning="Enhancement verb but no active project",
            )

        # ── Creation verb without strong noun/framework ─────────────
        if new_verb and not (framework or new_noun):
            if has_active_project:
                return ClassificationResult(
                    intent=Intent.ENHANCEMENT,
                    confidence=0.68,
                    project_hint=None,
                    reasoning="Weak creation verb, active project exists → treat as enhancement",
                )
            return ClassificationResult(
                intent=Intent.AMBIGUOUS,
                confidence=0.50,
                project_hint=_project_slug(prompt),
                reasoning="Creation verb without project noun",
            )

        # ── Default fallback ────────────────────────────────────────
        if has_active_project:
            return ClassificationResult(
                intent=Intent.ENHANCEMENT,
                confidence=0.60,
                project_hint=None,
                reasoning="Active project exists — defaulting to enhancement",
            )

        return ClassificationResult(
            intent=Intent.NEW_PROJECT,
            confidence=0.50,
            project_hint=_project_slug(prompt),
            reasoning="No active project — defaulting to new project",
        )
