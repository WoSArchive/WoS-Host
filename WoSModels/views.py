from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, FileResponse, Http404, HttpResponseRedirect
from django.utils.text import slugify
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from .models import NavSection
from django.db.models import Q
import os
import shutil
import logging

from .models import UserProfile, WorldSlot
from .forms import SlotUploadForm

logger = logging.getLogger(__name__)

# Utility to count used slots (ZIP or URL counts as "used")
def get_used_slot_count(user):
    return WorldSlot.objects.filter(
        owner=user
    ).filter(
        Q(zip_file__isnull=False, zip_file__gt='') |
        Q(self_hosted_url__isnull=False, self_hosted_url__gt='')
    ).count()

# Auth page view
def auth(request):
    login_form = AuthenticationForm()
    signup_form = UserCreationForm()
    return render(request, 'auth.html', {
        'login_form': login_form,
        'signup_form': signup_form
    })

# Signup handler
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            logger.info(f"New user registered: {user.username} (ID: {user.id})")
            return redirect('dashboard')
        else:
            logger.warning(f"Failed signup attempt from {request.META.get('REMOTE_ADDR')}")
    return redirect('homepage')

# Login handler
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"User logged in: {user.username} (ID: {user.id})")
            return redirect('dashboard')
        else:
            logger.warning(f"Failed login attempt for username: {request.POST.get('username')} from {request.META.get('REMOTE_ADDR')}")
    return redirect('homepage')

# Logout handler
def logout_view(request):
    username = request.user.username if request.user.is_authenticated else "anonymous"
    logout(request)
    logger.info(f"User logged out: {username}")
    return redirect('homepage')

# Dashboard route
@login_required
def dashboard(request):
    profile = request.user.userprofile
    nav_sections = NavSection.objects.prefetch_related('links').order_by('order')

    if not profile.is_verified_creator:
        return render(request, 'dashboard_uv.html', {
            'profile': profile,
            'nav_sections': nav_sections
        })

    slots = request.user.worldslot_set.filter(
        Q(zip_file__isnull=False, zip_file__gt='') |
        Q(self_hosted_url__isnull=False, self_hosted_url__gt='')
    )

    return render(request, 'dashboard.html', {
        'profile': profile,
        'slots': slots,
        'nav_sections': nav_sections
    })

