from pydantic import BaseModel
from typing import Any

from crewai.flow.flow import Flow, start, listen, router
from spotifai.crews.discovery_crew import DiscoveryCrew
from spotifai.crews.playlist_crew import PlaylistCrew
from spotifai.models import DiscoveryResult, PlaylistResult
from spotifai.tools.spotify_tools import search_spotify_tracks

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

        plan = result.tasks_output[0].pydantic
        discovery = search_spotify_tracks(
            plan.search_queries or [self.state.user_request],
            plan.playlist_name,
        )
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

        previous_ids = {track.spotify_id for track in previous.approved_tracks}
        plan = result.tasks_output[0].pydantic
        discovery = search_spotify_tracks(
            plan.search_queries or [user_request],
            plan.playlist_name,
            previous_ids,
        )
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
        target_tracks = 20

        playlist_name = discovery.playlist_name
        result = PlaylistCrew().crew().kickoff(
            inputs={
                "playlist_name": playlist_name,
            }
        )
        playlist_result = PlaylistResult.model_validate_json(result.raw)

        if playlist_result.status != "DONE" or not playlist_result.playlist_id:
            self.state.playlist_result = playlist_result
            self.state.status = playlist_result.status
            self.state.error = "Spotify did not create the playlist."
            return playlist_result

        playlist_id = playlist_result.playlist_id
        playlist_url = playlist_result.playlist_url
        total_added = 0
        seen_track_ids: set[str] = set()
        current_discovery = discovery

        for _ in range(5):
            track_ids = [
                track.spotify_id
                for track in current_discovery.approved_tracks
                if track.spotify_id not in seen_track_ids
            ]
            seen_track_ids.update(track_ids)

            if track_ids:
                add_result = PlaylistCrew().add_tracks_crew().kickoff(
                    inputs={
                        "playlist_id": playlist_id,
                        "track_ids": ",".join(track_ids),
                    }
                )
                added = PlaylistResult.model_validate_json(add_result.raw)
                if added.status == "DONE":
                    total_added += added.tracks_added

            if total_added >= target_tracks:
                break

            retry = DiscoveryCrew().crew().kickoff(
                inputs={
                    "user_request": self.state.user_request,
                    "previous_feedback": f"Need {target_tracks - total_added} more different tracks.",
                    "previous_tracks": list(seen_track_ids),
                }
            )
            plan = retry.tasks_output[0].pydantic
            current_discovery = search_spotify_tracks(
                plan.search_queries or [self.state.user_request],
                playlist_name,
                seen_track_ids,
            )
            self.state.discovery_result = current_discovery

        playlist_result = PlaylistResult(
            status="DONE" if total_added >= target_tracks else "FAILED",
            playlist_id=playlist_id,
            playlist_url=playlist_url,
            tracks_added=total_added,
        )
        self.state.playlist_result = playlist_result
        self.state.status = playlist_result.status
        if playlist_result.status != "DONE":
            self.state.error = f"Spotify only added {total_added}/{target_tracks} tracks."

        return playlist_result

    @listen("no_tracks_found")
    def finish_without_tracks(self):
        self.state.status = "NO_TRACKS_FOUND"
        self.state.error = "Discovery did not return any Spotify track IDs."
        return self.state.model_dump()
