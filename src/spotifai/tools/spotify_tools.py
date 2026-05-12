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
            scope="playlist-modify-private,playlist-modify-public"
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

@tool("Create playlist and add tracks on Spotify")
def create_playlist_with_tracks(name: str, track_ids: str) -> str:
    """
    Creates a Spotify playlist and adds tracks to it in one step.
    The 'name' parameter is the playlist name (plain text string).
    The 'track_ids' parameter is a comma-separated string of Spotify track IDs.
    Example: track_ids="6rqhFgbbKwnb9MLmUQDhG6,4u7EnebtB2gSQ7sXFoGx8V"
    """
    sp = get_spotify_client()
    user_id = os.getenv("SPOTIFY_USERNAME")

    playlist = sp.user_playlist_create(
        user=user_id,
        name=name,
        public=False,
        collaborative=False,
        description="Playlist generada automaticament per SpotifAI"
    )

    print(playlist)

    playlist_id = playlist["id"]
    playlist_url = playlist["external_urls"]["spotify"]

    ids = [tid.strip() for tid in track_ids.split(",") if tid.strip()]
    if ids:
        sp.playlist_add_items(playlist_id, ids)

    return f"Playlist created: {playlist_url} - Added {len(ids)} tracks."