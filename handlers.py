"""Chat functions for Iguana Connector: instance connection management,
licensing portal connection management, Channel API (list/status/start/
stop/add/update/remove/export/import channels), Server API (log query,
server config, performance stats), and Tier-3 value-add audit. Built on
iguana_client.py / schemas.py, following the same shape as GitLab CI/CD
Connector's / PagerDuty Connector's handlers.py.
"""
from __future__ import annotations

import base64
import json
import uuid

from imperal_sdk import ActionResult

import iguana_client as ic
from app import ext, chat
from schemas import (
    NoParams,
    ConnectIguanaParams, ProviderConnection, ProviderConnectionList,
    DisconnectIguanaParams, DeleteResult, ConnectionRefParams,
    ConnectLicensePortalParams, DisconnectLicensePortalParams,
    LicensePortalConnection, LicensePortalConnectionList,
    LicenseConnectionRefParams, ListLicensesParams, LicenseEntry, LicenseList,
    ActivateLicenseParams, LicenseActivationResult,
    CheckLicenseActivationParams, TransferLicenseParams,
    GetInstanceLicenseDetailParams, InstanceLicenseDetail,
    ApplyInstanceLicenseParams,
    ChannelRefParams, GetServerStatusParams, ChannelInfo, ServerStatus,
    StartChannelParams, StopChannelParams,
    StartAllChannelsParams, StopAllChannelsParams,
    GetCurrentVersionParams, VersionInfo,
    GetServerSaltParams, ServerSalt,
    GetChannelConfigParams, ChannelConfig,
    GetDefaultConfigParams,
    AddChannelParams, UpdateChannelParams, RemoveChannelParams,
    ExportProjectParams, ProjectExport,
    ImportProjectParams, ImportProjectResult,
    SaveProjectMilestoneParams, MilestoneResult,
    QueryLogsParams, LogEntry, LogQueryResult,
    GetServerConfigParams, ServerConfig,
    GetPerformanceStatsParams, PerformanceStats,
    AuditInstanceParams, IguanaAuditReport,
)

_CONN_SECRET = "iguana_connections"
_LICENSE_SECRET = "iguana_license_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_CONN_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, items: list[dict]) -> None:
    await ctx.secrets.set(_CONN_SECRET, json.dumps(items))


async def _load_license_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_LICENSE_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_license_connections(ctx, items: list[dict]) -> None:
    await ctx.secrets.set(_LICENSE_SECRET, json.dumps(items))


async def _resolve(ctx, connection_id: str = ""):
    """Return (base_url, username, password) for a connection, or None."""
    conns = await _load_connections(ctx)
    if not conns:
        return None
    if connection_id:
        for c in conns:
            if c.get("id") == connection_id:
                return c.get("base_url", ""), c.get("username", ""), c.get("password", "")
        return None
    c = conns[0]
    return c.get("base_url", ""), c.get("username", ""), c.get("password", "")


async def _resolve_license(ctx, connection_id: str = ""):
    conns = await _load_license_connections(ctx)
    if not conns:
        return None
    if connection_id:
        for c in conns:
            if c.get("id") == connection_id:
                return c.get("license_username", ""), c.get("license_password", "")
        return None
    c = conns[0]
    return c.get("license_username", ""), c.get("license_password", "")


def _no_connection() -> ActionResult:
    return ActionResult.error("No Iguana instance connected yet. Use connect_iguana first.")


def _no_license_connection() -> ActionResult:
    return ActionResult.error("No licensing portal login saved yet. Use connect_license_portal first.")


def _fail(exc: Exception) -> ActionResult:
    if isinstance(exc, ic.ProviderError):
        return ActionResult.error(f"Iguana request failed ({exc.status_code}): {exc.detail}")
    return ActionResult.error(f"Iguana request failed: {exc}")


