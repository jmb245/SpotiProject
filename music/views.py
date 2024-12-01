# views.py

import logging
import random
from django.http import JsonResponse
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from allauth.socialaccount.models import SocialToken, SocialAccount
from django.urls import reverse
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.conf import settings
from .models import Wrap
from datetime import datetime, date
from .forms import ContactForm

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
@login_required
def home(request):
    wraps = Wrap.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'music/home.html', {'wraps': wraps})

@login_required
def generate_wrap(request):
    user = request.user
    logger.info(f"Generating a new wrap for user: {user.username}")

    # Check if today is a holiday
    holidays = {
        '10-31': 'Halloween',
        '12-25': 'Christmas',
    }

    # Override date for testing
    override_date = request.GET.get('override_date')
    today = datetime.strptime(override_date, '%m-%d').date() if override_date else datetime.now().date()

    holiday_name = holidays.get(today.strftime('%m-%d'), None)
    is_holiday_wrap = 'holiday' in request.GET or bool(holiday_name)

    # Fetch Spotify data
    top_artists_data = fetch_spotify_data("https://api.spotify.com/v1/me/top/artists", user, params={"limit": 5})
    top_tracks_data = fetch_spotify_data("https://api.spotify.com/v1/me/top/tracks", user, params={"limit": 5})
    recent_tracks_data = fetch_spotify_data("https://api.spotify.com/v1/me/player/recently-played", user,
                                            params={"limit": 5})
    playlists_data = fetch_spotify_data("https://api.spotify.com/v1/me/playlists", user, params={"limit": 5})

    # Parse data for slides
    slides = [
        {"title": "Welcome to Your Spotify Wrap", "content": ['Use the buttons below to navigate!']},
        {"title": "Are You Ready?", "content": ['Get ready to explore your Spotify activity!']},
        {"title": "Your Top Artists", "content": [artist['name'] for artist in top_artists_data.get('items', [])]},
        {"title": "Your Top Genres", "content": list(
            set(genre for artist in top_artists_data.get('items', []) for genre in artist.get('genres', [])))},
        {"title": "Your Top Albums",
         "content": list({track['album']['name'] for track in top_tracks_data.get('items', [])})},
        {"title": "Your Top Tracks", "content": [
            {
                "name": track['name'],
                "artist": track['artists'][0]['name'],
                "spotify_id": track['id'],
            } for track in top_tracks_data.get('items', [])
        ]},
        {"title": "Your Recently Played Tracks",
         "content": [f"{item['track']['name']} by {item['track']['artists'][0]['name']}" for item in
                     recent_tracks_data.get('items', [])]},
        {"title": "Your Playlists",
         "content": [f"{playlist['name']} - {playlist['tracks']['total']} tracks" for playlist in
                     playlists_data.get('items', [])]},
        {"title": "Thank You for Viewing", "content": ['We hope you enjoyed your Spotify wrap!']},
    ]

    # Add holiday greeting
    if is_holiday_wrap:
        holiday_greeting = f"Happy {holiday_name or 'Holiday'}!"
        slides.insert(0, {"title": holiday_greeting, "content": ["Enjoy your festive Spotify wrap!"]})
        slides.append({"title": "This Holiday Has Been Wrapped!", "content": ["🎄 Spread the joy with festive music! 🎃"]})

    # Save the wrap
    wrap = Wrap.objects.create(
        user=user,
        title=f"{'Holiday' if is_holiday_wrap else 'Spotify'} Wrap",
        content={"slides": slides},
        wrap_type='holiday' if is_holiday_wrap else 'regular'
    )
    messages.success(request, f"New {'Holiday' if is_holiday_wrap else ''} Wrap generated successfully!")
    return redirect('home')



@login_required
def delete_wrap(request, wrap_id):
    wrap = get_object_or_404(Wrap, id=wrap_id, user=request.user)
    wrap.delete()
    messages.success(request, 'Wrap deleted successfully!')
    return redirect('home')

@login_required
def view_wrap(request, wrap_id):
    wrap = get_object_or_404(Wrap, id=wrap_id, user=request.user)
    return render(request, 'music/view_wrap.html', {'wrap': wrap})

def contact_developer(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent to the developer!")
            return redirect('home')  # Redirect to home or any desired page
        else:
            messages.error(request, "There was an error with your submission. Please try again.")
    else:
        form = ContactForm()

    return render(request, 'music/contact.html', {'form': form})

def refresh_token(token_info):
    token_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token_info['refresh_token'],
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "client_secret": settings.SPOTIFY_CLIENT_SECRET,
    }
    response = requests.post(token_url, data=payload)
    return response.json()

@login_required
def musician_guess(request):
    token_info = request.session.get('token_info')
    if not token_info:
        return redirect('spotify_login')  # Ensure proper redirection

    # Refresh the token if expired
    if 'expires_in' in token_info and token_info['expires_in'] <= 0:
        token_info = refresh_token(token_info)
        request.session['token_info'] = token_info

    headers = {
        "Authorization": f"Bearer {token_info['access_token']}",
    }
    top_artists_url = "https://api.spotify.com/v1/me/top/artists"
    response = requests.get(top_artists_url, headers=headers, params={"limit": 10, "time_range": "medium_term"})

    if response.status_code == 401:  # Token might have expired
        return redirect('spotify_login')

    data = response.json()
    artist_names = [artist['name'] for artist in data['items']]

    if request.method == 'POST':
        user_guess = request.POST.get('guess').lower()
        if user_guess in (name.lower() for name in artist_names):
            message = "Correct! That artist is in your top 10."
        else:
            message = "Not quite! Try again."
        return render(request, 'music/musician_guess.html', {'message': message, 'artists': artist_names})

    return render(request, 'music/musician_guess.html', {'artists': artist_names})

@login_required
def audio_guess(request):
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('spotify_login')

    # Fetch user's top tracks
    headers = {"Authorization": f"Bearer {access_token}"}
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks?limit=10&time_range=short_term"
    response = requests.get(top_tracks_url, headers=headers)
    top_tracks = response.json()

    # Randomly select a song
    song = random.choice(top_tracks['items'])
    snippet_url = song.get('preview_url')
    options = [song['name']] + [random.choice(top_tracks['items'])['name'] for _ in range(3)]
    random.shuffle(options)

    context = {
        'snippet_url': snippet_url,
        'options': options,
        'answer': song['name'],
    }
    return render(request, 'music/audio_guess.html', context)

def check_answer(request):
    if request.method == 'POST':
        answer = request.POST.get('answer')
        user_guess = request.POST.get('guess')
        correct = answer == user_guess
        return JsonResponse({'correct': correct})