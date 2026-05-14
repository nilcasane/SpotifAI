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


class MusicSearchPlan(BaseModel):
    playlist_name: str
    user_goal: str
    target_tracks: int = 20
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    min_bpm: int | None = None
    max_bpm: int | None = None
    min_energy: float | None = None
    max_energy: float | None = None
    min_valence: float | None = None
    max_valence: float | None = None
    avoid: list[str] = Field(default_factory=list)
    explanation: str


class PlaylistResult(BaseModel):
    status: Literal["DONE", "FAILED"]
    playlist_id: str | None = None
    playlist_url: str | None = None
    tracks_added: int = 0