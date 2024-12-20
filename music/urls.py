# music/urls.py

from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('link-spotify/', views.link_spotify, name='link_spotify'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
    path('generate-wrap/', views.generate_wrap, name='generate_wrap'),
    path('wrap/<int:wrap_id>/', views.view_wrap, name='view_wrap'),
    path('wrap/<int:wrap_id>/delete/', views.delete_wrap, name='delete_wrap'),
    path('generate-holiday-wrap/', views.generate_wrap, {'holiday': True}, name='generate_holiday_wrap'),
    path('contact/', views.contact_developer, name='contact_developer'),
    path('audio_guess/', views.audio_guess, name='audio_guess'),
    path('check/', views.check_answer, name='check_answer'),
    path('set_language/', views.set_language, name='set_language'),
    path('change-language/<str:lang_code>/', views.change_language, name='change_language'),
    path('i18n/', include('django.conf.urls.i18n')),

]
