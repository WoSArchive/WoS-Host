from django.db.models.signals import post_save
from django.contrib.auth.models import User
from .storage import OverwriteStorage
from django.utils.text import slugify
from datetime import date, timedelta
from django.dispatch import receiver
from django.db import models

# Initialize custom storage for file overwrites
overwrite_storage = OverwriteStorage()


def user_zip_path(instance, filename):
    """Generate upload path for world ZIP files: media/user_<id>/slot_<id>/world.zip"""
    return f"user_{instance.owner.id}/slot_{instance.id}/world.zip"


class UserProfile(models.Model):
    """Extended user profile with creator verification and slot limits."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified_creator = models.BooleanField(default=False)
    max_world_slots = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class WorldSlot(models.Model):
    """A world upload slot that can contain either a ZIP file or external URL."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    world_name = models.SlugField(
        max_length=100,
        help_text="Unique name used in URLs. Only letters, numbers, dashes or underscores.",
        unique=True
    )
    version = models.CharField(max_length=50)
    dev_name = models.CharField(max_length=100, blank=True)
    zip_file = models.FileField(
        upload_to=user_zip_path,
        blank=True,
        storage=overwrite_storage
    )
    self_hosted_url = models.URLField(
        blank=True,
        help_text="Optional external link for self-hosted world ZIP"
    )
    max_file_size_mb = models.IntegerField(default=100)
    uploaded_at = models.DateTimeField(auto_now=True)
    last_updated = models.DateField(
        blank=True,
        null=True,
        help_text="Optional manual override for update date. Defaults to upload date."
    )
    download_slug = models.SlugField(max_length=200, unique=True, blank=True)

    def save(self, *args, **kwargs):
        """Generate download slug and set default last_updated date."""
        # Create download slug from dev_name and world_name
        if self.dev_name and self.world_name:
            self.download_slug = slugify(f"{self.dev_name}_{self.world_name}")
        elif self.world_name:
            self.download_slug = slugify(self.world_name)

        # Set default last_updated to today if not specified
        if not self.last_updated:
            self.last_updated = date.today()

        super().save(*args, **kwargs)

    def is_self_hosted(self):
        """Check if this world uses external hosting instead of uploaded file."""
        return bool(self.self_hosted_url)

    def __str__(self):
        return f"{self.owner.username} - {self.world_name} v{self.version}"


class NavSection(models.Model):
    """Top-level navigation sections that can have dropdowns or direct links."""
    title = models.CharField(max_length=50)
    url = models.CharField(
        max_length=200,
        blank=True,
        help_text="Internal or external URL. Leave blank if this section is a dropdown."
    )
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.title


class NavLink(models.Model):
    """Individual navigation links within dropdown sections."""
    section = models.ForeignKey(NavSection, related_name="links", on_delete=models.CASCADE)
    label = models.CharField(max_length=100)
    url = models.CharField(
        max_length=200,
        help_text="Internal or external URL (e.g. /dashboard/ or https://...)"
    )
    order = models.IntegerField(default=0)
    external = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.label} → {self.url}"


class PageAccessLog(models.Model):
    """Log entry for tracking page access and HTTP requests."""
    timestamp = models.DateTimeField(auto_now_add=True)
    path = models.CharField(max_length=512)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    user_agent = models.TextField(blank=True)
    referrer = models.TextField(blank=True)

    def __str__(self):
        return f"[{self.status_code}] {self.method} {self.path} @ {self.timestamp}"


class WeeklyTrafficSummary(models.Model):
    """Aggregated weekly traffic statistics for performance monitoring."""
    week_start = models.DateField(unique=True)  # Monday of the week
    total_requests = models.PositiveIntegerField(default=0)
    total_404s = models.PositiveIntegerField(default=0)
    total_200s = models.PositiveIntegerField(default=0)
    total_other = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Week of {self.week_start} — {self.total_requests} requests"

    @staticmethod
    def get_week_start(today=None):
        """Calculate the Monday date for a given date's week."""
        if not today:
            today = date.today()
        return today - timedelta(days=today.weekday())

class ImageLinks(models.Model):
    background = models.URLField(default='https://i14.servimg.com/u/f14/17/55/69/45/evergr10.jpg')
    avatar = models.URLField(default='https://avatars.githubusercontent.com/u/57301293?v=4')
    def save(self, *a, **kw): self.pk = 1; super().save(*a, **kw)
    @classmethod
    def get(cls): return cls.objects.get_or_create(pk=1)[0]
    def __str__(self): return "Image Links"
    class Meta: verbose_name = verbose_name_plural = "Image Links"

# Signal handlers for automatic user profile creation
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure UserProfile is saved when User is saved."""
    instance.userprofile.save()