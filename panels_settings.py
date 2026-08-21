"""The single "App settings" screen (center slot) -- connection management
(disconnect per Iguana instance and per licensing portal login) for Iguana
Connector. Split out of panels.py per the same convention as GitLab CI/CD
Connector's / MuleSoft Connector's panels_settings.py.

Per ~/UI_INTERFACE_STANDARD.md: the left sidebar never wraps the connect
form in a Card, and disconnect (never exposed in the sidebar itself) lives
here, one row per connected instance/login. The one secondary "App
settings" button sits LAST at the bottom of the sidebar. The help modal
(its own separate panel, opened from this screen) is the ONLY place
carrying the generation-mismatch warning (Iguana 6 vs IguanaX) -- the
sidebar never repeats it.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers as h


def _instance_row(c: dict) -> ui.UINode:
    label = c.get("title") or c.get("base_url", "")
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Text(c.get("detail", ""), variant="caption"),
        ui.Button(
            "Disconnect", variant="danger", size="sm",
            on_click=ui.Call("disconnect_iguana", {"connection_id": c.get("id")}),
        ),
    ])


def _license_row(c: dict) -> ui.UINode:
    label = c.get("title") or c.get("license_username", "")
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Text("my.interfaceware.com", variant="caption"),
        ui.Button(
            "Disconnect", variant="danger", size="sm",
            on_click=ui.Call("disconnect_license_portal", {"connection_id": c.get("id")}),
        ),
    ])


def _instances_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Stack(direction="v", gap=1, children=[
            ui.Text("Iguana instances", variant="heading"),
            ui.Text("No Iguana instances connected yet.", variant="caption"),
        ])
    children: list[ui.UINode] = [ui.Text("Iguana instances", variant="heading")]
    for i, c in enumerate(connections):
        if i:
            children.append(ui.Divider())
        children.append(_instance_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _licenses_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Stack(direction="v", gap=1, children=[
            ui.Text("Licensing portal logins", variant="heading"),
            ui.Text("No my.interfaceware.com login connected yet.", variant="caption"),
        ])
    children: list[ui.UINode] = [ui.Text("Licensing portal logins", variant="heading")]
    for i, c in enumerate(connections):
        if i:
            children.append(ui.Divider())
        children.append(_license_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


@ext.panel("iguana_settings", slot="center", title="Iguana -- App settings", center_overlay=True)
async def iguana_settings_panel(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    license_connections = await h._load_license_connections(ctx)
    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        ui.Header(text="App settings", level=2, subtitle="Iguana Connector"),
        _instances_section(connections),
        ui.Divider(),
        _licenses_section(license_connections),
        ui.Divider(),
        ui.Button(
            "About this connector", variant="ghost", size="sm",
            on_click=ui.Call("__panel__iguana_help"),
        ),
    ])


@ext.panel("iguana_help", slot="center", title="About Iguana Connector", center_overlay=True)
async def iguana_help_panel(ctx, **kwargs) -> ui.UINode:
    """The one place carrying the generation-mismatch and scope warnings --
    never duplicated in the sidebar. See PREPARATION.md section 1 for the
    full citation trail behind this text."""
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text(
            "This connector talks to the Iguana 6 HTTP API -- the fully "
            "documented, stable management surface for self-hosted Iguana "
            "instances (help.interfaceware.com). Iguana instances running "
            "on the newer IguanaX runtime do not expose an equivalent "
            "public REST API for external management, per iNTERFACEWARE's "
            "own IguanaX documentation -- if your instance is IguanaX-only, "
            "the Channel API calls here will not work against it."
        ),
        ui.Divider(),
        ui.Text(
            "Your administrator username and password are sent as HTTP "
            "Basic Auth on every call, exactly as Iguana's own API expects "
            "-- there is no separate login step."
        ),
        ui.Divider(),
        ui.Text(
            "The licensing portal login (my.interfaceware.com) is a "
            "separate, optional credential pair used only for license API "
            "calls -- you do not need it to manage channels."
        ),
        ui.Divider(),
        ui.Link(
            label="Open iNTERFACEWARE's official Iguana 6 HTTP API reference",
            href="https://help.interfaceware.com/v6/http-api-reference",
        ),
    ])
    return ui.Dialog(
        title="About this connector",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )
