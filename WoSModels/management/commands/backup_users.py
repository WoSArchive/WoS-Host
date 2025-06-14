import os
import shutil
import json
import logging
import pyzipper
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from WoSModels.models import UserProfile, WorldSlot, NavSection, NavLink, ImageLinks

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Backup user data, uploads, and admin-linked metadata into encrypted archive.'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='Backup specific user by ID')
        parser.add_argument('--output-dir', type=str, default=os.path.join(settings.BASE_DIR, 'backups'))
        parser.add_argument('--include-files', action='store_true', help='Include ZIP files in backup')
        parser.add_argument('--password', type=str, help='Password for encrypted zip')

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        user_id = options.get('user_id')
        include_files = options['include_files']
        zip_password = options.get('password')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_root = os.path.join(output_dir, f'backup_{timestamp}')
        os.makedirs(backup_root, exist_ok=True)

        self.stdout.write(f"Creating temporary backup in: {backup_root}")

        if user_id:
            users = User.objects.filter(id=user_id)
            if not users.exists():
                self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
                return
        else:
            users = User.objects.all()

        backup_data = {
            'timestamp': timestamp,
            'users': [],
            'include_files': include_files
        }

        for user in users:
            self.stdout.write(f"Backing up user: {user.username} (ID: {user.id})")
            try:
                profile = user.userprofile
            except UserProfile.DoesNotExist:
                profile = None

            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat(),
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'password': user.password,
                'profile': {
                    'is_verified_creator': profile.is_verified_creator if profile else False,
                    'max_world_slots': profile.max_world_slots if profile else 1,
                } if profile else None,
                'world_slots': []
            }

            slots = WorldSlot.objects.filter(owner=user)
            for slot in slots:
                slot_data = {
                    'id': slot.id,
                    'world_name': slot.world_name,
                    'version': slot.version,
                    'dev_name': slot.dev_name,
                    'self_hosted_url': slot.self_hosted_url,
                    'max_file_size_mb': slot.max_file_size_mb,
                    'uploaded_at': slot.uploaded_at.isoformat(),
                    'last_updated': slot.last_updated.isoformat() if slot.last_updated else None,
                    'download_slug': slot.download_slug,
                    'has_zip_file': bool(slot.zip_file and slot.zip_file.name),
                    'zip_file_path': slot.zip_file.name if slot.zip_file else None,
                }

                if include_files and slot.zip_file and slot.zip_file.name:
                    try:
                        source_path = slot.zip_file.path
                        if os.path.exists(source_path):
                            user_dir = os.path.join(backup_root, f'user_{user.id}')
                            os.makedirs(user_dir, exist_ok=True)
                            dest_file = f'slot_{slot.id}_{slot.world_name}.zip'
                            dest_path = os.path.join(user_dir, dest_file)
                            shutil.copy2(source_path, dest_path)
                            slot_data['backup_file_path'] = os.path.join(f'user_{user.id}', dest_file)
                            self.stdout.write(f"  Copied file: {dest_file}")
                        else:
                            self.stdout.write(self.style.WARNING(f"  File not found: {source_path}"))
                            slot_data['backup_file_path'] = None
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  Failed to copy slot {slot.id}: {e}"))
                        slot_data['backup_file_path'] = None

                user_data['world_slots'].append(slot_data)

            backup_data['users'].append(user_data)

        # Include admin model data
        backup_data['nav_sections'] = [
            {
                'title': section.title,
                'url': section.url,
                'order': section.order,
                'links': [
                    {
                        'label': link.label,
                        'url': link.url,
                        'order': link.order,
                        'external': link.external
                    } for link in section.links.all().order_by('order')
                ]
            } for section in NavSection.objects.all().order_by('order')
        ]

        backup_data['image_links'] = [
            {
                'avatar': link.avatar,
                'background': link.background
            } for link in ImageLinks.objects.all()
        ]

        metadata_path = os.path.join(backup_root, 'backup_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2)

        zip_name = f'backup_{timestamp}.zip'
        zip_path = os.path.join(output_dir, zip_name)

        self.stdout.write(f'Encrypting and compressing backup into: {zip_path}')

        with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            if zip_password:
                zf.setpassword(zip_password.encode('utf-8'))
            for root, _, files in os.walk(backup_root):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, backup_root)
                    zf.write(abs_path, arcname=rel_path)

        shutil.rmtree(backup_root)
        self.stdout.write(self.style.SUCCESS(f"Backup complete and encrypted: {zip_path}"))
