from .models import UserProfile, WorldSlot, NavSection, NavLink, PageAccessLog, WeeklyTrafficSummary, ImageLinks
from django.contrib import admin

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for managing user profiles and creator verification."""
    list_display = ('user', 'is_verified_creator', 'max_world_slots')
    list_editable = ('is_verified_creator', 'max_world_slots')
    search_fields = ('user__username',)


@admin.register(WorldSlot)
class WorldSlotAdmin(admin.ModelAdmin):
    """Admin interface for managing world upload slots."""
    list_display = (
        'owner',
        'world_name',
        'version',
        'dev_name',
        'max_file_size_mb',
        'uploaded_at',
        'last_updated',
        'download_slug',
        'self_hosted_url',
    )
    list_editable = ('max_file_size_mb', 'last_updated')
    search_fields = (
        'owner__username',
        'world_name',
        'dev_name',
        'download_slug',
        'self_hosted_url'
    )
    fields = (
        'owner',
        'world_name',
        'version',
        'dev_name',
        'zip_file',
        'max_file_size_mb',
        'self_hosted_url',
        'last_updated',
    )


class NavLinkInline(admin.TabularInline):
    """Inline editor for navigation links within sections."""
    model = NavLink
    extra = 1
    fields = ('label', 'url', 'order', 'external')
    show_change_link = True


@admin.register(NavSection)
class NavSectionAdmin(admin.ModelAdmin):
    """Admin interface for managing navigation sections and their dropdown links."""
    list_display = ('title', 'url', 'order', 'has_dropdown')
    ordering = ('order',)
    inlines = [NavLinkInline]

    def has_dropdown(self, obj):
        """Check if this navigation section contains dropdown links."""
        return obj.links.exists()
    has_dropdown.boolean = True
    has_dropdown.short_description = "Dropdown?"


@admin.register(NavLink)
class NavLinkAdmin(admin.ModelAdmin):
    """Admin interface for managing individual navigation links."""
    list_display = ('label', 'section', 'url', 'external', 'order')
    list_filter = ('section', 'external')
    search_fields = ('label', 'url')
    ordering = ('section__order', 'order')


@admin.register(PageAccessLog)
class PageAccessLogAdmin(admin.ModelAdmin):
    """Admin interface for viewing page access logs and traffic analysis."""
    list_display = ('timestamp', 'path', 'method', 'status_code')
    list_filter = ('status_code', 'method')
    search_fields = ('path', 'user_agent', 'referrer')


@admin.register(WeeklyTrafficSummary)
class WeeklyTrafficSummaryAdmin(admin.ModelAdmin):
    """Admin interface for viewing weekly traffic summary reports."""
    list_display = ('week_start', 'total_requests', 'total_200s', 'total_404s', 'total_other')
    ordering = ('-week_start',)

@admin.register(ImageLinks)
class ImageLinksAdmin(admin.ModelAdmin):
    fields = ('background', 'avatar')
