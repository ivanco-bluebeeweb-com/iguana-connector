"""Iguana (iNTERFACEWARE) HTTP API client -- thin async wrappers over
ctx.http (never `requests`), same fail()/ProviderError shape as
gitlab_client.py / pagerduty_client.py.

WHY HTTP BASIC AUTH ON EVERY REQUEST, NOT A SESSION TOKEN.

Confirmed by direct reading of help.interfaceware.com/kb/1477 (2026-08-21):
every Iguana 6 HTTP API function (add_channel, get_channel_config, status,
api_query, get_server_config, monitor_query, etc.) is called as
`net.http.post{url='<base_url>/<function>', auth={username=.., password=..}}`
-- i.e. plain HTTP Basic Auth, credentials sent fresh on every call. There
is no login step, no bearer/session token for this surface. This is a
different (older, simpler) auth model than GitLab's PRIVATE-TOKEN header or
PagerDuty's `Token token=` scheme, so it is implemented exactly as
documented rather than assumed to look like either.

WHY base_url IS A REQUIRED CONNECTION FIELD, SAME REASONING AS
gitlab_client.py / uipath / blue-prism / automation-anywhere.

Iguana is a self-hosted product -- the user's own on-premise or private-
cloud instance, commonly on port 6543 (documented default in every sample
URL, e.g. `localhost:6543`). There is no shared cloud host to default to.

WHY THIS CLIENT ONLY TARGETS THE "IGUANA 6" HTTP API SURFACE
(help.interfaceware.com/v6, /web_api/, /kb/1477), NOT "IguanaX".

Confirmed by direct reading of interfaceware.atlassian.net/wiki/spaces/IXB
(2026-08-21/22): IguanaX's own APIs are designed to be called from Lua
*inside* the Translator via `iguana.call()`, or as raw web calls requiring
a `POST /session/login` step whose exact request/response contract is not
published in any human-readable reference page reachable without an
authenticated my.interfaceware.com account -- every attempt to read the
concrete IguanaX HTTP contract page returned only a login-gated or
browser-unsupported stub. Iguana 6's HTTP API, by contrast, is fully and
concretely documented with exact parameter names, HTTP methods and sample
code. Building against IguanaX today would mean guessing an unconfirmed
contract, which the platform's anti-fabrication rules forbid. See
CONNECTOR_DISCOVERY.md section 2 for the full reasoning and the citation
trail; PREPARATION.md documents this as a vendor-side documentation gap,
not a project shortfall, and states the trigger condition for later adding
an IguanaX-specific client once iNTERFACEWARE publishes a concrete public
contract for it.

WHY 401 vs 403 ARE HANDLED DIFFERENTLY, SAME PRINCIPLE AS EVERY OTHER
IMPERAL CONNECTOR'S CLIENT.

A 401 means the base_url/username/password triple itself is not accepted
(wrong URL, wrong credentials, or the instance unreachable at that path).
A 403 means the credentials are valid but the account lacks the required
privilege for that specific operation -- Iguana's own docs are explicit
that add_channel/remove_channel/update_channel/import_project all require
"administrator privileges", while get_channel_config only requires "view
permission" -- a materially different, more specific and more fixable
cause than "wrong credentials", so it must never be reported as such.
"""
from __future__ import annotations

import base64


