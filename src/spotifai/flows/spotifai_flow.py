from pydantic import BaseModel
from typing import Any
import re

from crewai.flow.flow import Flow, start, listen, router
from spotifai.crews.discovery_crew import DiscoveryCrew
from spotifai.crews.playlist_crew import PlaylistCrew

class SpotifAIState(BaseModel):
    user_request: str = ""
    discovery_result: dict | None = None
    retry_count: int = 0
    playlist_result: dict | None = None
    status: str = "PENDING"
    error: str | None = None

def _result_to_dict(result: Any) -> dict:
    """Normalize a Crew.kickoff result to a plain dict when possible."""
    if result is None:
        return {}
    # Common Crew output wrappers
    if hasattr(result, "json_dict") and isinstance(result.json_dict, dict):
        return result.json_dict
    if hasattr(result, "pydantic"):
        try:
            if hasattr(result.pydantic, "model_dump"):
                return result.pydantic.model_dump()
            return result.pydantic.dict()
        except Exception:
            pass
    if hasattr(result, "raw"):
        raw = result.raw
        if isinstance(raw, dict):
            return raw
        return {"raw": str(raw)}
    # Fallback: if it's already a dict
    if isinstance(result, dict):
        return result
    return {"raw": str(result)}

def _extract_tracks_from_text(text: str) -> list[dict[str, str]]:
    """Extract Spotify tracks from the markdown-ish output returned by the crew."""
    tracks: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    def add_track(name: str, artist: str, spotify_id: str) -> None:
        name = name.strip(" -*")
        artist = artist.strip(" -*")
        spotify_id = spotify_id.strip()
        if not spotify_id or spotify_id in seen_ids:
            return
        seen_ids.add(spotify_id)
        tracks.append(
            {
                "name": name,
                "artist": artist,
                "spotify_id": spotify_id,
            }
        )

    for match in re.finditer(
        r"^\s*-\s*(?P<name>.+?)\s+by\s+(?P<artist>.+?)\s+\(ID:\s*(?P<id>[A-Za-z0-9]+)\)",
        text,
        flags=re.MULTILINE,
    ):
        add_track(match.group("name"), match.group("artist"), match.group("id"))

    current_name = ""
    current_artist = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if lower.startswith("name:"):
            current_name = line.split(":", 1)[1].strip()
        elif lower.startswith("artist:"):
            current_artist = line.split(":", 1)[1].strip()
        elif lower.startswith("spotify id:"):
            spotify_id = line.split(":", 1)[1].strip()
            if current_name and current_artist:
                add_track(current_name, current_artist, spotify_id)
            current_name = ""
            current_artist = ""

    return tracks

def _normalize_discovery_result(result: Any, user_request: str) -> dict:
    data = _result_to_dict(result)
    raw = str(data.get("raw", ""))

    approved_tracks = data.get("approved_tracks") or _extract_tracks_from_text(raw)
    data["approved_tracks"] = approved_tracks
    data.setdefault("playlist_name", f"SpotifAI - {user_request}")
    data["status"] = "READY" if approved_tracks else "NEEDS_MORE"

    return data

def _track_ids(approved_tracks: list[Any]) -> str:
    ids: list[str] = []
    for track in approved_tracks:
        if isinstance(track, dict):
            spotify_id = track.get("spotify_id") or track.get("id") or track.get("Spotify ID")
            if spotify_id:
                ids.append(str(spotify_id).strip())
            continue

        match = re.search(r"(?:Spotify ID|ID):\s*([A-Za-z0-9]+)", str(track))
        if match:
            ids.append(match.group(1))

    return ",".join(dict.fromkeys(track_id for track_id in ids if track_id))

class SpotifAIFlow(Flow[SpotifAIState]):

    @start()
    def start_discovery(self, crewai_trigger_payload: dict | None = None):
        """Entry point: set user_request from trigger or existing state and run discovery."""
        if crewai_trigger_payload and isinstance(crewai_trigger_payload, dict):
            # support payloads that provide the user's prompt
            self.state.user_request = crewai_trigger_payload.get("user_request") or crewai_trigger_payload.get("topic") or self.state.user_request

        if not self.state.user_request:
            raise ValueError("No user_request provided to SpotifAIFlow.start_discovery")

        discovery = DiscoveryCrew().crew().kickoff(
            inputs={
                "user_request": self.state.user_request,
                "previous_feedback": "",
                "previous_tracks": [],
            }
        )

        self.state.discovery_result = _normalize_discovery_result(discovery, self.state.user_request)
        return discovery

    def _next_step(self) -> str:
        d = self.state.discovery_result or {}
        status = d.get("status") or d.get("state")

        if status == "READY" and d.get("approved_tracks"):
            return "create_playlist"

        if self.state.retry_count < 1:
            return "retry_discovery"

        return "no_tracks_found"

    @router(start_discovery)
    def decide_next_step(self):
        return self._next_step()

    @listen("retry_discovery")
    def run_discovery_again(self):
        prev = self.state.discovery_result or {}
        self.state.retry_count += 1

        result = DiscoveryCrew().crew().kickoff(
            inputs={
                "user_request": self.state.user_request,
                "previous_feedback": prev.get("next_search_strategy", ""),
                "previous_tracks": prev.get("approved_tracks", [])
            }
        )

        self.state.discovery_result = _normalize_discovery_result(result, self.state.user_request)
        return result

    @router(run_discovery_again)
    def decide_after_retry(self):
        return self._next_step()

    @listen("create_playlist")
    def build_playlist(self):
        d = self.state.discovery_result or {}
        playlist_name = d.get("playlist_name") or f"SpotifAI - {self.state.user_request}"
        approved_tracks = d.get("approved_tracks") or []
        track_ids = _track_ids(approved_tracks)

        if not track_ids:
            self.state.status = "NO_TRACKS_FOUND"
            self.state.error = "Discovery did not return any Spotify track IDs."
            return self.state.model_dump()

        try:
            result = PlaylistCrew().crew().kickoff(
                inputs={
                    "playlist_name": playlist_name,
                    "approved_tracks": approved_tracks,
                    "track_ids": track_ids,
                }
            )

            self.state.playlist_result = _result_to_dict(result)
            self.state.status = "DONE"
            return result
        except Exception as e:
            self.state.error = str(e)
            self.state.status = "FAILED"
            raise

    @listen("no_tracks_found")
    def finish_without_tracks(self):
        self.state.status = "NO_TRACKS_FOUND"
        self.state.error = "Discovery did not return any Spotify track IDs."
        return self.state.model_dump()
