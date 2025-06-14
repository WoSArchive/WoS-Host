import os
import json
import logging
import pyzipper
import shutil
import tempfile
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from WoSModels.models import UserProfile, WorldSlot, NavSection, NavLink, ImageLinks
from django.utils.dateparse import parse_datetime, parse_date
from django.core.files.base import File

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Interactive restore of users, uploads, and admin-linked metadata from encrypted backup'

    def handle(self, *args, **options):
        backups_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backups_dir):
            self.stdout.write(self.style.ERROR(f"Backup folder does not exist: {backups_dir}"))
            return

        zip_files = [
            os.path.join(backups_dir, f)
            for f in os.listdir(backups_dir)
            if f.endswith('.zip') and os.path.isfile(os.path.join(backups_dir, f))
        ]

        if not zip_files:
            self.stdout.write(self.style.WARNING("No ZIP backups found in /backups/."))
            return

        zip_files.sort(key=lambda f: os.path.getctime(f), reverse=True)

        self.stdout.write("\nAvailable Backups:\n")
        for idx, path in enumerate(zip_files):
            name = os.path.basename(path)
            latest = " [Latest]" if idx == 0 else ""
            self.stdout.write(f"{idx + 1}. {name}{latest}")

        selected = None
        while selected is None:
            try:
                choice = int(input("\nEnter the number of the backup to restore from: ").strip())
                if 1 <= choice <= len(zip_files):
                    selected = zip_files[choice - 1]
                else:
                    raise ValueError
            except ValueError:
                self.stdout.write(self.style.ERROR("Invalid selection."))

        password = input("Enter backup password: ").strip().encode('utf-8')

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with pyzipper.AESZipFile(selected, 'r') as zf:
                    zf.setpassword(password)
                    zf.extractall(temp_dir)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to extract ZIP: {e}"))
                return

            metadata_path = os.path.join(temp_dir, 'backup_metadata.json')
            if not os.path.exists(metadata_path):
                self.stdout.write(self.style.ERROR("Metadata file not found."))
                return

            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            include_files = data.get('include_files', False)

            # === RESTORE USERS ===
            for user_data in data['users']:
                user, created = User.objects.get_or_create(id=user_data['id'], defaults={
                    'username': user_data['username'],
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_active': user_data['is_active'],
                    'is_staff': user_data.get('is_staff', False),
                    'is_superuser': user_data.get('is_superuser', False),
                    'date_joined': parse_datetime(user_data['date_joined']),
                    'password': user_data['password'],
                })

                # Always overwrite essential fields
                user.password = user_data['password']
                user.is_active = user_data['is_active']
                user.is_staff = user_data.get('is_staff', False)
                user.is_superuser = user_data.get('is_superuser', False)
                user.save()

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Restored user: {user.username}"))
                else:
                    self.stdout.write(f"Updated existing user: {user.username}")

                # === UserProfile ===
                profile_data = user_data.get('profile')
                if profile_data:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.is_verified_creator = profile_data.get('is_verified_creator', False)
                    profile.max_world_slots = profile_data.get('max_world_slots', 1)
                    profile.save()

                # === WorldSlots ===
                for slot_data in user_data['world_slots']:
                    slot, _ = WorldSlot.objects.get_or_create(
                        id=slot_data['id'],
                        defaults={
                            'owner': user,
                            'world_name': slot_data['world_name'],
                            'version': slot_data['version'],
                            'dev_name': slot_data['dev_name'],
                            'self_hosted_url': slot_data['self_hosted_url'],
                            'max_file_size_mb': slot_data['max_file_size_mb'],
                            'uploaded_at': parse_datetime(slot_data['uploaded_at']),
                            'last_updated': parse_date(slot_data['last_updated']) if slot_data['last_updated'] else None,
                            'download_slug': slot_data['download_slug'],
                        }
                    )

                    # === ZIP file restore ===
                    if include_files and slot_data.get('backup_file_path'):
                        backup_zip_path = os.path.join(temp_dir, slot_data['backup_file_path'])
                        if os.path.exists(backup_zip_path):
                            dest_folder = os.path.join(settings.MEDIA_ROOT, f"user_{user.id}", f"slot_{slot.id}")
                            os.makedirs(dest_folder, exist_ok=True)
                            dest_zip = os.path.join(dest_folder, "world.zip")
                            shutil.copy2(backup_zip_path, dest_zip)
                            slot.zip_file.name = os.path.relpath(dest_zip, settings.MEDIA_ROOT)
                            slot.save()
                            self.stdout.write(self.style.SUCCESS(f"Restored ZIP for slot: {slot.world_name}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"Missing ZIP file for slot: {slot.world_name}"))

            # === Restore Navigation ===
            NavLink.objects.all().delete()
            NavSection.objects.all().delete()
            for section_data in data.get('nav_sections', []):
                section = NavSection.objects.create(
                    title=section_data['title'],
                    url=section_data['url'],
                    order=section_data['order']
                )
                for link_data in section_data.get('links', []):
                    NavLink.objects.create(
                        section=section,
                        label=link_data['label'],
                        url=link_data['url'],
                        order=link_data['order'],
                        external=link_data['external']
                    )
            self.stdout.write(self.style.SUCCESS("Restored navigation sections and links."))

            # === Restore ImageLinks ===
            ImageLinks.objects.all().delete()
            for image in data.get('image_links', []):
                ImageLinks.objects.create(
                    avatar=image['avatar'],
                    background=image['background']
                )
            self.stdout.write(self.style.SUCCESS("Restored ImageLinks."))

        self.stdout.write(self.style.SUCCESS("Restore complete!"))
