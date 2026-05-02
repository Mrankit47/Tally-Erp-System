"""
Management command to create a default superuser during deployment.

Reads credentials from environment variables:
    DJANGO_SUPERUSER_USERNAME
    DJANGO_SUPERUSER_EMAIL
    DJANGO_SUPERUSER_PASSWORD

Idempotent — skips creation if the user already exists.
Designed for headless environments like Render (no shell access).
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a default superuser from environment variables (idempotent)."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        # ── Validate ────────────────────────────────────────────────────
        if not all([username, email, password]):
            self.stderr.write(
                self.style.WARNING(
                    "WARNING: Skipping superuser creation — one or more env vars missing:\n"
                    "   DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD"
                )
            )
            return

        # ── Create or skip ──────────────────────────────────────────────
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.SUCCESS(
                    f'SUCCESS: Superuser "{username}" already exists — skipping.'
                )
            )
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'SUCCESS: Superuser "{username}" created successfully.'
                )
            )
