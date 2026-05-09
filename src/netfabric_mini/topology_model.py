from __future__ import annotations

import sqlite3
from typing import Any

import networkx as nx

from netfabric_mini.db import query_all


def build_graph(conn: sqlite3.Connection) -> nx.Graph:
    graph = nx.Graph()
    for device in query_all(conn, "devices"):
        graph.add_node(device["id"], **device)

    for link in query_all(conn, "links"):
        if link["status"] != "up":
            continue
        graph.add_edge(
            link["src_device"],
            link["dst_device"],
            id=link["id"],
            src_device=link["src_device"],
            src_interface=link["src_interface"],
            dst_device=link["dst_device"],
            dst_interface=link["dst_interface"],
            weight=link["weight"],
            status=link["status"],
        )
    return graph


def infer_path(conn: sqlite3.Connection, src_device: str, dst_device: str) -> dict[str, Any]:
    graph = build_graph(conn)
    result_id = f"path-{src_device}-to-{dst_device}"
    down_links = [link for link in query_all(conn, "links") if link["status"] == "down"]
    evidence: list[dict[str, str]] = [
        {
            "type": "path_result",
            "id": result_id,
            "description": f"Path inference from {src_device} to {dst_device} used only links with status up.",
        }
    ]

    try:
        path = nx.shortest_path(graph, src_device, dst_device, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        evidence.extend(_link_evidence(down_links))
        explanation = (
            f"No up-link path exists from {src_device} to {dst_device}. "
            "Down links are reported as path evidence, not as a standalone RCA."
        )
        return {
            "reachable": False,
            "src_device": src_device,
            "dst_device": dst_device,
            "path": [],
            "path_links": [],
            "down_links": down_links,
            "explanation": explanation,
            "evidence": evidence,
        }

    path_links = [_edge_to_link(graph, left, right) for left, right in zip(path, path[1:])]
    evidence.extend(
        {
            "type": "link",
            "id": link["id"],
            "description": (
                f"Up link {link['src_device']}:{link['src_interface']} "
                f"to {link['dst_device']}:{link['dst_interface']} is on the inferred path."
            ),
        }
        for link in path_links
    )
    explanation = f"Reachable path found: {' -> '.join(path)}."
    return {
        "reachable": True,
        "src_device": src_device,
        "dst_device": dst_device,
        "path": path,
        "path_links": path_links,
        "down_links": down_links,
        "explanation": explanation,
        "evidence": evidence,
    }


def _edge_to_link(graph: nx.Graph, left: str, right: str) -> dict[str, Any]:
    data = graph.edges[left, right]
    return {
        "id": data["id"],
        "src_device": data["src_device"],
        "src_interface": data["src_interface"],
        "dst_device": data["dst_device"],
        "dst_interface": data["dst_interface"],
        "weight": data["weight"],
        "status": data["status"],
    }


def _link_evidence(links: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "type": "link",
            "id": link["id"],
            "description": (
                f"Down link {link['src_device']}:{link['src_interface']} "
                f"to {link['dst_device']}:{link['dst_interface']} was excluded from path inference."
            ),
        }
        for link in links
    ]

