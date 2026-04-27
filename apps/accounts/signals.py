from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    """Auto-creates a profile for every new user."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
    else:
        # Ensure profile exists even for old users
        if not hasattr(instance, 'profile'):
            UserProfile.objects.get_or_create(user=instance)