# ──────────────────────────────────────────────────────────────────────────
# Connection management
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "connect_iguana",
    "Connect your Iguana instance by saving its base URL plus an administrator "
    "username/password, after checking they actually work together.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.connect_iguana",
    effects=["iguana.provider.connected"],
    data_model=ProviderConnection,
)
async def connect_iguana(ctx, params: ConnectIguanaParams) -> ActionResult:
    """Connect your Iguana instance by saving its base URL plus an administrator username/password."""
    base_url = (params.base_url or "").strip().rstrip("/")
    if not base_url:
        return ActionResult.error("base_url is required, e.g. https://your-server.example.com:6543")
    if not params.username or not params.password:
        return ActionResult.error("username and password are both required.")
    try:
        version = await ic.current_version(ctx, base_url, params.username, params.password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    conns = await _load_connections(ctx)
    conn_id = str(uuid.uuid4())
    title = params.label or base_url
    detail = f"Iguana {version.get('major', '?')}.{version.get('minor', '?')}.{version.get('build', '?')}"
    conns.append({
        "id": conn_id, "title": title, "detail": detail,
        "base_url": base_url, "username": params.username, "password": params.password,
    })
    await _save_connections(ctx, conns)
    return ActionResult.success(
        ProviderConnection(id=conn_id, title=title, connected=True, detail=detail, base_url=base_url),
        summary=f"Connected to Iguana instance at {base_url}.",
        refresh_panels=["iguana_connect", "iguana_settings"],
    )


@chat.function(
    "disconnect_iguana",
    "Disconnect an Iguana instance: deletes the saved base URL/credentials. "
    "Nothing on the Iguana server itself is changed.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.disconnect_iguana",
    effects=["iguana.provider.disconnected"],
    data_model=DeleteResult,
)
async def disconnect_iguana(ctx, params: DisconnectIguanaParams) -> ActionResult:
    """Disconnect an Iguana instance: deletes the saved base URL/credentials."""
    conns = await _load_connections(ctx)
    if not conns:
        return _no_connection()
    target_id = params.connection_id or conns[0].get("id", "")
    remaining = [c for c in conns if c.get("id") != target_id]
    if len(remaining) == len(conns):
        return ActionResult.error(f"No connection found with id {target_id}.")
    await _save_connections(ctx, remaining)
    return ActionResult.success(
        DeleteResult(deleted=True, id=target_id),
        summary="Iguana instance disconnected.",
        refresh_panels=["iguana_connect", "iguana_settings"],
    )


@chat.function(
    "list_connections",
    "List the connected Iguana instances.",
    action_type="read",
    chain_callable=True,
    data_model=ProviderConnectionList,
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected Iguana instances."""
    conns = await _load_connections(ctx)
    items = [ProviderConnection(id=c.get("id", ""), title=c.get("title", ""), connected=True,
                                 detail=c.get("detail", ""), base_url=c.get("base_url", ""))
             for c in conns]
    return ActionResult.success(ProviderConnectionList(connections=items))


@chat.function(
    "connect_license_portal",
    "Connect your my.interfaceware.com licensing portal login (separate from your "
    "Iguana instance connection), after checking it actually works.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.connect_license_portal",
    effects=["iguana.license_portal.connected"],
    data_model=LicensePortalConnection,
)
async def connect_license_portal(ctx, params: ConnectLicensePortalParams) -> ActionResult:
    """Connect your my.interfaceware.com licensing portal login."""
    if not params.license_username or not params.license_password:
        return ActionResult.error("license_username and license_password are both required.")
    try:
        await ic.license_login(ctx, params.license_username, params.license_password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    conns = await _load_license_connections(ctx)
    conn_id = str(uuid.uuid4())
    title = params.label or params.license_username
    conns.append({
        "id": conn_id, "title": title,
        "license_username": params.license_username, "license_password": params.license_password,
    })
    await _save_license_connections(ctx, conns)
    return ActionResult.success(
        LicensePortalConnection(id=conn_id, title=title, connected=True, detail="my.interfaceware.com"),
        summary="Connected to the Iguana licensing portal.",
        refresh_panels=["iguana_connect", "iguana_settings"],
    )


@chat.function(
    "disconnect_license_portal",
    "Disconnect a licensing portal login: deletes the saved credentials. "
    "Nothing on my.interfaceware.com itself is changed.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.disconnect_license_portal",
    effects=["iguana.license_portal.disconnected"],
    data_model=DeleteResult,
)
async def disconnect_license_portal(ctx, params: DisconnectLicensePortalParams) -> ActionResult:
    """Disconnect a licensing portal login: deletes the saved credentials."""
    conns = await _load_license_connections(ctx)
    if not conns:
        return _no_license_connection()
    target_id = params.connection_id or conns[0].get("id", "")
    remaining = [c for c in conns if c.get("id") != target_id]
    if len(remaining) == len(conns):
        return ActionResult.error(f"No licensing portal connection found with id {target_id}.")
    await _save_license_connections(ctx, remaining)
    return ActionResult.success(
        DeleteResult(deleted=True, id=target_id),
        summary="Licensing portal disconnected.",
        refresh_panels=["iguana_connect", "iguana_settings"],
    )


@chat.function(
    "list_license_connections",
    "List the connected Iguana licensing portal logins.",
    action_type="read",
    chain_callable=True,
    data_model=LicensePortalConnectionList,
)
async def list_license_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected Iguana licensing portal logins."""
    conns = await _load_license_connections(ctx)
    items = [LicensePortalConnection(id=c.get("id", ""), title=c.get("title", ""), connected=True,
                                      detail="my.interfaceware.com")
             for c in conns]
    return ActionResult.success(LicensePortalConnectionList(connections=items))


# ──────────────────────────────────────────────────────────────────────────
# License API (my.interfaceware.com)
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_licenses",
    "List the Iguana license entitlements available on your connected "
    "my.interfaceware.com account.",
    action_type="read",
    chain_callable=True,
    data_model=LicenseList,
)
async def list_licenses(ctx, params: ListLicensesParams) -> ActionResult:
    """List the Iguana license entitlements available on your connected my.interfaceware.com account."""
    resolved = await _resolve_license(ctx, params.connection_id)
    if not resolved:
        return _no_license_connection()
    username, password = resolved
    try:
        data = await ic.list_entitlements(ctx, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    items = [LicenseEntry(entitlement_id=str(e.get("id", "")), description=str(e.get("description", "")), raw=e)
             for e in (data if isinstance(data, list) else data.get("entitlements", []) if isinstance(data, dict) else [])]
    return ActionResult.success(LicenseList(licenses=items))


@chat.function(
    "get_instance_license_detail",
    "Read the license detail (instance id and current license status) of "
    "your connected Iguana instance -- needed before activating a license "
    "against it.",
    action_type="read",
    chain_callable=True,
    data_model=InstanceLicenseDetail,
)
async def get_instance_license_detail(ctx, params: GetInstanceLicenseDetailParams) -> ActionResult:
    """Read the license detail of your connected Iguana instance."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        data = await ic.get_license_detail(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(InstanceLicenseDetail(instance_id=str(data.get("instance_id", "")), raw=data))


@chat.function(
    "activate_license",
    "Activate a license entitlement from your my.interfaceware.com account "
    "against a specific Iguana instance.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.activate_license",
    effects=["iguana.license.activated"],
    data_model=LicenseActivationResult,
)
async def activate_license(ctx, params: ActivateLicenseParams) -> ActionResult:
    """Activate a license entitlement against a specific Iguana instance."""
    resolved = await _resolve_license(ctx, params.connection_id)
    if not resolved:
        return _no_license_connection()
    username, password = resolved
    if not params.entitlement_id or not params.instance_id:
        return ActionResult.error("entitlement_id and instance_id are both required.")
    try:
        data = await ic.activate_license(ctx, username, password, params.entitlement_id, params.instance_id, params.description)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        LicenseActivationResult(activation_id=str(data.get("activation_id", "")), description=params.description, raw=data),
        summary="License activated.",
    )


@chat.function(
    "check_license_activation",
    "Check the activation status of a license entitlement on your "
    "my.interfaceware.com account.",
    action_type="read",
    chain_callable=True,
    data_model=LicenseActivationResult,
)
async def check_license_activation(ctx, params: CheckLicenseActivationParams) -> ActionResult:
    """Check the activation status of a license entitlement."""
    resolved = await _resolve_license(ctx, params.connection_id)
    if not resolved:
        return _no_license_connection()
    username, password = resolved
    if not params.entitlement_id:
        return ActionResult.error("entitlement_id is required.")
    try:
        data = await ic.check_activation(ctx, username, password, params.entitlement_id)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        LicenseActivationResult(activation_id=str(data.get("activation_id", "")), description=str(data.get("description", "")), raw=data)
    )


@chat.function(
    "transfer_license",
    "Transfer an existing license activation from one Iguana instance to "
    "another, after explicit confirmation -- frees the license from an "
    "instance that is no longer being used.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.transfer_license",
    effects=["iguana.license.transferred"],
    data_model=LicenseActivationResult,
)
async def transfer_license(ctx, params: TransferLicenseParams) -> ActionResult:
    """Transfer an existing license activation to a different Iguana instance."""
    resolved = await _resolve_license(ctx, params.connection_id)
    if not resolved:
        return _no_license_connection()
    username, password = resolved
    if not params.activation_id or not params.instance_id:
        return ActionResult.error("activation_id and instance_id are both required.")
    try:
        data = await ic.transfer_license(ctx, username, password, params.activation_id, params.instance_id, params.description)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        LicenseActivationResult(activation_id=str(data.get("activation_id", params.activation_id)), description=params.description, raw=data),
        summary="License transferred.",
    )


@chat.function(
    "apply_instance_license",
    "Apply a license key directly to your connected Iguana instance.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.apply_instance_license",
    effects=["iguana.license.applied"],
    data_model=InstanceLicenseDetail,
)
async def apply_instance_license(ctx, params: ApplyInstanceLicenseParams) -> ActionResult:
    """Apply a license key directly to your connected Iguana instance."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.key:
        return ActionResult.error("key is required.")
    try:
        data = await ic.apply_license(ctx, base_url, username, password, params.key)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        InstanceLicenseDetail(instance_id=str(data.get("instance_id", "")), raw=data),
        summary="License applied to the Iguana instance.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Channel API -- status, start/stop, config, project export/import
# ──────────────────────────────────────────────────────────────────────────


def _channel_info_from(entry: dict) -> ChannelInfo:
    return ChannelInfo(
        name=str(entry.get("name", "")), guid=str(entry.get("guid", "")),
        status=str(entry.get("status", entry.get("state", ""))), raw=entry,
    )


def _extract_channels(data) -> list[dict]:
    if isinstance(data, dict):
        channels = data.get("channels") or data.get("Channels") or data.get("channel") or []
        if isinstance(channels, dict):
            channels = [channels]
        return channels if isinstance(channels, list) else []
    return []


@chat.function(
    "get_server_status",
    "Read the connected Iguana server's own status report -- server info "
    "plus every channel's current status (running/stopped).",
    action_type="read",
    chain_callable=True,
    data_model=ServerStatus,
)
async def get_server_status(ctx, params: GetServerStatusParams) -> ActionResult:
    """Read the connected Iguana server's own status report, plus every channel's current status."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        data = await ic.get_status(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    channels = [_channel_info_from(e) for e in _extract_channels(data)]
    return ActionResult.success(ServerStatus(channels=channels, raw=data if isinstance(data, dict) else {}))


@chat.function(
    "start_channel",
    "Start a channel on the connected Iguana instance by name or guid.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.start_channel",
    effects=["iguana.channel.started"],
    data_model=ChannelInfo,
)
async def start_channel(ctx, params: StartChannelParams) -> ActionResult:
    """Start a channel on the connected Iguana instance by name or guid."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.name and not params.guid:
        return ActionResult.error("name or guid is required.")
    try:
        data = await ic.start_channel(ctx, base_url, username, password, name=params.name, guid=params.guid)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        ChannelInfo(name=params.name, guid=params.guid, status="started", raw=data if isinstance(data, dict) else {}),
        summary=f"Channel {params.name or params.guid} started.",
    )


@chat.function(
    "stop_channel",
    "Stop a channel on the connected Iguana instance by name or guid.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.stop_channel",
    effects=["iguana.channel.stopped"],
    data_model=ChannelInfo,
)
async def stop_channel(ctx, params: StopChannelParams) -> ActionResult:
    """Stop a channel on the connected Iguana instance by name or guid."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.name and not params.guid:
        return ActionResult.error("name or guid is required.")
    try:
        data = await ic.stop_channel(ctx, base_url, username, password, name=params.name, guid=params.guid)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        ChannelInfo(name=params.name, guid=params.guid, status="stopped", raw=data if isinstance(data, dict) else {}),
        summary=f"Channel {params.name or params.guid} stopped.",
    )


@chat.function(
    "start_all_channels",
    "Start every channel on the connected Iguana instance.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.start_all_channels",
    effects=["iguana.channels.started_all"],
    data_model=ServerStatus,
)
async def start_all_channels(ctx, params: StartAllChannelsParams) -> ActionResult:
    """Start every channel on the connected Iguana instance."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        data = await ic.start_all_channels(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    channels = [_channel_info_from(e) for e in _extract_channels(data)]
    return ActionResult.success(
        ServerStatus(channels=channels, raw=data if isinstance(data, dict) else {}),
        summary="All channels started.",
    )


@chat.function(
    "stop_all_channels",
    "Stop every channel on the connected Iguana instance.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.stop_all_channels",
    effects=["iguana.channels.stopped_all"],
    data_model=ServerStatus,
)
async def stop_all_channels(ctx, params: StopAllChannelsParams) -> ActionResult:
    """Stop every channel on the connected Iguana instance."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        data = await ic.stop_all_channels(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    channels = [_channel_info_from(e) for e in _extract_channels(data)]
    return ActionResult.success(
        ServerStatus(channels=channels, raw=data if isinstance(data, dict) else {}),
        summary="All channels stopped.",
    )


@chat.function(
    "get_current_version",
    "Read the connected Iguana server's own version information.",
    action_type="read",
    chain_callable=True,
    data_model=VersionInfo,
)
async def get_current_version(ctx, params: GetCurrentVersionParams) -> ActionResult:
    """Read the connected Iguana server's own version information."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        data = await ic.current_version(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(VersionInfo(
        major=str(data.get("major", "")), minor=str(data.get("minor", "")),
        build=str(data.get("build", "")), raw=data if isinstance(data, dict) else {},
    ))


