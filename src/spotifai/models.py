from pydantic import BaseModel, Field
from typing import Literal


class TrackResult(BaseModel):
    spotify_id: str
    name: str
    artist: str


class DiscoveryResult(BaseModel):
    status: Literal["READY", "NEEDS_MORE", "NO_TRACKS"]
    playlist_name: str
    approved_tracks: list[TrackResult] = Field(default_factory=list)
    rejected_summary: str = ""
    next_search_strategy: str = ""


class PlaylistResult(BaseModel):
    status: Literal["DONE", "FAILED"]
    playlist_id: str | None = None
    playlist_url: str | None = None
    tracks_added: int = 0