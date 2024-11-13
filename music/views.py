from django.shortcuts import redirect, render
from django.http import JsonResponse
from collections import Counter
import requests
import logging
import os
from django.http import HttpRequest

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

# Check for missing environment variables
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET or not SPOTIFY_REDIRECT_URI:
    logger.error("Spotify credentials are missing. Check your environment variables.")


def spotify_login(request):
    scopes = "user-read-recently-played user-top-read user-library-read"
    spotify_auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?response_type=code&client_id={SPOTIFY_CLIENT_ID}"
        f"&scope={scopes}&redirect_uri={SPOTIFY_REDIRECT_URI}"
        f"&show_dialog=true"
    )

    # Log the full Spotify authorization URL to check scopes
    logger.info(f"Spotify authorization URL: {spotify_auth_url}")

    return redirect(spotify_auth_url)


def spotify_callback(request):
    code = request.GET.get('code')
    logger.info(f"Authorization code received: {code}")
    token_url = 'https://accounts.spotify.com/api/token'

    response = requests.post(
        token_url,
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URI,
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET
        }
    )

    # Log the token response status and content
    logger.info(f"Token response status: {response.status_code}")
    logger.info(f"Token response content: {response.text}")

    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get('access_token')
        logger.info(f"Access token received: {access_token}")
        request.session['access_token'] = access_token
        return redirect('home')
    else:
        logger.error("Spotify authentication failed.")
        return JsonResponse({'error': 'Spotify authentication failed'}, status=response.status_code)


def home_view(request):
    access_token = request.session.get('access_token')

    if not access_token:
        logger.info("No access token found, redirecting to login page.")
        return redirect('login_page')

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Fetch top artists
    response_artists = requests.get('https://api.spotify.com/v1/me/top/artists', headers=headers)
    top_artists = response_artists.json().get('items', []) if response_artists.status_code == 200 else []
    genres = [genre for artist in top_artists for genre in artist.get('genres', [])]
    top_genres = [genre for genre, _ in Counter(genres).most_common(5)]  # Top 5 genres

    # Fetch top tracks (songs)
    response_tracks = requests.get('https://api.spotify.com/v1/me/top/tracks', headers=headers)
    top_tracks = response_tracks.json().get('items', []) if response_tracks.status_code == 200 else []
    top_albums = list({track['album']['name']: track['album'] for track in top_tracks}.values())[:5]  # Unique albums, top 5

    # Fetch recently played tracks
    response_recent = requests.get('https://api.spotify.com/v1/me/player/recently-played', headers=headers)
    recent_tracks = response_recent.json().get('items', []) if response_recent.status_code == 200 else []

    # Fetch user playlists
    response_playlists = requests.get('https://api.spotify.com/v1/me/playlists', headers=headers)
    playlists = response_playlists.json().get('items', []) if response_playlists.status_code == 200 else []

    context = {
        "wrapped_data": "Your custom Wrapped data here",
        "share_url": request.build_absolute_uri(),
    }

    return render(request, 'music/home.html', {
        'top_artists': top_artists,
        'top_tracks': top_tracks,
        'recent_tracks': recent_tracks,
        'playlists': playlists,
        'top_genres': top_genres,
        'top_albums': top_albums,
    })

def logout_view(request):
    # Log before clearing session data
    logger.info("Logging out: Clearing session data")

    # Clear the session data, including the access token
    request.session.flush()


    # Directly print the session data after flushing
    logger.info(f"Session data after flush: {request.session.items()}")

    # Redirect to Spotify login and log redirection
    logger.info("Redirecting to Spotify login page.")
    return redirect('home')


def login_page(request):
    return render(request, 'music/login.html')
    return render(request, 'music/login.html')