@chat.function(
    "get_server_salt",
    "Read the encryption salt used by the connected Iguana server -- needed "
    "to encrypt source/destination passwords before sending them in "
    "add_channel/update_channel calls.",
    action_type="read",
    chain_callable=True,
    data_model=ServerSalt,
)
async def get_server_salt(ctx, params: GetServerSaltParams) -> ActionResult:
    """Read the encryption salt used by the connected Iguana server."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        data = await ic.get_server_salt(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    salt = data if isinstance(data, str) else str(data.get("salt", data)) if isinstance(data, dict) else str(data)
    return ActionResult.success(ServerSalt(salt=salt))


@chat.function(
    "get_channel_config",
    "Read the full configuration of an existing channel (serialized as "
    "XML), by name or guid -- use this to clone/inspect a channel before "
    "update_channel.",
    action_type="read",
    chain_callable=True,
    data_model=ChannelConfig,
)
async def get_channel_config(ctx, params: GetChannelConfigParams) -> ActionResult:
    """Read the full configuration of an existing channel by name or guid."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.name and not params.guid:
        return ActionResult.error("name or guid is required.")
    try:
        data = await ic.get_channel_config(ctx, base_url, username, password, name=params.name, guid=params.guid, compact=str(params.compact).lower())
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    config = data if isinstance(data, str) else json.dumps(data)
    return ActionResult.success(ChannelConfig(name=params.name, guid=params.guid, config_xml=config))


