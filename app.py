"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), SAME REASONING AS GitLab CI/CD Connector /
PagerDuty Connector / UiPath Connector / Blue Prism Connector /
Automation Anywhere Connector.

Iguana is the user's OWN self-hosted integration engine instance -- Imperal
cannot and should not broker access to someone else's healthcare interface
engine centrally. The user supplies their own base_url + administrator
username/password once, Vault-encrypted via `ctx.secrets`, and every call
runs against their own instance.

WHY HTTP BASIC AUTH ON EVERY REQUEST, NOT A STORED BEARER TOKEN.

Confirmed by direct reading of help.interfaceware.com/kb/1477 (2026-08-21):
every Iguana 6 HTTP API function takes `auth={username=.., password=..}`
as plain HTTP Basic Auth on every call, with no login/token step. This is
a genuinely different, older auth model than the Bearer/PAT/API-key schemes
used by every other connector in this portfolio, so username+password are
both stored (not a single derived token) -- see iguana_client.py's
module docstring for the full citation trail.

WHY A SEPARATE SECOND CONNECTION TYPE FOR THE LICENSE PORTAL
(my.interfaceware.com), NOT THE SAME SECRET AS THE INSTANCE CONNECTION.

The License API (help.interfaceware.com/license_api/, confirmed
2026-08-21) is a genuinely distinct surface: it authenticates against
`my.interfaceware.com` (iNTERFACEWARE's own central licensing system, not
the user's Iguana instance) with its own username/password and its own
session-token flow (`method=session.login` returns a token used on
subsequent license.* calls). A user may want to manage licenses without
ever configuring an instance connection (or vice versa) -- same
"genuinely separate auth surface gets its own secret store" precedent as
PagerDuty Connector's REST API key vs. Events API routing_key.

WHY `write_mode="both"`, SAME REASONING AS EVERY OTHER BYOK CONNECTOR IN
THIS PORTFOLIO.

Declaring `write_mode="user"` would mean only the platform's generic
Secrets screen could write these -- leaving a first-time user with no
in-app screen explaining what an Iguana administrator account or a
my.interfaceware.com login even is. `"both"` keeps the generic Secrets
screen as a fallback while letting the in-app connect form (panels.py)
write the same secret.
"""

from imperal_sdk import Extension, ChatExtension

ext = Extension(
    "iguana-connector",
    version="0.1.0",
    display_name="Iguana",
    description=(
        "Connect your own self-hosted Iguana (iNTERFACEWARE) instance to manage "
        "channels from Imperal -- status/start/stop/start-all/stop-all, full "
        "channel configuration (add/update/remove, get/get-default config), "
        "Translator project export/import and milestones, server log queries, "
        "server configuration and performance stats, plus your "
        "my.interfaceware.com license entitlements (list/activate/check/"
        "transfer, and applying a license key to your instance). Your admin "
        "credentials are verified against your own instance before they're "
        "saved. Scoped to the fully-documented Iguana 6 HTTP API surface -- "
        "see this app's own settings screen for the IguanaX compatibility note."
    ),
    icon="icon.svg",
    actions_explicit=True,
    capabilities=["iguana:read", "iguana:write"],
)

chat = ChatExtension(
    ext,
    tool_name="iguana-connector",
    description="View and manage Iguana (iNTERFACEWARE) channels, projects, server logs/config, and licensing",
)

ext.secret(
    "iguana_connections",
    (
        "Your connected Iguana instances -- stored as a JSON array, one "
        "entry per instance, each with its own base_url, administrator "
        "username, password, and an optional friendly label. Managed "
        "through connect_iguana / disconnect_iguana -- you should not need "
        "to edit this directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)

ext.secret(
    "iguana_license_connections",
    (
        "Your saved my.interfaceware.com licensing portal logins -- stored "
        "as a JSON array, one entry per login, each with its own username, "
        "password, and an optional friendly label. Managed through "
        "connect_license_portal / disconnect_license_portal -- you should "
        "not need to edit this directly."
    ),
    required=False,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Reports whether at least one Iguana instance connection is saved --
    does not make a live network call (the instance may be on a private
    network unreachable from Imperal's own infrastructure), same
    conservative approach as GitLab CI/CD Connector's health_check."""
    import json as _json
    raw = await ctx.secrets.get("iguana_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} Iguana instance(s) connected." if count
            else "Not connected yet -- run connect_iguana."
        ),
    }
