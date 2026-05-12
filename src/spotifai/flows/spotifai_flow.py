from pydantic import BaseModel
from typing import Any

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
                "previous_feedback": ""
            }
        )

        self.state.discovery_result = _result_to_dict(discovery)
        return discovery

    @router(start_discovery)
    def decide_next_step(self):
        d = self.state.discovery_result or {}
        status = d.get("status") or d.get("state") or ("READY" if "approved_tracks" in d and d.get("approved_tracks") else "NEEDS_MORE")

        if status == "READY":
            return "create_playlist"

        # Allow a single retry
        if self.state.retry_count < 1:
            return "retry_discovery"

        # After one retry, proceed to create playlist with what we have (graceful fallback)
        return "create_playlist"

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

        self.state.discovery_result = _result_to_dict(result)
        return result

    @listen("create_playlist")
    def create_playlist(self):
        d = self.state.discovery_result or {}
        playlist_name = d.get("playlist_name") or f"SpotifAI - {self.state.user_request}"
        approved_tracks = d.get("approved_tracks") or []

        try:
            result = PlaylistCrew().crew().kickoff(
                inputs={
                    "playlist_name": playlist_name,
                    "approved_tracks": approved_tracks,
                }
            )

            self.state.playlist_result = _result_to_dict(result)
            self.state.status = "DONE"
            return result
        except Exception as e:
            self.state.error = str(e)
            self.state.status = "FAILED"
            raise
