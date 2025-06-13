from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import escape
from .models import WorldSlot
import zipfile
import logging

logger = logging.getLogger(__name__)

class SlotUploadForm(forms.ModelForm):
    external_url = forms.URLField(
        required=False,
        help_text="Optional external link for self-hosted world ZIP"
    )

    last_updated = forms.DateField(
        required=False,
        help_text="Optional manual override. Defaults to upload date.",
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = WorldSlot
        fields = ['world_name', 'version', 'dev_name', 'zip_file', 'last_updated']

    def __init__(self, *args, **kwargs):
        self.slot = kwargs.pop('slot', None)
        super().__init__(*args, **kwargs)

        # Pre-fill external_url
        if self.instance and self.instance.pk and self.instance.self_hosted_url:
            self.fields['external_url'].initial = self.instance.self_hosted_url

    def clean_world_name(self):
        world_name = self.cleaned_data.get('world_name')
        if world_name:
            # Basic sanitization while allowing flexibility
            world_name = escape(world_name.strip())
            if len(world_name) > 100:
                raise ValidationError("World name is too long (max 100 characters).")
        return world_name
    
    def clean_dev_name(self):
        dev_name = self.cleaned_data.get('dev_name')
        if dev_name:
            # Basic sanitization while allowing flexibility
            dev_name = escape(dev_name.strip())
            if len(dev_name) > 100:
                raise ValidationError("Developer name is too long (max 100 characters).")
        return dev_name
    
    def clean_version(self):
        version = self.cleaned_data.get('version')
        if version:
            version = escape(version.strip())
            if len(version) > 50:
                raise ValidationError("Version is too long (max 50 characters).")
        return version

    def clean_zip_file(self):
        file = self.cleaned_data.get('zip_file')
        if file:
            # Size validation
            limit = (self.slot.max_file_size_mb if self.slot else 100) * 1024 * 1024
            if file.size > limit:
                raise ValidationError(f"File exceeds {limit // (1024 * 1024)} MB limit.")
            
            # Basic file extension check
            if not file.name.lower().endswith('.zip'):
                raise ValidationError("Please upload a ZIP file.")
            
            # Validate it's actually a ZIP file
            try:
                # Read a small portion to validate ZIP header
                file.seek(0)
                header = file.read(4)
                file.seek(0)  # Reset file pointer
                
                # ZIP file magic numbers
                if header[:2] not in [b'PK', b'\x50\x4b']:
                    raise ValidationError("File is not a valid ZIP archive.")
                    
                # Additional validation - try to open as ZIP
                try:
                    with zipfile.ZipFile(file, 'r') as zip_file:
                        # Test the ZIP file integrity
                        zip_file.testzip()
                except zipfile.BadZipFile:
                    raise ValidationError("Corrupted ZIP file.")
                except Exception as e:
                    logger.warning(f"ZIP validation error: {e}")
                    raise ValidationError("Invalid ZIP file.")
                finally:
                    file.seek(0)  # Reset file pointer
                    
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                logger.error(f"Unexpected error during ZIP validation: {e}")
                raise ValidationError("Unable to validate ZIP file.")
        
        return file

    def clean(self):
        cleaned_data = super().clean()
        zip_file = cleaned_data.get('zip_file')
        external_url = cleaned_data.get('external_url')

        if not zip_file and not external_url:
            raise ValidationError("You must provide either a ZIP file or a self-hosted URL.")

        if zip_file and external_url:
            raise ValidationError("Please provide only one: a ZIP file or a self-hosted URL, not both.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.self_hosted_url = self.cleaned_data.get('external_url', '')

        if commit:
            instance.save()
            
            # Log the upload event
            action = "updated" if instance.pk else "created"
            logger.info(f"World slot {action}: {instance.world_name} by user {instance.owner.id}")
            
        return instance