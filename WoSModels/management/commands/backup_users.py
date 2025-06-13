# Create this file as: management/commands/backup_users.py
# Directory structure: yourapp/management/commands/backup_users.py

import os
import shutil
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from yourapp.models import UserProfile, WorldSlot  # Replace 'yourapp' with your actual app name
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Backup user data including files and metadata'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Backup specific user by ID',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'backups'),
            help='Output directory for backups',
        )
        parser.add_argument(
            '--include-files',
            action='store_true',
            help='Include actual ZIP files in backup (default: metadata only)',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        user_id = options.get('user_id')
        include_files = options['include_files']
        
        # Create backup directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(output_dir, f'backup_{timestamp}')
        os.makedirs(backup_dir, exist_ok=True)
        
        self.stdout.write(f"Creating backup in: {backup_dir}")
        
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
                'profile': {
                    'is_verified_creator': profile.is_verified_creator if profile else False,
                    'max_world_slots': profile.max_world_slots if profile else 1,
                } if profile else None,
                'world_slots': []
            }
            
            # Backup world slots
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
                
                # Copy actual files if requested
                if include_files and slot.zip_file and slot.zip_file.name:
                    try:
                        source_path = slot.zip_file.path
                        if os.path.exists(source_path):
                            # Create user backup directory
                            user_backup_dir = os.path.join(backup_dir, f'user_{user.id}')
                            os.makedirs(user_backup_dir, exist_ok=True)
                            
                            # Copy file
                            filename = f'slot_{slot.id}_{slot.world_name}.zip'
                            dest_path = os.path.join(user_backup_dir, filename)
                            shutil.copy2(source_path, dest_path)
                            
                            slot_data['backup_file_path'] = os.path.join(f'user_{user.id}', filename)
                            self.stdout.write(f"  Copied file: {filename}")
                        else:
                            self.stdout.write(self.style.WARNING(f"  File not found: {source_path}"))
                            slot_data['backup_file_path'] = None
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  Failed to copy file for slot {slot.id}: {e}"))
                        slot_data['backup_file_path'] = None
                
                user_data['world_slots'].append(slot_data)
            
            backup_data['users'].append(user_data)
        
        # Save metadata
        metadata_file = os.path.join(backup_dir, 'backup_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        # Create restore script
        self.create_restore_script(backup_dir)
        
        self.stdout.write(self.style.SUCCESS(f'Backup completed: {backup_dir}'))
        self.stdout.write(f'Total users backed up: {len(backup_data["users"])}')
        
        # Log the backup
        logger.info(f'User backup completed: {len(backup_data["users"])} users, files included: {include_files}')

    def create_restore_script(self, backup_dir):
        """Create a restore script for the backup"""
        restore_script = f"""#!/usr/bin/env python
# Auto-generated restore script for backup: {os.path.basename(backup_dir)}
# Usage: python manage.py shell < restore_script.py

import json
import os
import shutil
from django.contrib.auth.models import User
from yourapp.models import UserProfile, WorldSlot  # Replace 'yourapp' with your actual app name
from django.conf import settings

# Load backup metadata
with open('{os.path.join(backup_dir, 'backup_metadata.json')}', 'r') as f:
    backup_data = json.load(f)

print(f"Restoring backup from: {{backup_data['timestamp']}}")

for user_data in backup_data['users']:
    print(f"Processing user: {{user_data['username']}}")
    
    # Note: This script provides a template for restoration
    # You'll need to customize it based on your specific needs
    # and handle conflicts/duplicates appropriately
    
    # Example restoration logic would go here
    pass

print("Restore script template completed")
print("Please customize this script for your specific restoration needs")
"""
        
        script_path = os.path.join(backup_dir, 'restore_script.py')
        with open(script_path, 'w') as f:
            f.write(restore_script)
        
        # Make it executable on Unix systems
        try:
            os.chmod(script_path, 0o755)
        except:
            pass