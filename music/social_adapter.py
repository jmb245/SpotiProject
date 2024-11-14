from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect


class NoSignupSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Ensure this flow only proceeds if the user is logged in
        if not request.user.is_authenticated:
            # Redirect to the login page if the user is not logged in
            raise ImmediateHttpResponse(redirect('login'))

        # If the user is authenticated and already linked, prevent duplicate linking
        if sociallogin.is_existing:
            raise ImmediateHttpResponse(redirect('home'))

        # If a logged-in user does not have an associated social account, allow linking
        sociallogin.connect(request, request.user)
