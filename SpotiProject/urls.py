from django.contrib import admin
from django.urls import path, include
from music import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('music.urls')),
    path('accounts/', include('allauth.urls')),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
]