@chat.function(
    "get_default_config",
    "Read the default channel configuration for a given source and "
    "destination component type pair -- the starting point for building a "
    "new channel with add_channel.",
    action_type="read",
    chain_callable=True,
    data_model=ChannelConfig,
)
async def get_default_config(ctx, params: GetDefaultConfigParams) -> ActionResult:
    """Read the default channel configuration for a source/destination component pair."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.source or not params.destination:
        return ActionResult.error("source and destination are both required, e.g. 'LLP', 'Iguana Translator'.")
    try:
        data = await ic.get_default_config(ctx, base_url, username, password, params.source, params.destination, compact=str(params.compact).lower())
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    config = data if isinstance(data, str) else json.dumps(data)
    return ActionResult.success(ChannelConfig(name="", guid="", config_xml=config))


@chat.function(
    "add_channel",
    "Add a new channel to the connected Iguana server from a channel "
    "configuration (as XML, e.g. from get_default_config or "
    "get_channel_config). Requires administrator privileges. The channel "
    "name inside the config must be unique.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.add_channel",
    effects=["iguana.channel.created"],
    data_model=ChannelInfo,
)
async def add_channel(ctx, params: AddChannelParams) -> ActionResult:
    """Add a new channel to the connected Iguana server from a channel configuration."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.config:
        return ActionResult.error("config (channel configuration XML) is required.")
    try:
        data = await ic.add_channel(
            ctx, base_url, username, password, params.config, compact=str(params.compact).lower(),
            source_password=params.source_password, destination_password=params.destination_password, salt=params.salt,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        ChannelInfo(name="", guid=str(data.get("guid", "")) if isinstance(data, dict) else "", status="created", raw=data if isinstance(data, dict) else {}),
        summary="Channel created.",
    )


