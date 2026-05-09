from __future__ import annotations

import ipaddress
import sqlite3
from typing import Any


def check_acl(
    conn: sqlite3.Connection,
    src_ip: str,
    dst_ip: str,
    protocol: str,
    port: int,
    path: list[str] | None = None,
) -> dict[str, Any]:
    src_addr = ipaddress.ip_address(src_ip)
    dst_addr = ipaddress.ip_address(dst_ip)
    protocol_normalized = protocol.lower()
    rules = _get_rules(conn)
    devices = path if path is not None else _devices_with_rules(rules)
    evidence: list[dict[str, str]] = []
    first_allow: dict[str, Any] | None = None

    for device in devices:
        device_rules = [rule for rule in rules if rule["device"] == device]
        for rule in device_rules:
            if not _matches(rule, src_addr, dst_addr, protocol_normalized, port):
                continue

            evidence.append(
                {
                    "type": "acl_rule",
                    "id": rule["id"],
                    "description": (
                        f"ACL rule {rule['rule_name']} on {device} matched "
                        f"{protocol_normalized}/{port} from {src_ip} to {dst_ip} "
                        f"with action {rule['action']}."
                    ),
                }
            )
            if rule["action"] == "deny":
                return {
                    "result": "deny",
                    "matched_rule": rule,
                    "checked_devices": devices,
                    "evidence": evidence,
                    "explanation": f"Traffic is denied by {rule['rule_name']} on {device}.",
                }
            if first_allow is None:
                first_allow = rule
            break

    if first_allow is not None:
        explanation = (
            f"No matching deny rule was found. First matching allow was "
            f"{first_allow['rule_name']} on {first_allow['device']}."
        )
        return {
            "result": "allow",
            "matched_rule": first_allow,
            "checked_devices": devices,
            "evidence": evidence,
            "explanation": explanation,
        }

    evidence.append(
        {
            "type": "acl_default",
            "id": "acl-default-allow",
            "description": "No matching ACL deny rule was found; MVP default is allow.",
        }
    )
    return {
        "result": "allow",
        "matched_rule": None,
        "checked_devices": devices,
        "evidence": evidence,
        "explanation": "No matching ACL rule was found; MVP default is allow.",
    }


def _get_rules(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return conn.execute("SELECT * FROM acl_rules ORDER BY rowid").fetchall()


def _devices_with_rules(rules: list[dict[str, Any]]) -> list[str]:
    devices: list[str] = []
    for rule in rules:
        if rule["device"] not in devices:
            devices.append(rule["device"])
    return devices


def _matches(
    rule: dict[str, Any],
    src_addr: ipaddress._BaseAddress,
    dst_addr: ipaddress._BaseAddress,
    protocol: str,
    port: int,
) -> bool:
    return (
        rule["protocol"].lower() == protocol
        and int(rule["port"]) == int(port)
        and src_addr in ipaddress.ip_network(rule["src_prefix"], strict=False)
        and dst_addr in ipaddress.ip_network(rule["dst_prefix"], strict=False)
    )

