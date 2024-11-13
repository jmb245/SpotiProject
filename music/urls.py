from django.urls import path
from . import views

urlpatterns = [
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('music/callback/', views.spotify_callback, name='spotify_callback'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home_view, name='home'),  # Home page
    path('login/', views.login_page, name='login_page'),  # Login page URL
]
