import pytest

from netfabric_mini.guardrails import classify_action


@pytest.mark.parametrize(
    "action",
    [
        "show interface status",
        "check path from Zurich to App-B",
        "query cpu metrics on r2",
    ],
)
def test_read_only_checks_are_safe(action: str) -> None:
    result = classify_action(action)

    assert result["classification"] == "safe_read_only"
    assert result["allowed_for_mvp"] is True


@pytest.mark.parametrize("action", ["restart r2", "clear bgp session"])
def test_restart_and_clear_require_human_approval(action: str) -> None:
    result = classify_action(action)

    assert result["classification"] == "requires_human_approval"
    assert result["allowed_for_mvp"] is False


@pytest.mark.parametrize(
    "action",
    [
        "shutdown interface eth1",
        "delete acl BLOCK_ZURICH",
        "remove static route",
    ],
)
def test_destructive_actions_are_forbidden(action: str) -> None:
    result = classify_action(action)

    assert result["classification"] == "forbidden_for_mvp"
    assert result["allowed_for_mvp"] is False

