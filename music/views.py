# views.py

import logging
import requests
import urllib.parse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from allauth.socialaccount.models import SocialToken, SocialAccount
from django.urls import reverse
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.conf import settings

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
    return render('settings.html')

# Spotify Integration Views

def spotify_login(request):
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "scope": "user-read-email",
    }
    url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    return redirect(url)

def spotify_callback(request):
    code = request.GET.get('code')
    token_url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "client_secret": settings.SPOTIFY_CLIENT_SECRET,
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
        # Store these tokens in your database for the user
        return JsonResponse({"access_token": access_token, "refresh_token": refresh_token})
    else:
        return JsonResponse({"error": "Failed to authenticate"}, status=response.status_code)

def get_user_info(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info_url = "https://api.spotify.com/v1/me"
    response = requests.get(user_info_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

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
@login_required
def home(request):
    # Fetch Spotify data for various sections
    top_artists_data = fetch_spotify_data("https://api.spotify.com/v1/me/top/artists", request.user,
                                          params={"limit": 5})
    top_tracks_data = fetch_spotify_data("https://api.spotify.com/v1/me/top/tracks", request.user, params={"limit": 5})
    recent_tracks_data = fetch_spotify_data("https://api.spotify.com/v1/me/player/recently-played", request.user,
                                            params={"limit": 5})
    playlists_data = fetch_spotify_data("https://api.spotify.com/v1/me/playlists", request.user, params={"limit": 5})

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

    context = {
        "top_artists": top_artists,
        "top_genres": top_genres,
        "top_albums": top_albums.values(),
        "top_tracks": top_tracks,
        "recent_tracks": recent_tracks,
        "playlists": playlists,
    }

    return render(request, 'music/home.html', context)
