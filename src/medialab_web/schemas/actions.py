from pydantic import BaseModel


class ActionResponse(BaseModel):
    """Envelope the gateway returns for a fire-and-forget action such as
    stop-seeding: the downloader's own status and human-readable message."""

    status: str
    message: str
