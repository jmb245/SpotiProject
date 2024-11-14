from django.contrib import admin
from django.urls import path, include
from music import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('music.urls')),  # Your app URLs
    path('accounts/', include('allauth.urls')),  # Include allauth URLs
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),  # Explicit callback
]
