# storage.py - Create this as a new file in your Django app directory
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

class OverwriteStorage(FileSystemStorage):
    """
    Custom storage that deletes existing files before saving new ones.
    This prevents Django from creating duplicate files with modified names.
    """
    
    def get_available_name(self, name, max_length=None):
        """
        Return a filename that's available for use.
        If a file with the given name already exists, delete it first.
        """
        if self.exists(name):
            self.delete(name)
        return name

    def _save(self, name, content):
        """
        Save the file, overwriting any existing file with the same name.
        """
        # Ensure the directory exists
        full_path = self.path(name)
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # If file exists, delete it first (belt and suspenders approach)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass  # File might be in use or already deleted
        
        return super()._save(name, content)