# Upload-to-slot handler
@login_required
def upload_to_slot(request, slot_id):
    try:
        slot = WorldSlot.objects.get(id=slot_id, owner=request.user)
    except WorldSlot.DoesNotExist:
        logger.warning(f"User {request.user.id} attempted to access non-existent or unauthorized slot {slot_id}")
        return HttpResponseForbidden("You don't have access to this slot.")

    if not request.user.userprofile.is_verified_creator:
        logger.warning(f"Unverified user {request.user.id} attempted to upload to slot {slot_id}")
        return HttpResponseForbidden("You are not a verified creator.")

    if request.method == 'POST':
        form = SlotUploadForm(request.POST, request.FILES, instance=slot, slot=slot)
        if form.is_valid():
            slot = form.save(commit=False)

            # Clear previous values depending on what's being submitted
            if slot.zip_file:
                slot.self_hosted_url = ''
            elif slot.self_hosted_url:
                if slot.zip_file:
                    slot.zip_file.delete(save=False)
                slot.zip_file = None

            slot.save()
            logger.info(f"Slot {slot_id} updated by user {request.user.id}")
            messages.success(request, "World updated successfully!")
            return redirect('dashboard')
        else:
            logger.warning(f"Form validation failed for slot {slot_id} by user {request.user.id}: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            messages.error(request, "There was a problem with your update.")
            return redirect('dashboard')
    else:
        form = SlotUploadForm(instance=slot, slot=slot)

    return render(request, 'upload_to_slot.html', {
        'slot': slot,
        'form': form
    })

# Create new slot (from dashboard modal)
@login_required
def create_slot(request):
    profile = request.user.userprofile

    if not profile.is_verified_creator:
        logger.warning(f"Unverified user {request.user.id} attempted to create slot")
        return HttpResponseForbidden("You are not a verified creator.")

    used_slots = get_used_slot_count(request.user)
    if used_slots >= profile.max_world_slots:
        logger.warning(f"User {request.user.id} attempted to exceed slot limit ({used_slots}/{profile.max_world_slots})")
        return HttpResponseForbidden("You have no available upload slots.")

    if request.method == 'POST':
        form = SlotUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            slot = form.save(commit=False)
            slot.owner = request.user
            
            # Handle the world_name slugification
            if slot.world_name:
                original_name = slot.world_name
                slug_name = slugify(original_name)
                if slug_name != original_name:
                    slot.world_name = slug_name

            # Make sure only one is stored
            if slot.zip_file:
                slot.self_hosted_url = ''
            elif slot.self_hosted_url:
                slot.zip_file = None

            try:
                slot.save()
                logger.info(f"New slot created by user {request.user.id}: {slot.world_name}")
                messages.success(request, "World slot created successfully!")
                return redirect('dashboard')
            except Exception as e:
                logger.error(f"Error saving slot for user {request.user.id}: {str(e)}")
                messages.error(request, f"Error saving: {str(e)}")
                return redirect('dashboard')
        else:
            logger.warning(f"Form validation failed for new slot by user {request.user.id}: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            messages.error(request, "There was a problem with your upload.")
            return redirect('dashboard')

    return HttpResponseForbidden("Invalid request.")

# Serve download: redirects if URL, else sends ZIP
def serve_world_zip(request, slug):
    try:
        slot = WorldSlot.objects.get(download_slug=slug)
    except WorldSlot.DoesNotExist:
        logger.warning(f"Download attempt for non-existent slug: {slug}")
        raise Http404("World not found.")

    # Log download attempt
    logger.info(f"World download: {slug} from {request.META.get('REMOTE_ADDR')}")

    if slot.self_hosted_url:
        return HttpResponseRedirect(slot.self_hosted_url)

    if not slot.zip_file:
        logger.error(f"No zip file for slot {slot.id} ({slug})")
        raise Http404("No zip file associated.")

    zip_path = slot.zip_file.path
    if not os.path.exists(zip_path):
        logger.error(f"ZIP file does not exist: {zip_path}")
        raise Http404("ZIP file does not exist.")

    # Security check: ensure file is within expected directory
    try:
        expected_base = os.path.join(settings.MEDIA_ROOT, f"user_{slot.owner.id}")
        if not os.path.commonpath([zip_path, expected_base]) == expected_base:
            logger.error(f"Path traversal attempt detected: {zip_path}")
            raise Http404("Invalid file path.")
    except ValueError:
        logger.error(f"Path validation failed for: {zip_path}")
        raise Http404("Invalid file path.")

    return FileResponse(
        open(zip_path, 'rb'), 
        as_attachment=True, 
        filename=f"{slot.download_slug}.zip"
    )

# Delete slot (and associated files)
@login_required
def delete_slot_zip(request, slot_id):
    try:
        slot = WorldSlot.objects.get(id=slot_id, owner=request.user)
    except WorldSlot.DoesNotExist:
        logger.warning(f"User {request.user.id} attempted to delete non-existent or unauthorized slot {slot_id}")
        return HttpResponseForbidden("You don't have access to this slot.")

    if not request.user.userprofile.is_verified_creator:
        logger.warning(f"Unverified user {request.user.id} attempted to delete slot {slot_id}")
        return HttpResponseForbidden("You are not a verified creator.")

    if request.method == 'POST':
        world_name = slot.world_name
        
        # Delete uploaded ZIP
        if slot.zip_file and slot.zip_file.name:
            slot.zip_file.delete(save=False)

        # Remove slot directory
        slot_folder = os.path.join(settings.MEDIA_ROOT, f"user_{slot.owner.id}", f"slot_{slot.id}")
        if os.path.exists(slot_folder):
            try:
                shutil.rmtree(slot_folder)
            except Exception as e:
                logger.error(f"Failed to remove slot folder {slot_folder}: {e}")

        slot.delete()
        logger.info(f"Slot deleted by user {request.user.id}: {world_name} (slot {slot_id})")
        messages.success(request, "World upload deleted and slot has been freed.")
        return redirect('dashboard')

    return HttpResponseForbidden("Invalid request.")

def api_world_list(request):
    slots = WorldSlot.objects.filter(
        Q(zip_file__isnull=False, zip_file__gt='') |
        Q(self_hosted_url__isnull=False, self_hosted_url__gt='')
    ).order_by('world_name')

    data = []
    for slot in slots:
        data.append({
            'world_name': slot.world_name,
            'version': slot.version,
            'dev_name': slot.dev_name,
            'last_updated': slot.last_updated.strftime("%Y-%m-%d") if slot.last_updated else slot.uploaded_at.strftime("%Y-%m-%d"),
            'download_url': (
                slot.self_hosted_url
                if slot.self_hosted_url
                else request.build_absolute_uri(f"/worlds/{slot.download_slug}.zip")
            )
        })

    return JsonResponse(data, safe=False)

# Navigation context helper
def get_nav_context():
    return {
        'nav_sections': NavSection.objects.prefetch_related('links').order_by('order')
    }

def homepage(request):
    nav_sections = NavSection.objects.prefetch_related('links').order_by('order')
    return render(request, 'homepage.html', {'nav_sections': nav_sections})

def worlds_index(request):
    return render(request, 'worlds.html', {
        'nav_sections': NavSection.objects.prefetch_related('links').order_by('order')
    })

def athelias_quest(request):
    return render(request, 'AtheliasQuest.html', {
        'nav_sections': NavSection.objects.prefetch_related('links').order_by('order')
    })