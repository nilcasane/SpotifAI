import os
import spotipy
from dotenv import load_dotenv
from crewai.tools import tool
from spotipy.oauth2 import SpotifyOAuth

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
    results = sp.search(q=query, type="track", limit=10)
    tracks = results.get("tracks", {}).get("items", [])
    output = []
    for t in tracks:
        artist_names = ", ".join(a["name"] for a in t["artists"])
        output.append(
            f"- {t['name']} by {artist_names} (ID: {t['id']})"
        )
    return "\n".join(output) if output else "No tracks found."

@tool("Create playlist on Spotify")
def create_playlist(name: str = "SpotifAI Playlist") -> str:
    """
    Creates a Spotify playlist. Run this ONLY ONCE.
    The 'name' parameter is the playlist name (plain text string). Optional.
    Returns the Playlist ID and its URL.
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
    return f"Playlist created successfully. PLAYLIST_ID: {playlist_id} URL: {playlist_url}"

@tool("Add tracks to playlist on Spotify")
def add_tracks_to_playlist(playlist_id: str, track_ids: str) -> str:
    """
    Adds tracks to an existing Spotify playlist.
    The 'playlist_id' parameter is the ID returned by the 'Create playlist on Spotify' tool.
    The 'track_ids' parameter is a comma-separated string of Spotify track IDs.
    Example: playlist_id="3PsUvVljRMBS4zLm2B68Ht", track_ids="6rqhFgbbKwnb9MLmUQDhG6,4u7EnebtB2gSQ7sXFoGx8V"
    """
    sp = get_spotify_client()
    
    # Strip any extra text that the LLM might have included with the playlist ID
    pid = playlist_id.replace("PLAYLIST_ID:", "").strip()

    ids = [tid.strip() for tid in track_ids.split(",") if tid.strip()]
    if ids:
        sp.playlist_add_items(pid, ids)

    return f"Added {len(ids)} tracks to the playlist."