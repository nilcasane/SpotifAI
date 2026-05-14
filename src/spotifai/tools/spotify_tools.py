import os
import re
import spotipy
from dotenv import load_dotenv
from crewai.tools import tool
from spotipy.oauth2 import SpotifyOAuth
from spotifai.models import PlaylistResult

load_dotenv()

def get_spotify_client():
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope="playlist-modify-private playlist-modify-public"
        )
    )

@tool("Search tracks on Spotify")
def search_tracks(query: str) -> str:
    """
    Search for tracks on Spotify.
    The 'query' parameter must be a plain text search string (NOT JSON).
    Use natural keywords like genre, artist, mood, or decade.
    """
    sp = get_spotify_client()
    results = sp.search(q=query, type="track", limit=20)
    tracks = results.get("tracks", {}).get("items", [])
    output = []
    for t in tracks:
        artist_names = ", ".join(a["name"] for a in t["artists"])
        output.append(
            f"- {t['name']} by {artist_names} (ID: {t['id']})"
        )
    return "\n".join(output) if output else "No tracks found."

@tool("Get track audio features on Spotify")
def get_track_analysis(track_id: str) -> str:
    """
    Get audio features for a Spotify track.
    The 'track_id' parameter is the Spotify track ID (NOT a URL).
    Example: "6rqhFgbbKwnb9MLmUQDhG6"
    """
    sp = get_spotify_client()
    features = sp.audio_features([track_id])[0]
    if not features:
        return "Track not found or no audio features available."

    return (
        f"Audio features for track ID {track_id}:\n"
        f"- Danceability: {features['danceability']}\n"
        f"- Energy: {features['energy']}\n"
        f"- Tempo: {features['tempo']} BPM\n"
        f"- Valence: {features['valence']}\n"
        f"- Acousticness: {features['acousticness']}\n"
        f"- Instrumentalness: {features['instrumentalness']}\n"
        f"- Liveness: {features['liveness']}\n"
        f"- Speechiness: {features['speechiness']}"
    )

@tool("Create playlist on Spotify")
def create_playlist(name: str = "SpotifAI Playlist") -> PlaylistResult:
    """
    Creates a Spotify playlist. Run this ONLY ONCE.
    The 'name' parameter is the playlist name (plain text string). Optional.
    Returns a PlaylistResult directly.
    """
    sp = get_spotify_client()

    # Use /me/playlists endpoint
    playlist = sp._post("me/playlists", payload={
        "name": name,
        "public": True,
        "description": "Playlist generada automaticament per SpotifAI"
    })

    playlist_id = playlist["id"]
    playlist_url = playlist["external_urls"]["spotify"]
    if not playlist_id or not playlist_url:
        return PlaylistResult(status="FAILED")

    return PlaylistResult(
        status="DONE",
        playlist_id=playlist_id,
        playlist_url=playlist_url,
        tracks_added=0,
    )

@tool("Add tracks to playlist on Spotify")
def add_tracks_to_playlist(playlist_id: str, track_ids: str) -> PlaylistResult:
    """
    Adds tracks to an existing Spotify playlist.
    The 'playlist_id' parameter is the ID returned by the 'Create playlist on Spotify' tool.
    The 'track_ids' parameter is a comma-separated string of Spotify track IDs.
    Returns a PlaylistResult directly.
    """
    pid = playlist_id.strip()
    ids = [
        track_id.strip()
        for track_id in track_ids.split(",")
        if len(track_id.strip()) == 22 and track_id.strip().isalnum()
    ]

    if not pid or not ids:
        return PlaylistResult(status="FAILED", playlist_id=pid or None)

    sp = get_spotify_client()
    sp.playlist_add_items(pid, ids)

    return PlaylistResult(status="DONE", playlist_id=pid, tracks_added=len(ids))
