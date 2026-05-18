import os
import spotipy
from dotenv import load_dotenv
from crewai.tools import tool
from spotipy.oauth2 import SpotifyOAuth
from spotifai.models import DiscoveryResult, PlaylistResult, TrackResult

load_dotenv()

def get_spotify_client():
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope="playlist-modify-private playlist-modify-public playlist-read-private"
        )
    )


def _clean_track_ids(track_ids: str) -> list[str]:
    ids = []
    for track_id in track_ids.split(","):
        cleaned = track_id.strip().removeprefix("spotify:track:")
        if "/track/" in cleaned:
            cleaned = cleaned.split("/track/", 1)[1].split("?", 1)[0]
        if len(cleaned) == 22 and cleaned.isalnum() and cleaned not in ids:
            ids.append(cleaned)
    return ids


def search_spotify_tracks(
    queries: list[str],
    playlist_name: str,
    excluded_ids: set[str] | None = None,
) -> DiscoveryResult:
    sp = get_spotify_client()
    approved_tracks = []
    seen = set(excluded_ids or set())

    for query in queries:
        results = sp.search(q=query, type="track", limit=10)
        tracks = results.get("tracks", {}).get("items", [])
        for track in tracks:
            spotify_id = track["id"]
            if spotify_id in seen:
                continue

            seen.add(spotify_id)
            artist_names = ", ".join(artist["name"] for artist in track["artists"])
            approved_tracks.append(
                TrackResult(
                    spotify_id=spotify_id,
                    name=track["name"],
                    artist=artist_names,
                )
            )

            if len(approved_tracks) >= 20:
                break

        if len(approved_tracks) >= 20:
            break

    return DiscoveryResult(
        status="READY" if approved_tracks else "NO_TRACKS",
        playlist_name=playlist_name,
        approved_tracks=approved_tracks,
    )


@tool("Search tracks on Spotify", result_as_answer=True)
def search_tracks(query: str) -> str:
    """
    Search for tracks on Spotify.
    The 'query' parameter must be a plain text search string (NOT JSON).
    Returns a JSON DiscoveryResult built only from Spotify API results.
    """
    playlist_name = query.strip().title() or "SpotifAI Playlist"
    return search_spotify_tracks([query], playlist_name).model_dump_json()

@tool("create_playlist_on_spotify", result_as_answer=True)
def create_playlist(name: str = "SpotifAI Playlist") -> str:
    """
    Creates a Spotify playlist.
    The 'name' parameter is the playlist name (plain text string).
    Returns a JSON PlaylistResult produced by Spotify.
    """
    sp = get_spotify_client()
    playlist = sp._post("me/playlists", payload={
        "name": name,
        "public": True,
        "description": "Playlist generada automaticament per SpotifAI",
    },)

    result = PlaylistResult(
        status="DONE" if playlist and "id" in playlist else "FAILED",
        playlist_id=playlist["id"],
        playlist_url=playlist["external_urls"]["spotify"],
        tracks_added=0,
    )

    return result.model_dump_json()

@tool("add_tracks_to_playlist_on_spotify", result_as_answer=True)
def add_tracks_to_playlist(playlist_id: str, track_ids: str) -> str:
    """
    Adds tracks to an existing Spotify playlist.
    The 'playlist_id' parameter is the ID returned by the create playlist tool.
    The 'track_ids' parameter is a comma-separated string of Spotify track IDs.
    Returns a JSON PlaylistResult produced by Spotify.
    """
    pid = playlist_id.strip()
    ids = _clean_track_ids(track_ids)

    sp = get_spotify_client()
    before = sp.playlist_items(pid, fields="total", limit=1)["total"]
    uris = [f"spotify:track:{track_id}" for track_id in ids]
    sp._post(f"playlists/{pid}/items", payload={"uris": uris, "position": 0})
    after = sp.playlist_items(pid, fields="total", limit=1)["total"]
    tracks_added = max(0, after - before)

    result = PlaylistResult(
        status="DONE" if tracks_added else "FAILED",
        playlist_id=pid or None,
        playlist_url=f"https://open.spotify.com/playlist/{pid}" if pid else None,
        tracks_added=tracks_added,
    )

    return result.model_dump_json()
