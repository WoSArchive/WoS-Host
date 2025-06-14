import re
import zipfile
import logging
from django import forms
from django.utils.html import escape
from django.core.exceptions import ValidationError
from .models import WorldSlot

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

        if self.instance and self.instance.pk and self.instance.self_hosted_url:
            self.fields['external_url'].initial = self.instance.self_hosted_url

    def clean_world_name(self):
        world_name = self.cleaned_data.get('world_name')
        if world_name:
            world_name = escape(world_name.strip())
            if len(world_name) > 100:
                raise ValidationError("World name is too long (max 100 characters).")
        return world_name

    def clean_dev_name(self):
        dev_name = self.cleaned_data.get('dev_name')
        if dev_name:
            dev_name = escape(dev_name.strip())
            if len(dev_name) > 100:
                raise ValidationError("Developer name is too long (max 100 characters).")
        return dev_name

    def clean_version(self):
        version = self.cleaned_data.get('version')
        if version:
            version = escape(version.strip())
            if version.lower().startswith('v'):
                version = version[1:].strip()
            if len(version) > 50:
                raise ValidationError("Version is too long (max 50 characters).")
        return version

    def clean_zip_file(self):
        file = self.cleaned_data.get('zip_file')
        if file:
            limit = (self.slot.max_file_size_mb if self.slot else 100) * 1024 * 1024
            if file.size > limit:
                raise ValidationError(f"File exceeds {limit // (1024 * 1024)} MB limit.")
            if not file.name.lower().endswith('.zip'):
                raise ValidationError("Please upload a ZIP file.")

            try:
                file.seek(0)
                header = file.read(4)
                file.seek(0)
                if header[:2] not in [b'PK', b'\x50\x4b']:
                    raise ValidationError("File is not a valid ZIP archive.")

                with zipfile.ZipFile(file, 'r') as zip_file:
                    zip_file.testzip()
            except zipfile.BadZipFile:
                raise ValidationError("Corrupted ZIP file.")
            except Exception as e:
                logger.warning(f"ZIP validation error: {e}")
                raise ValidationError("Invalid ZIP file.")
            finally:
                file.seek(0)
        return file

    def clean_external_url(self):
        url = self.cleaned_data.get('external_url', '').strip()

        # Google Drive
        if "drive.google.com" in url:
            match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
            if match:
                file_id = match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"

        # Dropbox
        if "dropbox.com" in url:
            return re.sub(r"\?dl=0$", "?dl=1", url)

        return url

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
            action = "updated" if instance.pk else "created"
            logger.info(f"World slot {action}: {instance.world_name} by user {instance.owner.id}")

        return instance