@chat.function(
    "update_channel",
    "Update the configuration of an existing channel (as XML). Requires "
    "administrator privileges.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.update_channel",
    effects=["iguana.channel.updated"],
    data_model=ChannelInfo,
)
async def update_channel(ctx, params: UpdateChannelParams) -> ActionResult:
    """Update the configuration of an existing channel."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.config:
        return ActionResult.error("config (channel configuration XML) is required.")
    try:
        data = await ic.update_channel(
            ctx, base_url, username, password, params.config, compact=str(params.compact).lower(),
            source_password=params.source_password, destination_password=params.destination_password,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        ChannelInfo(name="", guid="", status="updated", raw=data if isinstance(data, dict) else {}),
        summary="Channel updated.",
    )


@chat.function(
    "remove_channel",
    "Permanently remove a channel from the connected Iguana server, by "
    "name or guid. Requires administrator privileges. Cannot be undone.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.remove_channel",
    effects=["iguana.channel.removed"],
    data_model=DeleteResult,
)
async def remove_channel(ctx, params: RemoveChannelParams) -> ActionResult:
    """Permanently remove a channel from the connected Iguana server."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.name and not params.guid:
        return ActionResult.error("name or guid is required.")
    try:
        await ic.remove_channel(ctx, base_url, username, password, name=params.name, guid=params.guid, compact=str(params.compact).lower())
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        DeleteResult(deleted=True, id=params.guid or params.name),
        summary=f"Channel {params.name or params.guid} removed.",
    )


