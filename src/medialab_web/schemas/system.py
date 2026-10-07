from medialab_contracts import CredentialState
from pydantic import BaseModel


class DownstreamHealth(BaseModel):
    torrent_downloader: bool
    medialab_jellyfin: bool


class HealthResponse(BaseModel):
    """Aggregated gateway health: the orchestrator's own status, the
    reachability of both downstream worker services, and whether
    torrent-downloader reports qBittorrent bound to an accepted VPN interface.
    The flag is informational here; the downloader enforces it."""

    status: str
    uptime_seconds: float
    downstream: DownstreamHealth
    needs_attention: int = 0
    vpn_interface_bound: bool = False
    credentials: dict[str, CredentialState] = {}
    """Per-credential health across the stack; only ``invalid`` needs a human."""


class DiskUsageResponse(BaseModel):
    status: str
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    used_percent: float
