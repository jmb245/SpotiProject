# views.py

import logging
import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from allauth.socialaccount.models import SocialToken, SocialAccount
from django.urls import reverse
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.conf import settings
from django.utils.translation import gettext as _


logger = logging.getLogger(__name__)

# User Authentication Views

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('home')
        else:
            messages.error(request, 'There was an error with your signup.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'music/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Logged in successfully.')
            return redirect('home')
        else:
            messages.error(request, 'There was an error with your login.')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'music/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('login')

# Settings View

@login_required
def settings_view(request):
    return redirect('/accounts/spotify/login/')

# Spotify Integration Views

@login_required
def link_spotify(request):
    """Initiate Spotify link process"""
    return redirect('/accounts/spotify/login/')

@login_required
def spotify_callback(request):
    user = request.user
    logger.info(f"User: {user} has accessed the callback")

    # Retrieve the authorization code from the callback URL
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Spotify authorization failed. Please try again.')
        return redirect('settings')

    # Manually request the access token from Spotify
    token_url = 'https://accounts.spotify.com/api/token'
    redirect_uri = settings.SPOTIFY_REDIRECT_URI
    client_id = settings.SPOTIFY_CLIENT_ID
    client_secret = settings.SPOTIFY_CLIENT_SECRET
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret,
    }

    # Request the token from Spotify
    response = requests.post(token_url, data=payload)
    if response.status_code != 200:
        logger.error(f"Failed to get Spotify token. Status code: {response.status_code}")
        messages.error(request, 'Spotify linking failed. Please try again.')
        return redirect('settings')

    # Parse the token data
    token_data = response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')

    if not access_token:
        logger.error("No access token returned from Spotify.")
        messages.error(request, 'Spotify linking failed. Please try again.')
        return redirect('settings')

    # Save or update the token in the database
    social_account, _ = SocialAccount.objects.get_or_create(user=user, provider='spotify')
    social_token, _ = SocialToken.objects.get_or_create(account=social_account)
    social_token.token = access_token
    social_token.token_secret = refresh_token  # Use token_secret to store refresh token
    social_token.save()

    logger.info(f"Spotify token successfully stored for user {user.username}")
    messages.success(request, 'Spotify successfully linked!')
    return redirect('home')

@login_required
def check_spotify_token(request):
    user = request.user
    try:
        # Retrieve the existing token
        social_token = SocialToken.objects.get(account__user=user, account__provider='spotify')

        # Validate the token with Spotify API
        response = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {social_token.token}"}
        )

        # If the token is valid, return success
        if response.status_code == 200:
            return True

        # If the token is expired, attempt to refresh it
        elif response.status_code == 401:
            logger.info(f"Spotify token expired for user {user.username}. Refreshing token...")
            refresh_payload = {
                'grant_type': 'refresh_token',
                'refresh_token': social_token.token_secret,
                'client_id': settings.SPOTIFY_CLIENT_ID,
                'client_secret': settings.SPOTIFY_CLIENT_SECRET,
            }
            refresh_response = requests.post(token_url, data=refresh_payload)

            if refresh_response.status_code == 200:
                refresh_data = refresh_response.json()
                social_token.token = refresh_data.get('access_token')
                social_token.save()
                logger.info(f"Spotify token refreshed successfully for user {user.username}")
                return True
            else:
                logger.error(f"Failed to refresh Spotify token for user {user.username}")
                return False

        else:
            logger.error(f"Unexpected response from Spotify API: {response.status_code}")
            return False

    except SocialToken.DoesNotExist:
        logger.error(f"No Spotify token found for user {user.username}")
        return False

# Data Fetching for Top Artists

def fetch_spotify_data(user):
    social_account = SocialAccount.objects.filter(user=user, provider='spotify').first()
    token = SocialToken.objects.filter(account=social_account).first() if social_account else None
    if token:
        headers = {"Authorization": f"Bearer {token.token}"}
        response = requests.get("https://api.spotify.com/v1/me/top/artists", headers=headers, params={"limit": 5})
        if response.status_code == 200:
            return response.json().get('items', [])
        else:
            logger.warning(f"Failed to fetch data from Spotify. Status code: {response.status_code}")
    else:
        logger.warning("No Spotify token found for user.")
    return []

# Homepage Display
def fetch_spotify_data(url, user, params=None):
    social_account = SocialToken.objects.filter(account__user=user, account__provider='spotify').first()
    if social_account:
        headers = {"Authorization": f"Bearer {social_account.token}"}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch data from Spotify. Status code: {response.status_code}")
    else:
        logger.warning("No Spotify token found for user.")
    return {}
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    # Fetch Spotify data for various sections
    top_artists_data = fetch_spotify_data(
        "https://api.spotify.com/v1/me/top/artists", request.user, params={"limit": 5}
    )
    top_tracks_data = fetch_spotify_data(
        "https://api.spotify.com/v1/me/top/tracks", request.user, params={"limit": 5}
    )
    recent_tracks_data = fetch_spotify_data(
        "https://api.spotify.com/v1/me/player/recently-played", request.user, params={"limit": 5}
    )
    playlists_data = fetch_spotify_data(
        "https://api.spotify.com/v1/me/playlists", request.user, params={"limit": 5}
    )

    # Parse data for easy use in the template
    top_artists = top_artists_data.get("items", [])
    top_tracks = top_tracks_data.get("items", [])
    recent_tracks = recent_tracks_data.get("items", [])
    playlists = playlists_data.get("items", [])

    # Extract unique genres from top artists
    top_genres = set()
    for artist in top_artists:
        top_genres.update(artist.get("genres", []))
    top_genres = list(top_genres)

    # Extract top albums from top tracks
    top_albums = {track['album']['name']: track['album'] for track in top_tracks}

    # Translate context messages
    translated_message = _("Welcome to Spotify Wrapped!")

    context = {
        "top_artists": top_artists,
        "top_genres": top_genres,
        "top_albums": top_albums.values(),
        "top_tracks": top_tracks,
        "recent_tracks": recent_tracks,
        "playlists": playlists,
        "message": translated_message,  # Add translated message
    }

    return render(request, 'music/home.html', context)
