from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import uuid


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    def __str__(self):
        return self.user.username



class PendingRegistration(models.Model):

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    username = models.CharField(
        max_length=150
    )

    email = models.EmailField()

    password_hash = models.CharField(
        max_length=255
    )

    verification_code_hash = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveSmallIntegerField(
        default=0
    )


    def __str__(self):
        return self.email