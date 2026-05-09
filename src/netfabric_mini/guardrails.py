from __future__ import annotations


SAFE_READ_ONLY_KEYWORDS = (
    "show",
    "check",
    "query",
    "inspect",
    "view",
    "list",
    "get",
    "find",
    "investigate",
)
APPROVAL_KEYWORDS = (
    "restart",
    "reload",
    "clear",
    "bounce",
    "reset session",
)
FORBIDDEN_KEYWORDS = (
    "shutdown",
    "delete",
    "remove",
    "write erase",
    "configure terminal",
    "apply config",
    "change acl",
    "modify acl",
    "disable interface",
)


def classify_action(action_text: str) -> dict[str, object]:
    text = action_text.lower().strip()

    if _contains_any(text, FORBIDDEN_KEYWORDS):
        return {
            "classification": "forbidden_for_mvp",
            "allowed_for_mvp": False,
            "reason": "The action appears to change or delete network state, which is forbidden in this MVP.",
        }

    if _contains_any(text, APPROVAL_KEYWORDS):
        return {
            "classification": "requires_human_approval",
            "allowed_for_mvp": False,
            "reason": "The action could affect network state and requires explicit human approval outside this MVP.",
        }

    if _contains_any(text, SAFE_READ_ONLY_KEYWORDS):
        return {
            "classification": "safe_read_only",
            "allowed_for_mvp": True,
            "reason": "The action is phrased as a read-only investigation or lookup.",
        }

    return {
        "classification": "requires_human_approval",
        "allowed_for_mvp": False,
        "reason": "The action is ambiguous, so the MVP treats it as requiring human approval.",
    }


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)

