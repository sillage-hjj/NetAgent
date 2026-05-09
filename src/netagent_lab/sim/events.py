from __future__ import annotations


LINK_EVENTS = {
    "link_down",
    "link_up",
    "link_flap",
    "set_link_latency",
    "set_link_loss",
    "set_link_utilization",
    "set_link_errors",
}
DEVICE_EVENTS = {"device_down", "device_up", "set_device_cpu", "set_device_memory"}
INTERFACE_EVENTS = {"interface_down", "interface_up"}
SERVICE_EVENTS = {"service_down", "service_up", "service_degraded"}
ROUTE_EVENTS = {"route_withdrawal", "route_restore"}
SUPPORTED_EVENTS = LINK_EVENTS | DEVICE_EVENTS | INTERFACE_EVENTS | SERVICE_EVENTS | ROUTE_EVENTS


def target_type_for_event(event_type: str) -> str:
    if event_type in LINK_EVENTS:
        return "link"
    if event_type in DEVICE_EVENTS:
        return "device"
    if event_type in INTERFACE_EVENTS:
        return "interface"
    if event_type in SERVICE_EVENTS:
        return "service"
    if event_type in ROUTE_EVENTS:
        return "route_block"
    raise ValueError(f"Unsupported event type: {event_type}")