class ProviderError(Exception):
    """Raised for any Iguana API call that fails, carrying a status_code
    and a human-readable detail so handlers can distinguish 401 (bad
    credentials) from 403 (credentials ok, insufficient privilege)."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Iguana API error {status_code}: {detail}")


def _auth_header(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _check_status(resp, action: str):
    status = getattr(resp, "status_code", None) or getattr(resp, "status", None)
    if status is None or status >= 400:
        detail = ""
        try:
            detail = resp.text if hasattr(resp, "text") else str(resp.body)
        except Exception:
            detail = "(no response body)"
        if status == 401:
            raise ProviderError(401, f"Failed to {action}: credentials not accepted by this Iguana instance.")
        if status == 403:
            raise ProviderError(403, f"Failed to {action}: credentials valid but lack the required privilege for this operation.")
        raise ProviderError(status or 0, f"Failed to {action}: {detail}"[:500])
    try:
        return resp.json()
    except Exception:
        return resp.text if hasattr(resp, "text") else resp


async def _get(ctx, base_url, username, password, path, params=None):
    resp = await ctx.http.get(_url(base_url, path), headers=_auth_header(username, password), params=params or {})
    return resp


async def _post(ctx, base_url, username, password, path, params=None):
    resp = await ctx.http.post(_url(base_url, path), headers=_auth_header(username, password), data=params or {})
    return resp


# ──────────────────────────────────────────────────────────────────────────
# Connection check
# ──────────────────────────────────────────────────────────────────────────

async def check_connection(ctx, base_url: str, username: str, password: str) -> dict:
    """Validate credentials against the cheapest available call --
    current_version (no privilege requirement documented, tiny response)."""
    resp = await _post(ctx, base_url, username, password, "current_version")
    return _check_status(resp, "verify Iguana connection")


# ──────────────────────────────────────────────────────────────────────────
# Channel API
# ──────────────────────────────────────────────────────────────────────────

async def get_status(ctx, base_url, username, password, action="", name="", guid=""):
    params = {}
    if action:
        params["action"] = action
    if guid:
        params["guid"] = guid
    elif name:
        params["name"] = name
    resp = await _post(ctx, base_url, username, password, "status", params)
    return _check_status(resp, "get server/channel status")


async def start_channel(ctx, base_url, username, password, name="", guid=""):
    return await get_status(ctx, base_url, username, password, action="start", name=name, guid=guid)


async def stop_channel(ctx, base_url, username, password, name="", guid=""):
    return await get_status(ctx, base_url, username, password, action="stop", name=name, guid=guid)


async def start_all_channels(ctx, base_url, username, password):
    return await get_status(ctx, base_url, username, password, action="startall")


async def stop_all_channels(ctx, base_url, username, password):
    return await get_status(ctx, base_url, username, password, action="stopall")


async def current_version(ctx, base_url, username, password):
    resp = await _post(ctx, base_url, username, password, "current_version")
    return _check_status(resp, "get current version")


async def get_server_salt(ctx, base_url, username, password):
    resp = await _post(ctx, base_url, username, password, "get_server_salt")
    return _check_status(resp, "get server salt")


async def get_channel_config(ctx, base_url, username, password, name="", guid="", compact="true"):
    params = {"compact": compact}
    if guid:
        params["guid"] = guid
    elif name:
        params["name"] = name
    resp = await _post(ctx, base_url, username, password, "get_channel_config", params)
    return _check_status(resp, "get channel config")


async def get_default_config(ctx, base_url, username, password, source, destination, compact="true"):
    params = {"source": source, "destination": destination, "compact": compact}
    resp = await _post(ctx, base_url, username, password, "get_default_config", params)
    return _check_status(resp, "get default channel config")


async def add_channel(ctx, base_url, username, password, config, compact="true", source_password="", destination_password="", salt=""):
    params = {"config": config, "compact": compact}
    if source_password:
        params["source_password"] = source_password
    if destination_password:
        params["destination_password"] = destination_password
    if salt:
        params["salt"] = salt
    resp = await _post(ctx, base_url, username, password, "add_channel", params)
    return _check_status(resp, "add channel")


async def update_channel(ctx, base_url, username, password, config, compact="true", source_password="", destination_password=""):
    params = {"config": config, "compact": compact}
    if source_password:
        params["source_password"] = source_password
    if destination_password:
        params["destination_password"] = destination_password
    resp = await _post(ctx, base_url, username, password, "update_channel", params)
    return _check_status(resp, "update channel")


async def remove_channel(ctx, base_url, username, password, name="", guid="", compact="true"):
    params = {"compact": compact}
    if guid:
        params["guid"] = guid
    elif name:
        params["name"] = name
    resp = await _post(ctx, base_url, username, password, "remove_channel", params)
    return _check_status(resp, "remove channel")


async def export_project(ctx, base_url, username, password, guid, milestone_name="", sample_data="true"):
    params = {"guid": guid, "sample_data": sample_data}
    if milestone_name:
        params["milestone_name"] = milestone_name
    resp = await _post(ctx, base_url, username, password, "export_project", params)
    return _check_status(resp, "export Translator project")


async def import_project(ctx, base_url, username, password, guid, project_b64, sample_data=""):
    params = {"guid": guid, "project": project_b64}
    if sample_data:
        params["sample_data"] = sample_data
    resp = await _post(ctx, base_url, username, password, "import_project", params)
    return _check_status(resp, "import Translator project")


async def save_project_milestone(ctx, base_url, username, password, guid, milestone_name):
    params = {"guid": guid, "milestone_name": milestone_name}
    resp = await _post(ctx, base_url, username, password, "save_project_milestone", params)
    return _check_status(resp, "save project milestone")


# ──────────────────────────────────────────────────────────────────────────
# Server API (logs / config / performance)
# ──────────────────────────────────────────────────────────────────────────

async def api_query(ctx, base_url, username, password, **filters):
    resp = await _post(ctx, base_url, username, password, "api_query", filters)
    return _check_status(resp, "query Iguana logs")


async def get_server_config(ctx, base_url, username, password):
    resp = await _get(ctx, base_url, username, password, "get_server_config")
    return _check_status(resp, "get server config")


async def monitor_query(ctx, base_url, username, password):
    resp = await _get(ctx, base_url, username, password, "monitor_query")
    return _check_status(resp, "get performance statistics")


# ──────────────────────────────────────────────────────────────────────────
# License API (my.interfaceware.com licensing system -- separate host)
# ──────────────────────────────────────────────────────────────────────────

_LICENSE_HOST = "https://my.interfaceware.com/api"


def extract_session_token(data):
    """Pull the session token out of session.login's response.

    WHY DEFENSIVE, NOT ONE HARD-CODED FIELD NAME: help.interfaceware.com/
    license_api/ (read 2026-08-21) only says the call "Returns: A session
    token ... as JSON" without naming the exact field -- the concrete shape
    is not published. Rather than fabricate one specific key name, this
    tries the common candidates and falls back to a single-value dict or
    the raw response itself, so real-world responses in any of the likely
    shapes still work; PREPARATION.md records this as an assumption to
    verify against a live account before General Availability.
    """
    if isinstance(data, dict):
        for key in ("token", "Token", "session_token", "sessiontoken", "auth_token", "authtoken"):
            if key in data:
                return data[key]
        if len(data) == 1:
            return next(iter(data.values()))
    return data


async def license_login(ctx, license_username, license_password):
    resp = await ctx.http.post(_LICENSE_HOST, data={
        "username": license_username, "password": license_password, "method": "session.login",
    })
    return _check_status(resp, "log in to my.interfaceware.com licensing system")


async def license_list_entitlements(ctx, token):
    resp = await ctx.http.get(_LICENSE_HOST, params={"product": "Iguana", "token": token, "method": "license.listentitlements"})
    return _check_status(resp, "list license entitlements")


async def license_activate(ctx, token, description, entitlement_id, instance_id):
    resp = await ctx.http.post(_LICENSE_HOST, data={
        "product": "Iguana", "token": token, "method": "license.activate",
        "description": description, "entitlementid": entitlement_id, "instanceid": instance_id,
    })
    return _check_status(resp, "activate license")


async def license_list_activations(ctx, token, entitlement_id):
    resp = await ctx.http.post(_LICENSE_HOST, data={
        "product": "Iguana", "token": token, "method": "license.listActivations",
        "entitlementid": entitlement_id,
    })
    return _check_status(resp, "check license activation")


async def license_transfer(ctx, token, description, activation_id, instance_id):
    resp = await ctx.http.post(_LICENSE_HOST, data={
        "product": "Iguana", "token": token, "method": "license.UpdateActivationInfo",
        "description": description, "activationid": activation_id, "instanceid": instance_id,
    })
    return _check_status(resp, "transfer license")


async def get_instance_license_detail(ctx, base_url, username, password):
    resp = await _get(ctx, base_url, username, password, "license/detail")
    return _check_status(resp, "get instance license detail")


async def apply_instance_license(ctx, base_url, username, password, key):
    resp = await _post(ctx, base_url, username, password, "license/update", {"key": key})
    return _check_status(resp, "apply license key to instance")


# ──────────────────────────────────────────────────────────────────────────
# License API convenience wrappers -- do the session.login + token dance
# internally so handlers.py can call these with plain
# license_username/license_password, the same shape as every other
# credential-pair call in this client.
# ──────────────────────────────────────────────────────────────────────────

async def list_entitlements(ctx, license_username, license_password):
    login_data = await license_login(ctx, license_username, license_password)
    token = extract_session_token(login_data)
    return await license_list_entitlements(ctx, token)


async def activate_license(ctx, license_username, license_password, entitlement_id, instance_id, description=""):
    login_data = await license_login(ctx, license_username, license_password)
    token = extract_session_token(login_data)
    return await license_activate(ctx, token, description, entitlement_id, instance_id)


async def check_activation(ctx, license_username, license_password, entitlement_id):
    login_data = await license_login(ctx, license_username, license_password)
    token = extract_session_token(login_data)
    return await license_list_activations(ctx, token, entitlement_id)


async def transfer_license(ctx, license_username, license_password, activation_id, instance_id, description=""):
    login_data = await license_login(ctx, license_username, license_password)
    token = extract_session_token(login_data)
    return await license_transfer(ctx, token, description, activation_id, instance_id)


async def get_license_detail(ctx, base_url, username, password):
    return await get_instance_license_detail(ctx, base_url, username, password)


async def apply_license(ctx, base_url, username, password, key):
    return await apply_instance_license(ctx, base_url, username, password, key)
