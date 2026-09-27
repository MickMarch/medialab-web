from medialab_web.client._discover import _DiscoverMixin
from medialab_web.client._jobs import _JobsMixin
from medialab_web.client._settings import _SettingsMixin
from medialab_web.client._shows import _ShowsMixin
from medialab_web.client._status import _StatusMixin
from medialab_web.client._tmdb import _TmdbMixin
from medialab_web.client._torrents import _TorrentsMixin


class OrchestratorClient(
    _TmdbMixin,
    _TorrentsMixin,
    _StatusMixin,
    _JobsMixin,
    _SettingsMixin,
    _DiscoverMixin,
    _ShowsMixin,
):
    """The web UI's single downstream dependency: the medialab-orchestrator gateway."""
