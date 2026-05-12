"""
Debug script: check token scopes and try alternative playlist creation methods.
"""
import os
import json
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

print("=" * 60)
print("SPOTIFY PLAYLIST CREATION DEBUG")
print("=" * 60)

auth_manager = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope="playlist-modify-private playlist-modify-public"
)

sp = spotipy.Spotify(auth_manager=auth_manager)

# 1. Check actual token scopes
print("\n--- Token Info ---")
token_info = auth_manager.get_cached_token()
if token_info:
    print(f"Scopes in token:  '{token_info.get('scope', 'NONE')}'")
    print(f"Token expires at: {token_info.get('expires_at')}")
    required = {"playlist-modify-private", "playlist-modify-public"}
    actual = set(token_info.get("scope", "").split())
    missing = required - actual
    if missing:
        print(f"⚠️  MISSING SCOPES: {missing}")
        print(f"   Delete .cache and re-authenticate!")
    else:
        print(f"✅ All required scopes present")
else:
    print("❌ No cached token found!")

# 2. Check user
me = sp.current_user()
print(f"\n--- User Info ---")
print(f"User ID:      {me['id']}")
print(f"Display name: {me.get('display_name')}")
print(f"Product:      {me.get('product')}")
print(f"Country:      {me.get('country')}")

# 3. Try with sp.user_playlist_create
print(f"\n--- Test 1: user_playlist_create(user='{me['id']}') ---")
try:
    playlist = sp.user_playlist_create(
        user=me['id'],
        name="SpotifAI Debug Test",
        public=False,
        description="Debug test"
    )
    print(f"✅ SUCCESS! Playlist: {playlist['external_urls']['spotify']}")
    sp.current_user_unfollow_playlist(playlist['id'])
    print("   (cleaned up)")
except spotipy.exceptions.SpotifyException as e:
    print(f"❌ FAILED: {e.http_status} - {e.reason}")
    print(f"   Headers: {e.headers}")
    # Try the /me endpoint directly
    print(f"\n--- Test 2: Direct POST to /me/playlists ---")
    try:
        import requests
        token = auth_manager.get_access_token(as_dict=False)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "name": "SpotifAI Debug Test 2",
            "public": False,
            "description": "Debug test via /me"
        }
        resp = requests.post(
            "https://api.spotify.com/v1/me/playlists",
            headers=headers,
            json=body
        )
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text[:500]}")
        if resp.status_code == 201:
            data = resp.json()
            print(f"✅ SUCCESS with /me/playlists!")
            sp.current_user_unfollow_playlist(data['id'])
            print("   (cleaned up)")
    except Exception as e2:
        print(f"❌ Also failed: {e2}")
