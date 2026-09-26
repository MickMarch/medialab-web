from pydantic import BaseModel


class DeletionPlan(BaseModel):
    """What ``DELETE /jobs/{id}`` would remove, as the gateway computes it.
    Shown verbatim to the user before the confirm button."""

    status: str
    job_id: str
    torrent: bool
    download_folder: str | None = None
    placed_paths: list[str] = []
    scan_path: str | None = None
    refused: str | None = None
