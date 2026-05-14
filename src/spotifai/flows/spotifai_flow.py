from pydantic import BaseModel
from typing import Any

from crewai.flow.flow import Flow, start, listen, router
from spotifai.crews.discovery_crew import DiscoveryCrew
from spotifai.crews.playlist_crew import PlaylistCrew
from spotifai.models import DiscoveryResult, PlaylistResult

class SpotifAIState(BaseModel):
    user_request: str = ""
    discovery_result: Any | None = None
    retry_count: int = 0
    playlist_result: Any | None = None
    status: str = "PENDING"
    error: str | None = None


class SpotifAIFlow(Flow[SpotifAIState]):

    @start()
    def run_discovery(self, crewai_trigger_payload: dict | None = None):
        """Entry point: set user_request from trigger or existing state and run discovery."""
        if crewai_trigger_payload and isinstance(crewai_trigger_payload, dict):
            # support payloads that provide the user's prompt
            self.state.user_request = (
                crewai_trigger_payload.get("user_request")
                or crewai_trigger_payload.get("topic")
                or self.state.user_request
            )

        if not self.state.user_request:
            raise ValueError("No user_request provided to SpotifAIFlow.start_discovery")

        result = DiscoveryCrew().crew().kickoff(
            inputs={
                "user_request": self.state.user_request,
                "previous_feedback": "",
                "previous_tracks": [],
            }
        )

        discovery: DiscoveryResult = result.pydantic
        self.state.discovery_result = discovery

        return discovery

    @router(run_discovery)
    def decide_after_discovery(self):
        discovery: DiscoveryResult = self.state.discovery_result

        if discovery.status == "READY" and discovery.approved_tracks:
            return "playlist_ready"

        if discovery.status == "NEEDS_MORE":
            return "discovery_retry_needed"

        return "no_tracks_found"

    @listen("discovery_retry_needed")
    def retry_discovery(self):
        previous: DiscoveryResult = self.state.discovery_result
        user_request = self.state.user_request

        self.state.retry_count += 1

        result = DiscoveryCrew().crew().kickoff(
            inputs={
                "user_request": user_request,
                "previous_feedback": previous.next_search_strategy,
                "previous_tracks": previous.model_dump_json(),
            }
        )

        discovery: DiscoveryResult = result.pydantic
        self.state.discovery_result = discovery

        return discovery

    @router(retry_discovery)
    def decide_after_retry(self):
        discovery: DiscoveryResult = self.state.discovery_result

        if discovery.approved_tracks:
            return "playlist_ready"

        return "no_tracks_found"

    @listen("playlist_ready")
    def create_playlist(self):
        discovery: DiscoveryResult = self.state.discovery_result

        #playlist_name = self._playlist_name(discovery)
        playlist_name = "SpotifAI Playlist"
        track_ids = [track.spotify_id for track in discovery.approved_tracks]

        result = PlaylistCrew().crew().kickoff(
            inputs={
                "playlist_name": playlist_name,
                "track_ids": track_ids,
            }
        )

        playlist_result: PlaylistResult = result.pydantic
        self.state.playlist_result = playlist_result
        self.state.status = playlist_result.status
        if playlist_result.status != "DONE":
            self.state.error = "Spotify did not add any tracks to the playlist."

        return playlist_result

    @listen("no_tracks_found")
    def finish_without_tracks(self):
        self.state.status = "NO_TRACKS_FOUND"
        self.state.error = "Discovery did not return any Spotify track IDs."
        return self.state.model_dump()
