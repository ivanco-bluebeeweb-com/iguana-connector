"""Pydantic params models + SDL entity contracts for Iguana Connector.

All params models are module-scope (V17 federal invariant, same rule as
GitLab CI/CD Connector's / PagerDuty Connector's schemas.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectIguanaParams(BaseModel):
    base_url: str = Field(
        "",
        description="Base URL of your Iguana instance, e.g. https://your-server.example.com:6543",
    )
    allow_private_http: bool = Field(
        False,
        description=(
            "Set true to allow a plain http:// base_url for a self-hosted "
            "instance on localhost or a private network. HTTPS is required otherwise."
        ),
    )
    username: str = Field("", description="Iguana administrator username for this instance.")
    password: str = Field("", description="Iguana administrator password for this instance.")
    label: str = Field("", description="Optional friendly name for this instance connection.")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""
    base_url: str = ""


class ProviderConnectionList(sdl.Entity):
    connections: list[ProviderConnection] = []


class DisconnectIguanaParams(BaseModel):
    connection_id: str = Field("", description="ID of the connection to disconnect.")


class DeleteResult(sdl.Entity):
    deleted: bool = False
    id: str = ""


class ConnectionRefParams(BaseModel):
    connection_id: str = Field("", description="ID of the Iguana connection to use (leave empty to use the only/most recent one).")


# ──────────────────────────────────────────────────────────────────────────
# License API (my.interfaceware.com) -- separate connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectLicensePortalParams(BaseModel):
    license_username: str = Field("", description="Your my.interfaceware.com licensing portal username.")
    license_password: str = Field("", description="Your my.interfaceware.com licensing portal password.")
    label: str = Field("", description="Optional friendly name for this licensing portal login.")


class DisconnectLicensePortalParams(BaseModel):
    connection_id: str = Field("", description="ID of the licensing portal connection to remove.")


class LicensePortalConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""


class LicensePortalConnectionList(sdl.Entity):
    connections: list[LicensePortalConnection] = []


class LicenseConnectionRefParams(BaseModel):
    connection_id: str = Field("", description="ID of the licensing portal connection to use (leave empty to use the only/most recent one).")


class ListLicensesParams(LicenseConnectionRefParams):
    pass


class LicenseEntry(sdl.Entity):
    entitlement_id: str = ""
    description: str = ""
    raw: dict = {}


class LicenseList(sdl.Entity):
    licenses: list[LicenseEntry] = []


class ActivateLicenseParams(LicenseConnectionRefParams):
    entitlement_id: str = Field("", description="The entitlement ID of the license to activate, from list_licenses.")
    instance_id: str = Field("", description="The target Iguana instance ID, from get_instance_license_detail.")
    description: str = Field("", description="A description to pair with this activation, e.g. 'production' or 'testing'.")


class LicenseActivationResult(sdl.Entity):
    activation_id: str = ""
    description: str = ""
    raw: dict = {}


class CheckLicenseActivationParams(LicenseConnectionRefParams):
    entitlement_id: str = Field("", description="The entitlement ID to check activation status for.")


class TransferLicenseParams(LicenseConnectionRefParams):
    activation_id: str = Field("", description="The activation ID of the license to transfer from.")
    instance_id: str = Field("", description="The target Iguana instance ID to transfer the license to.")
    description: str = Field("", description="A description to pair with this transfer.")


class GetInstanceLicenseDetailParams(ConnectionRefParams):
    pass


class InstanceLicenseDetail(sdl.Entity):
    instance_id: str = ""
    raw: dict = {}


class ApplyInstanceLicenseParams(ConnectionRefParams):
    key: str = Field("", description="The license key to apply to this Iguana instance.")


# ──────────────────────────────────────────────────────────────────────────
# Channel API
# ──────────────────────────────────────────────────────────────────────────


class ChannelRefParams(ConnectionRefParams):
    name: str = Field("", description="Channel name (use this OR guid, guid is preferred and stable across renames).")
    guid: str = Field("", description="Channel GUID (preferred -- does not change when a channel is renamed).")


class GetServerStatusParams(ConnectionRefParams):
    pass


class ChannelInfo(sdl.Entity):
    name: str = ""
    guid: str = ""
    status: str = ""
    raw: dict = {}


class ServerStatus(sdl.Entity):
    number_of_channels: int = 0
    channels: list[ChannelInfo] = []
    raw: dict = {}


class StartChannelParams(ChannelRefParams):
    pass


class StopChannelParams(ChannelRefParams):
    pass


class StartAllChannelsParams(ConnectionRefParams):
    pass


class StopAllChannelsParams(ConnectionRefParams):
    pass


class VersionInfo(sdl.Entity):
    major: int = 0
    minor: int = 0
    build: int = 0
    build_ext: str = ""
    raw: dict = {}


class GetCurrentVersionParams(ConnectionRefParams):
    pass


class GetServerSaltParams(ConnectionRefParams):
    pass


class ServerSalt(sdl.Entity):
    salt: str = ""


class GetChannelConfigParams(ChannelRefParams):
    compact: bool = Field(True, description="Return XML in compact format.")


class ChannelConfig(sdl.Entity):
    name: str = ""
    guid: str = ""
    config_xml: str = ""


class GetDefaultConfigParams(ConnectionRefParams):
    source: str = Field(
        "",
        description="Source component type: LLP Listener, From Database, From File, From Plugin, From HTTPS, From Channel, or From Translator.",
    )
    destination: str = Field(
        "",
        description="Destination component type: LLP Client, To Database, To File, To Plugin, To HTTPS, To Channel, or To Translator.",
    )
    compact: bool = Field(True, description="Return XML in compact format.")


class AddChannelParams(ConnectionRefParams):
    config: str = Field("", description="Full channel configuration XML, e.g. from get_default_config or get_channel_config.")
    compact: bool = Field(True, description="Return XML in compact format.")
    source_password: str = Field("", description="Password for the source component (From File/From Database channels only).")
    destination_password: str = Field("", description="Password for the destination component (To File/To Database channels only).")
    salt: str = Field("", description="Encryption salt from get_server_salt -- needed when cloning a channel between different servers.")


class UpdateChannelParams(ConnectionRefParams):
    config: str = Field("", description="Updated channel configuration XML. The channel must be stopped first.")
    compact: bool = Field(True, description="Return XML in compact format.")
    source_password: str = Field("", description="Password for the source component (From File/From Database channels only).")
    destination_password: str = Field("", description="Password for the destination component (To File/To Database channels only).")


class RemoveChannelParams(ChannelRefParams):
    compact: bool = Field(True, description="Return XML in compact format.")


class ExportProjectParams(ConnectionRefParams):
    guid: str = Field("", description="Component GUID of the Translator to export (from_mapper/to_mapper guid, not the channel guid).")
    milestone_name: str = Field("", description="Name of the milestone to export. Defaults to the project's most recent milestone.")
    sample_data: bool = Field(True, description="Include sample data in the exported project.")


class ProjectExport(sdl.Entity):
    guid: str = ""
    zip_base64: str = ""


class ImportProjectParams(ConnectionRefParams):
    guid: str = Field("", description="Component GUID of the Translator to import into.")
    project_base64: str = Field("", description="Base64-encoded project zip file contents (matching export_project's output).")
    sample_data: str = Field("", description="One of 'append', 'replace', or empty to exclude sample data.")


class ImportProjectResult(sdl.Entity):
    guid: str = ""
    imported: bool = False
    raw: dict = {}


class SaveProjectMilestoneParams(ConnectionRefParams):
    guid: str = Field("", description="Component GUID of the Translator project.")
    milestone_name: str = Field("", description="Name for the new milestone.")


class MilestoneResult(sdl.Entity):
    guid: str = ""
    milestone_name: str = ""
    saved: bool = False
    raw: dict = {}


# ──────────────────────────────────────────────────────────────────────────
# Server API (logs / config / performance)
# ──────────────────────────────────────────────────────────────────────────


class QueryLogsParams(ConnectionRefParams):
    after: str = Field("", description="Only messages after this date, format yyyy/mm/dd hh:mm:ss.")
    before: str = Field("", description="Only messages before this date, format yyyy/mm/dd hh:mm:ss.")
    debugmode: bool = Field(False, description="Include system debug messages.")
    deleted: str = Field("", description="'true' to select only deleted messages, 'false' to exclude them, empty for both.")
    filter: str = Field("", description="Only messages containing this text.")
    includesourcelogs: bool = Field(False, description="Include messages from source channels feeding this channel.")
    refmsgid: str = Field("", description="Return only the message with this unique log message ID.")
    source: str = Field("", description="Only messages from this channel name.")
    type: str = Field(
        "",
        description="Comma-separated message types: messages, ack_messages, errors, errors_marked, errors_unmarked, info, debug, warnings, successes, resubmitted.",
    )
    limit: int = Field(0, description="Maximum number of log entries to return (0 = no limit specified).")


class LogEntry(sdl.Entity):
    message_id: str = ""
    channel: str = ""
    type: str = ""
    timestamp: str = ""
    text: str = ""
    raw: dict = {}


class LogQueryResult(sdl.Entity):
    entries: list[LogEntry] = []
    raw_xml: str = ""


class GetServerConfigParams(ConnectionRefParams):
    pass


class ServerConfig(sdl.Entity):
    raw_xml: str = ""


class GetPerformanceStatsParams(ConnectionRefParams):
    pass


class PerformanceStats(sdl.Entity):
    raw_xml: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Tier-3 value-add: instance audit
# ──────────────────────────────────────────────────────────────────────────


class AuditInstanceParams(ConnectionRefParams):
    pass


class IguanaAuditReport(sdl.Entity):
    version: str = ""
    total_channels: int = 0
    stopped_channels: int = 0
    stopped_channel_names: list[str] = []
    running_channels: int = 0
    raw: dict = {}