@chat.function(
    "export_project",
    "Export a Translator project (the channel's mapping code) as a zip "
    "file, base64-encoded, by project guid.",
    action_type="read",
    chain_callable=True,
    data_model=ProjectExport,
)
async def export_project(ctx, params: ExportProjectParams) -> ActionResult:
    """Export a Translator project as a base64-encoded zip file, by project guid."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.guid:
        return ActionResult.error("guid (project guid) is required.")
    try:
        data = await ic.export_project(ctx, base_url, username, password, params.guid, milestone_name=params.milestone_name)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    content = data if isinstance(data, str) else str(data)
    return ActionResult.success(ProjectExport(guid=params.guid, zip_base64=content))


@chat.function(
    "import_project",
    "Import a Translator project (base64-encoded zip, e.g. from "
    "export_project) into an existing channel by project guid.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.import_project",
    effects=["iguana.project.imported"],
    data_model=ImportProjectResult,
)
async def import_project(ctx, params: ImportProjectParams) -> ActionResult:
    """Import a Translator project into an existing channel by project guid."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.guid or not params.project_base64:
        return ActionResult.error("guid and project_base64 are both required.")
    try:
        data = await ic.import_project(ctx, base_url, username, password, params.guid, params.project_base64)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        ImportProjectResult(guid=params.guid, imported=True, raw=data if isinstance(data, dict) else {}),
        summary="Translator project imported.",
    )


