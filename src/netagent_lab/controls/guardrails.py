from __future__ import annotations


FORBIDDEN_REAL_ACTIONS = ("ssh", "snmp", "netconf", "gnmi", "kubectl", "containerlab", "batfish", "openai", "langchain")
SIM_MUTATIONS = ("link_down", "link_up", "device_down", "device_up", "set_link", "route_withdrawal")
READ_ONLY = ("show", "list", "collect", "monitor", "export", "diff", "state", "validate")


def enforce_no_external_network_access_config() -> dict[str, object]:
    return {
        "external_network_access": False,
        "llm_api_access": False,
        "real_device_access": False,
        "ok": True,
    }


def validate_collector_is_read_only(collector_name: str) -> dict[str, object]:
    unsafe = any(word in collector_name.lower() for word in ("inject", "mutate", "write", "delete", "restart"))
    return {
        "collector": collector_name,
        "read_only": not unsafe,
        "ok": not unsafe,
        "reason": "Collectors must not mutate simulated or real state.",
    }


def classify_sim_action(action_text: str) -> dict[str, object]:
    text = action_text.lower()
    if any(word in text for word in FORBIDDEN_REAL_ACTIONS):
        return {"classification": "forbidden_for_mvp", "allowed": False, "reason": "Real/external integration is forbidden."}
    if any(word in text for word in ("shutdown interface", "delete", "write erase", "configure terminal")):
        return {"classification": "forbidden_for_mvp", "allowed": False, "reason": "Destructive real-world action is forbidden."}
    if any(word in text for word in SIM_MUTATIONS):
        return {"classification": "simulated_mutation_only", "allowed": True, "reason": "Allowed only through SimulationEngine."}
    if any(word in text for word in READ_ONLY):
        return {"classification": "safe_read_only", "allowed": True, "reason": "Read-only simulated operation."}
    return {"classification": "requires_human_review", "allowed": False, "reason": "Ambiguous action."}

