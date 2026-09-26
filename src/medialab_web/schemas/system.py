from pydantic import BaseModel


class DownstreamHealth(BaseModel):
    torrent_downloader: bool
    medialab_jellyfin: bool


class HealthResponse(BaseModel):
    """Aggregated gateway health: the orchestrator's own status plus the
    reachability of both downstream worker services."""

    status: str
    uptime_seconds: float
    downstream: DownstreamHealth
    needs_attention: int = 0


class DiskUsageResponse(BaseModel):
    status: str
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    used_percent: float
