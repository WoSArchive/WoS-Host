from django.contrib import admin
from .models import UserProfile, WorldSlot, NavSection, NavLink, PageAccessLog, WeeklyTrafficSummary

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified_creator', 'max_world_slots')
    list_editable = ('is_verified_creator', 'max_world_slots')
    search_fields = ('user__username',)

@admin.register(WorldSlot)
class WorldSlotAdmin(admin.ModelAdmin):
    list_display = (
        'owner',
        'world_name',
        'version',
        'dev_name',
        'max_file_size_mb',
        'uploaded_at',
        'last_updated',       # ✅ Add to list
        'download_slug',
        'self_hosted_url',
    )
    list_editable = ('max_file_size_mb', 'last_updated')  # ✅ Allow editing from list view
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
        'last_updated',       # ✅ Editable in detail view
    )

class NavLinkInline(admin.TabularInline):
    model = NavLink
    extra = 1
    fields = ('label', 'url', 'order', 'external')
    show_change_link = True

@admin.register(NavSection)
class NavSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'order', 'has_dropdown')
    ordering = ('order',)
    inlines = [NavLinkInline]

    def has_dropdown(self, obj):
        return obj.links.exists()
    has_dropdown.boolean = True
    has_dropdown.short_description = "Dropdown?"

@admin.register(NavLink)
class NavLinkAdmin(admin.ModelAdmin):
    list_display = ('label', 'section', 'url', 'external', 'order')
    list_filter = ('section', 'external')
    search_fields = ('label', 'url')
    ordering = ('section__order', 'order')

@admin.register(PageAccessLog)
class PageAccessLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'path', 'method', 'status_code')
    list_filter = ('status_code', 'method')
    search_fields = ('path', 'user_agent', 'referrer')


@admin.register(WeeklyTrafficSummary)
class WeeklyTrafficSummaryAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'total_requests', 'total_200s', 'total_404s', 'total_other')
    ordering = ('-week_start',)