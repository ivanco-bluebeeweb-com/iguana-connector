"""Panel UI -- connections list/connect form for Iguana Connector.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as GitLab CI/CD
Connector's / MuleSoft Connector's panels.py).

Every section (connections, connect form) is a plain ui.Stack, content
stacked vertically and left-aligned, sections separated by ui.Divider() --
no Card border/background/shadow anywhere in this slot. Disconnect lives
only in the "App settings" screen (panels_settings.py). The one secondary
"App settings" button is always the LAST element at the bottom of the
sidebar.

Per Vlad's standing rule: every input carries its own label (not just a
placeholder), placeholders are contextually specific, the form container
is stretched to the full width of the left sidebar with its contents
stretched to fill it, and no instructional text duplicates what already
lives in the button's help modal (see panels_settings.py's help modal).

TWO SEPARATE CONNECT FORMS, NOT ONE -- because they are genuinely two
different credential pairs against two different hosts (the user's own
Iguana instance vs. my.interfaceware.com's licensing portal); see app.py's
module docstring for the full reasoning.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers as h


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button("App settings", variant="secondary", size="sm",
                      on_click=ui.OpenPanel("iguana_settings"))


def _instance_connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=2, align="stretch", width="100%", children=[
        ui.Text("Connect your Iguana instance", variant="heading"),
        ui.Input(
            label="Instance base URL", name="base_url",
            placeholder="https://your-server.example.com:6543",
            width="100%",
        ),
        ui.Input(
            label="Administrator username", name="username",
            placeholder="admin",
            width="100%",
        ),
        ui.Input(
            label="Administrator password", name="password", input_type="password",
            placeholder="Your Iguana administrator password",
            width="100%",
        ),
        ui.Input(
            label="Connection label (optional)", name="label",
            placeholder="e.g. Production HL7 server",
            width="100%",
        ),
        ui.Button(
            "Connect instance", variant="primary", width="100%",
            on_click=ui.Call("connect_iguana", {
                "base_url": ui.FieldRef("base_url"), "username": ui.FieldRef("username"),
                "password": ui.FieldRef("password"), "label": ui.FieldRef("label"),
            }),
        ),
    ])


def _license_connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=2, align="stretch", width="100%", children=[
        ui.Text("Connect licensing portal (optional)", variant="heading"),
        ui.Input(
            label="my.interfaceware.com username", name="license_username",
            placeholder="Your licensing portal username",
            width="100%",
        ),
        ui.Input(
            label="my.interfaceware.com password", name="license_password", input_type="password",
            placeholder="Your licensing portal password",
            width="100%",
        ),
        ui.Input(
            label="Login label (optional)", name="license_label",
            placeholder="e.g. Company licensing account",
            width="100%",
        ),
        ui.Button(
            "Connect licensing portal", variant="secondary", width="100%",
            on_click=ui.Call("connect_license_portal", {
                "license_username": ui.FieldRef("license_username"),
                "license_password": ui.FieldRef("license_password"),
                "label": ui.FieldRef("license_label"),
            }),
        ),
    ])


def _connections_summary(connections: list[dict], license_connections: list[dict]) -> ui.UINode:
    children: list[ui.UINode] = []
    if connections:
        children.append(ui.Text(f"{len(connections)} Iguana instance(s) connected.", variant="caption"))
    if license_connections:
        children.append(ui.Text(f"{len(license_connections)} licensing portal login(s) connected.", variant="caption"))
    if not children:
        return ui.Text("No connections yet.", variant="caption")
    return ui.Stack(direction="v", gap=1, children=children)


@ext.panel("iguana_connect", slot="left", title="Iguana")
async def iguana_connect_panel(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    license_connections = await h._load_license_connections(ctx)
    return ui.Stack(direction="v", gap=3, align="stretch", width="100%", children=[
        _connections_summary(connections, license_connections),
        ui.Divider(),
        _instance_connect_form(),
        ui.Divider(),
        _license_connect_form(),
        ui.Divider(),
        _settings_button(),
    ])
