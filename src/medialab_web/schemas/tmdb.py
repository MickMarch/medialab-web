from typing import Any

from pydantic import BaseModel


class TmdbSearchResult(BaseModel):
    tmdb_id: int
    title: str
    year: str
    media_type: str
    overview: str
    vote_average: float
    poster_path: str | None
    on_wishlist: bool = False
    in_library: bool = False


class TmdbSearchResponse(BaseModel):
    status: str
    message: str
    data: list[TmdbSearchResult]


class TmdbMediaDetailResponse(BaseModel):
    status: str
    message: str
    data: dict[str, Any] | None
