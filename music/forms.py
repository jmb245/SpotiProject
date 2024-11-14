# music/forms.py

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

class CustomUserCreationForm(UserCreationForm):
    usable_password = None
    class Meta:
        model = User
        fields = ['username', 'email', 'password1',]  # Only include fields needed for signup

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
