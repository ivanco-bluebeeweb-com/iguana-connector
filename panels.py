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

Per Vlad's standing rule: every input carries its own label (a ui.Text
caption above it, since ui.Input itself has no label kwarg), placeholders
are contextually specific, the form container is stretched to the full
width of the left sidebar with its contents stretched to fill it, and no
instructional text duplicates what already lives in the button's help
modal (see panels_settings.py's help modal).

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
                      on_click=ui.Call("__panel__iguana_settings"))


def _instance_connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Form(
            action="connect_iguana",
            submit_label="Connect instance",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Instance base URL", variant="caption"),
                    ui.Input(param_name="base_url",
                             placeholder="https://your-server.example.com:6543"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Administrator username", variant="caption"),
                    ui.Input(param_name="username", placeholder="admin"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Administrator password", variant="caption"),
                    ui.Password(param_name="password",
                                placeholder="Your Iguana administrator password"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Connection label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Production HL7 server"),
                ]),
            ],
        ),
    ])


def _license_connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Form(
            action="connect_license_portal",
            submit_label="Connect licensing portal",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("my.interfaceware.com username", variant="caption"),
                    ui.Input(param_name="license_username",
                             placeholder="Your licensing portal username"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("my.interfaceware.com password", variant="caption"),
                    ui.Password(param_name="license_password",
                                placeholder="Your licensing portal password"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Login label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Company licensing account"),
                ]),
            ],
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


@ext.panel("iguana_connect", slot="left", title="Iguana",
           default_width=320, min_width=260, max_width=420)
async def iguana_connect_panel(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    license_connections = await h._load_license_connections(ctx)

    header = ui.Header(text="Iguana", level=2,
                        subtitle="Manage your Iguana (iNTERFACEWARE) instance from Imperal")

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        _connections_summary(connections, license_connections),
        ui.Divider(),
        _instance_connect_form(),
        ui.Divider(),
        _license_connect_form(),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("iguana_center", slot="center", title="Iguana", icon="🦎", center_overlay=True)
async def iguana_center_panel(ctx, **kwargs) -> ui.UINode:
    """Base center panel -- per UI_INTERFACE_STANDARD.md (2026-08-20).
    This app has no list/detail content of its own to show in the center
    by default (everything lives in the sidebar). MUST carry
    center_overlay=True: per docs.imperal.io/en/concepts/panels, a plain
    slot="center" panel is registered but the Panel app never fetches it
    at session-init without that flag. Text is the shared canonical
    wording -- must stay identical across every app in this situation."""
    return ui.Empty(
        message="Nothing to show here -- this app is managed entirely from the sidebar.",
        icon="👈",
    )
