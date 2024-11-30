# music/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('link-spotify/', views.link_spotify, name='link_spotify'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
    path('contact/', views.contact_developers, name='contact_developers'),
]
