from fastapi import Request

from medialab_web.client import OrchestratorClient


def get_client(request: Request) -> OrchestratorClient:
    """The one gateway client, created at startup and stored on the app."""
    return request.app.state.client
