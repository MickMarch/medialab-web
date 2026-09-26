from medialab_contracts import TransferInfo
from pydantic import BaseModel

from medialab_web.schemas.jobs import JobView


class LiveTransfers(BaseModel):
    """The torrent-downloader live-transfers payload, passed through by the
    gateway under the ``transfers`` key."""

    status: str
    message: str = ""
    data: list[TransferInfo] = []


class MergedTransfersResponse(BaseModel):
    """Body of the gateway's ``GET /transfers``: live transfer state from
    torrent-downloader merged with the orchestrator's own pipeline job rows."""

    status: str
    transfers: LiveTransfers
    jobs: list[JobView]
