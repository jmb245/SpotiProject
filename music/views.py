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

    # Extract authorization code from the URL
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Spotify authorization failed. Please try again.')
        return redirect('settings')

    # Exchange authorization code for access token
    token_url = 'https://accounts.spotify.com/api/token'
    redirect_uri = settings.SPOTIFY_REDIRECT_URI
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    }
    response = requests.post(token_url, data=payload)
    if response.status_code != 200:
        messages.error(request, 'Spotify token exchange failed. Please try again.')
        return redirect('settings')

    token_data = response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    spotify_user_url = "https://api.spotify.com/v1/me"

    # Fetch Spotify user profile
    spotify_user_response = requests.get(
        spotify_user_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if spotify_user_response.status_code != 200:
        messages.error(request, 'Failed to fetch Spotify user profile. Please try again.')
        return redirect('settings')

    spotify_user_data = spotify_user_response.json()
    spotify_uid = spotify_user_data['id']

    # Check if a SocialAccount already exists for this Spotify UID
    social_account = SocialAccount.objects.filter(provider='spotify', uid=spotify_uid).first()

    if social_account:
        # If the social account already exists, associate it with the current user
        if social_account.user != user:
            messages.error(request, 'This Spotify account is already linked to another user.')
            return redirect('settings')
    else:
        # Create a new SocialAccount and associate it with the user
        social_account = SocialAccount.objects.create(
            user=user,
            provider='spotify',
            uid=spotify_uid,
            extra_data=spotify_user_data,
        )

    # Save or update the social token
    social_token, _ = SocialToken.objects.get_or_create(account=social_account)
    social_token.token = access_token
    social_token.token_secret = refresh_token
    social_token.save()

    messages.success(request, 'Spotify account successfully linked!')
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

            # Define the token URL
            token_url = "https://accounts.spotify.com/api/token"

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

    # Format top tracks for the template
    formatted_top_tracks = [
        {
            "id": track.get("id"),
            "name": track.get("name"),
            "artist": track.get("artists", [{}])[0].get("name", ""),
            "album": track.get("album", {}).get("name", ""),
            "album_image": track.get("album", {}).get("images", [{}])[0].get("url", ""),
        }
        for track in top_tracks
    ]

    # Translate context messages
    translated_message = _("Welcome to Spotify Wrapped!")

    context = {
        "top_artists": top_artists,
        "top_genres": top_genres,
        "top_albums": top_albums.values(),
        "top_tracks": formatted_top_tracks,
        "recent_tracks": recent_tracks,
        "playlists": playlists,
        "message": translated_message,  # Add translated message
    }

    return render(request, 'music/home.html', context)



def contact_developers(request):
    if request.method == 'POST':
        # Process feedback form
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        if name and email and message:
            try:
                # Send email or process feedback
                send_mail(
                    subject=f"Feedback from {name}",
                    message=message,
                    from_email=email,
                    recipient_list=['team@developers.com'],  # Replace with your team's email
                )
                messages.success(request, "Thank you for your feedback!")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            messages.error(request, "Please fill out all fields.")

    # Example team data for template
    developers = [
        {"name": "Jad Matthew Bardawil", "role": "Add role",
         "bio": "Add bio.", "email": "Add email"},
        {"name": "Benjamin Yohros", "role": "Add role",
         "bio": "Add bio.", "email": "Add email"},
        {"name": "Heeyoon Shin", "role": "Add role",
         "bio": "Add bio.", "email": "Add email"},
        {"name": "Natalie Burstein", "role": "Add role",
         "bio": "Add bio.", "email": "Add email"},
        {"name": "Emily Prieto", "role": "Add role",
         "bio": "Add bio.", "email": "Add email"},
    ]

    return render(request, 'music/contact_developers.html', {"developers": developers})