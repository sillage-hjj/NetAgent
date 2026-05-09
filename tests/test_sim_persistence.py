from netagent_lab.db import (
    get_current_tick,
    get_snapshot,
    init_sim_db,
    initialize_runtime_state,
    insert_sim_event,
    insert_snapshot,
    list_sim_events,
    list_sim_link_states,
    list_snapshots,
    load_topology_from_db,
    set_current_tick,
)
from netagent_lab.sim.schemas import MonitoringSnapshot, SimulationEvent
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_simulation_db_initializes_and_reloads_topology() -> None:
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")

    initialize_runtime_state(conn, topology)

    reloaded = load_topology_from_db(conn)
    assert reloaded.name == topology.name
    assert get_current_tick(conn) == 0


def test_runtime_state_persists() -> None:
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")

    initialize_runtime_state(conn, topology)

    links = list_sim_link_states(conn)
    assert any(link["link_id"] == "link_r1_r2" for link in links)
    assert all(link["oper_state"] == "up" for link in links)


def test_current_tick_can_be_updated() -> None:
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)

    set_current_tick(conn, 3)

    assert get_current_tick(conn) == 3


def test_events_persist_and_reload() -> None:
    conn = init_sim_db(":memory:")
    event = SimulationEvent(
        id="event-0-0001",
        tick=0,
        ts="tick-000000",
        event_type="link_down",
        target_type="link",
        target_id="link_r1_r2",
        severity="critical",
        params={"reason": "fiber_cut"},
        description="link down",
    )

    insert_sim_event(conn, event)

    events = list_sim_events(conn)
    assert events == [event.model_dump(mode="json")]


def test_snapshots_persist_and_aliases_work() -> None:
    conn = init_sim_db(":memory:")
    for index in range(2):
        snapshot = MonitoringSnapshot(
            id=f"snapshot-{index}-0001",
            tick=index,
            ts=f"tick-{index:06d}",
            topology_name="simple_branch_app",
            inventory={},
            devices={},
            interfaces={},
            links={},
            services={},
            probes={},
            paths={},
            alerts=[],
            events_since_previous=[],
        )
        insert_snapshot(conn, snapshot)

    assert [snapshot["id"] for snapshot in list_snapshots(conn)] == ["snapshot-0-0001", "snapshot-1-0001"]
    assert get_snapshot(conn, "latest")["id"] == "snapshot-1-0001"
    assert get_snapshot(conn, "latest-1")["id"] == "snapshot-0-0001"