@chat.function(
    "save_project_milestone",
    "Save a named milestone (version snapshot) for a Translator project, "
    "by project guid.",
    action_type="write",
    chain_callable=True,
    event="iguana-connector.save_project_milestone",
    effects=["iguana.project.milestone_saved"],
    data_model=MilestoneResult,
)
async def save_project_milestone(ctx, params: SaveProjectMilestoneParams) -> ActionResult:
    """Save a named milestone for a Translator project."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    if not params.guid or not params.milestone_name:
        return ActionResult.error("guid and milestone_name are both required.")
    try:
        data = await ic.save_project_milestone(ctx, base_url, username, password, params.guid, params.milestone_name)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    return ActionResult.success(
        MilestoneResult(guid=params.guid, milestone_name=params.milestone_name, saved=True, raw=data if isinstance(data, dict) else {}),
        summary=f"Milestone '{params.milestone_name}' saved.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Server API -- log query, server config, performance stats
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "query_logs",
    "Query the connected Iguana server's own log messages, optionally "
    "filtered by date range, channel, message type, or free-text filter.",
    action_type="read",
    chain_callable=True,
    data_model=LogQueryResult,
)
async def query_logs(ctx, params: QueryLogsParams) -> ActionResult:
    """Query the connected Iguana server's own log messages."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    filters = {k: v for k, v in {
        "after": params.after, "before": params.before, "source": params.source,
        "type": params.type, "filter": params.filter, "limit": params.limit,
        "debugmode": params.debugmode, "deleted": params.deleted,
        "includesourcelogs": params.includesourcelogs, "refmsgid": params.refmsgid,
    }.items() if v not in (None, "")}
    try:
        data = await ic.api_query(ctx, base_url, username, password, **filters)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    entries_raw = data if isinstance(data, list) else data.get("entries", data.get("messages", [])) if isinstance(data, dict) else []
    entries = [LogEntry(message_id=str(e.get("id", e.get("refmsgid", ""))), timestamp=str(e.get("timestamp", e.get("date", ""))),
                         channel=str(e.get("source", e.get("channel", ""))), type=str(e.get("type", "")),
                         text=str(e.get("text", e.get("message", ""))), raw=e)
               for e in (entries_raw if isinstance(entries_raw, list) else [])]
    raw_xml = data if isinstance(data, str) else ""
    return ActionResult.success(LogQueryResult(entries=entries, raw_xml=raw_xml))


@chat.function(
    "get_server_config",
    "Read the connected Iguana server's own configuration information "
    "(server-wide settings, not one channel's config).",
    action_type="read",
    chain_callable=True,
    data_model=ServerConfig,
)
async def get_server_config(ctx, params: GetServerConfigParams) -> ActionResult:
    """Read the connected Iguana server's own configuration information."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        data = await ic.get_server_config(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    raw_xml = data if isinstance(data, str) else json.dumps(data)
    return ActionResult.success(ServerConfig(raw_xml=raw_xml))


@chat.function(
    "get_performance_stats",
    "Read the connected Iguana server's own performance statistics "
    "(monitor_query) -- throughput/latency data for the server and its "
    "channels.",
    action_type="read",
    chain_callable=True,
    data_model=PerformanceStats,
)
async def get_performance_stats(ctx, params: GetPerformanceStatsParams) -> ActionResult:
    """Read the connected Iguana server's own performance statistics."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        data = await ic.monitor_query(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    raw_xml = data if isinstance(data, str) else json.dumps(data)
    return ActionResult.success(PerformanceStats(raw_xml=raw_xml))


# ──────────────────────────────────────────────────────────────────────────
# Tier-3 value-add: instance audit
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "audit_iguana_instance",
    "Build one aggregated health report for the connected Iguana instance: "
    "server version, total channel count, and how many channels are "
    "stopped (a channel that should be running but isn't is the single "
    "most common Iguana operational problem).",
    action_type="read",
    chain_callable=True,
    data_model=IguanaAuditReport,
)
async def audit_iguana_instance(ctx, params: AuditInstanceParams) -> ActionResult:
    """Build one aggregated health report for the connected Iguana instance."""
    resolved = await _resolve(ctx, params.connection_id)
    if not resolved:
        return _no_connection()
    base_url, username, password = resolved
    try:
        version_data = await ic.current_version(ctx, base_url, username, password)
        status_data = await ic.get_status(ctx, base_url, username, password)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)
    channels = _extract_channels(status_data)
    stopped = [str(c.get("name", c.get("guid", ""))) for c in channels
               if str(c.get("status", c.get("state", ""))).lower() not in ("running", "started")]
    version_str = ".".join(str(version_data.get(k, "")) for k in ("major", "minor", "build") if isinstance(version_data, dict) and version_data.get(k) not in (None, ""))
    return ActionResult.success(IguanaAuditReport(
        version=version_str, total_channels=len(channels), stopped_channels=len(stopped),
        stopped_channel_names=stopped, running_channels=len(channels) - len(stopped),
        raw=status_data if isinstance(status_data, dict) else {},
    ))
