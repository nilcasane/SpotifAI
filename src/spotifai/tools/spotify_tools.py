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
    Search for tracks on Spotify
    """
    def _run(query: str) -> str:
        sp = get_spotify_client()
        results = sp.search(q=query, type="track", limit=10)
        return results
    
    return _run(query)

@tool("Create playlist on Spotify")
def create_playlist(name: str) -> str:
    """
    Creates a Spotify playlist and returns its URL.
    """
    sp = get_spotify_client()
    user_id = os.getenv("SPOTIFY_USERNAME")

    playlist = sp.user_playlist_create(
        user=user_id,
        name=name,
        public=False,
        description="Playlist generada automàticament per SpotifAI"
    )

    return playlist["external_urls"]["spotify"]