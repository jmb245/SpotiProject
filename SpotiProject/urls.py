from django.contrib import admin
from django.urls import path, include
from music import views
from django.conf.urls.i18n import i18n_patterns  # For i18n
from django.conf.urls import include as i18n_include

# Add main URLs
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Include allauth URLs
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),  # Explicit callback
    path('i18n/', i18n_include('django.conf.urls.i18n')),  # i18n endpoint for set_language
]

# Include i18n patterns
urlpatterns += i18n_patterns(
    path('', include('music.urls')),  # Your app URLs with language prefix
)
