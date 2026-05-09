from pathlib import Path

import pytest
import yaml

from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, list_topologies, load_topology


def test_valid_topologies_load_successfully() -> None:
    names = {item["name"] for item in list_topologies(DEFAULT_TOPOLOGIES_DIR)}

    assert names == {"simple_branch_app", "ring_with_backup", "spine_leaf_mini"}


def test_simple_branch_app_contains_backup_link_and_probe() -> None:
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")

    assert topology.name == "simple_branch_app"
    assert any(link.id == "link_r1_r3_backup" for link in topology.links)
    assert topology.probes[0].target_service == "app_b"


def test_duplicate_device_ids_fail(tmp_path: Path) -> None:
    data = _valid_topology_dict()
    data["devices"].append(data["devices"][0])
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Device ID must be unique"):
        load_topology(path)


def test_invalid_link_endpoint_fails(tmp_path: Path) -> None:
    data = _valid_topology_dict()
    data["links"][0]["endpoint_b"]["interface"] = "missing"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="missing interface"):
        load_topology(path)


def test_invalid_service_device_fails(tmp_path: Path) -> None:
    data = _valid_topology_dict()
    data["services"][0]["device"] = "missing_device"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Service app_b references missing device"):
        load_topology(path)


def test_invalid_probe_target_fails(tmp_path: Path) -> None:
    data = _valid_topology_dict()
    data["probes"][0]["target_service"] = "missing_service"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Probe probe1 references missing target service"):
        load_topology(path)


def _valid_topology_dict() -> dict:
    return {
        "name": "tiny",
        "description": "tiny",
        "version": "1.0",
        "sites": [{"id": "site1", "name": "Site 1"}],
        "devices": [
            {
                "id": "a",
                "hostname": "a",
                "role": "router",
                "site": "site1",
                "vendor": "synthetic",
                "model": "router",
                "management_ip": None,
                "interfaces": [{"id": "eth0", "name": "eth0", "speed_mbps": 1000}],
            },
            {
                "id": "b",
                "hostname": "b",
                "role": "application",
                "site": "site1",
                "vendor": "synthetic",
                "model": "host",
                "management_ip": None,
                "interfaces": [{"id": "eth0", "name": "eth0", "speed_mbps": 1000}],
            },
        ],
        "links": [
            {
                "id": "link_a_b",
                "endpoint_a": {"device": "a", "interface": "eth0"},
                "endpoint_b": {"device": "b", "interface": "eth0"},
                "bandwidth_mbps": 1000,
            }
        ],
        "services": [
            {
                "id": "app_b",
                "name": "App-B",
                "device": "b",
                "ip": "10.2.0.10",
                "protocol": "tcp",
                "port": 443,
            }
        ],
        "probes": [
            {
                "id": "probe1",
                "name": "Probe 1",
                "source_device": "a",
                "target_service": "app_b",
                "protocol": "tcp",
                "port": 443,
            }
        ],
    }

