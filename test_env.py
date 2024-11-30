# test_env.py
from decouple import config

print("DJANGO_SECRET_KEY:", config("DJANGO_SECRET_KEY", default="NOT FOUND"))
print("SPOTIFY_REDIRECT_URI:", config("SPOTIFY_REDIRECT_URI", default="NOT FOUND"))
