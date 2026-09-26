"""Mapping between TMDB's media-type strings and the shared MediaType enum."""

from medialab_contracts import MediaType

# TMDB classifies titles as "movie" or "tv"; the medialab suite uses
# "movie"/"show" (medialab-contracts MediaType). Map at this boundary.
_TMDB_TO_MEDIA_TYPE = {
    "movie": MediaType.MOVIE,
    "tv": MediaType.SHOW,
    "show": MediaType.SHOW,
}


def from_tmdb_media_type(tmdb_media_type: str) -> MediaType | None:
    """Return the MediaType for a TMDB media-type string, or None if unknown."""
    return _TMDB_TO_MEDIA_TYPE.get(tmdb_media_type.lower())
