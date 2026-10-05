"""The shared structured-error model, and the gateway refusal a client hands back."""

from medialab_contracts import ErrorResponse

__all__ = ["ErrorResponse", "GatewayError"]


class GatewayError(ErrorResponse):
    """A non-2xx gateway answer whose body parsed as the error envelope.

    The route decides whether ``detail`` is shown; the client only carries it.
    ``status_code`` is the HTTP status it arrived with.
    """

    status: str = "error"
    status_code: int
