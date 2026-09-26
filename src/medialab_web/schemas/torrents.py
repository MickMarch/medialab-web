from pydantic import BaseModel, ConfigDict, Field


class TorrentResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    file_name: str = Field(alias="fileName")
    file_url: str = Field(alias="fileUrl")
    seeders: int = Field(alias="nbSeeders", ge=0)
    leechers: int = Field(alias="nbLeechers", ge=0)
    file_size: int = Field(alias="fileSize")
    languages: list[str] = Field(default_factory=list)
    multi_audio: bool = Field(alias="multiAudio", default=False)


class TorrentSearchResponse(BaseModel):
    status: str
    message: str
    data: dict[str, list[TorrentResult]]
