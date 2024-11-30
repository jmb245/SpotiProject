# music/models.py
from django.db import models
from django.contrib.auth.models import User

class Wrap(models.Model):
    WRAP_TYPES = [
        ('regular', 'Regular'),
        ('holiday', 'Holiday'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wraps")
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.JSONField()  # Store wrap data as JSON
    wrap_type = models.CharField(max_length=20, choices=WRAP_TYPES, default='regular')  # Added field

    def __str__(self):
        return f"{self.title} ({self.wrap_type}) by {self.user.username}"

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} by {self.name}"

