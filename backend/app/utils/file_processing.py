"""
File processing utilities for handling uploads, validation, and conversion.
"""
import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image, ImageOps
import magic
from app.core.config import get_settings
from app.exceptions.custom_exceptions import ValidationError

settings = get_settings()


class FileProcessor:
    """Handles file processing, validation, and conversion."""
    
    # Allowed file types
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'
    }
    
    ALLOWED_DOCUMENT_TYPES = {
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain', 'text/csv'
    }
    
    ALLOWED_ARCHIVE_TYPES = {
        'application/zip', 'application/x-zip-compressed',
        'application/x-rar-compressed', 'application/x-7z-compressed'
    }
    
    # File size limits (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_ARCHIVE_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.subdirs = {
            'images': self.upload_dir / 'images',
            'documents': self.upload_dir / 'documents',
            'archives': self.upload_dir / 'archives',
            'temp': self.upload_dir / 'temp',
            'processed': self.upload_dir / 'processed'
        }
        
        for subdir in self.subdirs.values():
            subdir.mkdir(parents=True, exist_ok=True)
    
    def validate_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Validate file content and metadata."""
        # Detect MIME type using python-magic
        mime_type = magic.from_buffer(file_content, mime=True)
        
        # Get file extension
        file_ext = Path(filename).suffix.lower()
        
        # Validate file size
        file_size = len(file_content)
        
        # Determine file category
        file_category = self._get_file_category(mime_type)
        
        # Validate based on category
        if file_category == 'image':
            self._validate_image_file(file_content, file_size, mime_type)
        elif file_category == 'document':
            self._validate_document_file(file_content, file_size, mime_type)
        elif file_category == 'archive':
            self._validate_archive_file(file_content, file_size, mime_type)
        else:
            raise ValidationError(f"File type {mime_type} is not allowed")
        
        return {
            'filename': filename,
            'mime_type': mime_type,
            'file_size': file_size,
            'file_category': file_category,
            'file_extension': file_ext
        }
    
    def _get_file_category(self, mime_type: str) -> str:
        """Determine file category based on MIME type."""
        if mime_type in self.ALLOWED_IMAGE_TYPES:
            return 'image'
        elif mime_type in self.ALLOWED_DOCUMENT_TYPES:
            return 'document'
        elif mime_type in self.ALLOWED_ARCHIVE_TYPES:
            return 'archive'
        else:
            return 'unknown'
    
    def _validate_image_file(self, content: bytes, size: int, mime_type: str):
        """Validate image file."""
        if size > self.MAX_IMAGE_SIZE:
            raise ValidationError(f"Image file too large. Maximum size: {self.MAX_IMAGE_SIZE} bytes")
        
        if mime_type not in self.ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Image type {mime_type} not allowed")
        
        # Additional image validation using PIL
        try:
            image = Image.open(BytesIO(content))
            image.verify()
        except Exception as e:
            raise ValidationError(f"Invalid image file: {str(e)}")
    
    def _validate_document_file(self, content: bytes, size: int, mime_type: str):
        """Validate document file."""
        if size > self.MAX_DOCUMENT_SIZE:
            raise ValidationError(f"Document file too large. Maximum size: {self.MAX_DOCUMENT_SIZE} bytes")
        
        if mime_type not in self.ALLOWED_DOCUMENT_TYPES:
            raise ValidationError(f"Document type {mime_type} not allowed")
    
    def _validate_archive_file(self, content: bytes, size: int, mime_type: str):
        """Validate archive file."""
        if size > self.MAX_ARCHIVE_SIZE:
            raise ValidationError(f"Archive file too large. Maximum size: {self.MAX_ARCHIVE_SIZE} bytes")
        
        if mime_type not in self.ALLOWED_ARCHIVE_TYPES:
            raise ValidationError(f"Archive type {mime_type} not allowed")
    
    def save_file(
        self,
        file_content: bytes,
        filename: str,
        file_info: Dict[str, Any],
        subfolder: Optional[str] = None
    ) -> str:
        """Save file to disk and return file path."""
        # Generate unique filename
        file_ext = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Determine save directory
        category = file_info['file_category']
        save_dir = self.subdirs[f"{category}s"]  # images, documents, archives
        
        if subfolder:
            save_dir = save_dir / subfolder
            save_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = save_dir / unique_filename
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return str(file_path.relative_to(self.upload_dir))
    
    def process_image(
        self,
        file_path: str,
        resize: Optional[Tuple[int, int]] = None,
        quality: int = 85,
        format_output: Optional[str] = None
    ) -> str:
        """Process image with resizing and optimization."""
        full_path = self.upload_dir / file_path
        
        with Image.open(full_path) as image:
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Apply auto-orientation
            image = ImageOps.exif_transpose(image)
            
            # Resize if requested
            if resize:
                image = image.resize(resize, Image.Resampling.LANCZOS)
            
            # Generate processed filename
            processed_filename = f"processed_{Path(full_path).stem}.jpg"
            processed_path = self.subdirs['processed'] / processed_filename
            
            # Save processed image
            image.save(
                processed_path,
                format=format_output or 'JPEG',
                quality=quality,
                optimize=True
            )
            
            return str(processed_path.relative_to(self.upload_dir))
    
    def create_thumbnail(
        self,
        file_path: str,
        size: Tuple[int, int] = (200, 200),
        quality: int = 75
    ) -> str:
        """Create thumbnail for image."""
        full_path = self.upload_dir / file_path
        
        with Image.open(full_path) as image:
            # Create thumbnail
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Generate thumbnail filename
            thumb_filename = f"thumb_{Path(full_path).stem}.jpg"
            thumb_path = self.subdirs['processed'] / thumb_filename
            
            # Save thumbnail
            image.save(thumb_path, format='JPEG', quality=quality, optimize=True)
            
            return str(thumb_path.relative_to(self.upload_dir))
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get detailed file information."""
        full_path = self.upload_dir / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = full_path.stat()
        mime_type, _ = mimetypes.guess_type(str(full_path))
        
        info = {
            'filename': full_path.name,
            'file_path': file_path,
            'file_size': stat.st_size,
            'mime_type': mime_type,
            'created_at': stat.st_ctime,
            'modified_at': stat.st_mtime,
            'file_category': self._get_file_category(mime_type or '')
        }
        
        # Add image-specific info
        if info['file_category'] == 'image':
            try:
                with Image.open(full_path) as image:
                    info.update({
                        'width': image.width,
                        'height': image.height,
                        'format': image.format,
                        'mode': image.mode
                    })
            except Exception:
                pass
        
        return info
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from disk."""
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary files older than specified hours."""
        import time
        
        temp_dir = self.subdirs['temp']
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in temp_dir.glob('*'):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        print(f"Error deleting temp file {file_path}: {e}")


class FileValidator:
    """Advanced file validation utilities."""
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """Check if filename is safe (no path traversal)."""
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        name = Path(filename).stem[:100]
        ext = Path(filename).suffix[:10]
        
        return f"{name}{ext}"
    
    @staticmethod
    def check_virus_signature(file_content: bytes) -> bool:
        """Basic virus signature check (implement with antivirus API)."""
        # This is a placeholder - implement with actual antivirus service
        # like ClamAV, VirusTotal API, etc.
        
        # Check for common malicious patterns
        malicious_patterns = [
            b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE',  # EICAR test signature
            b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR',  # EICAR variant
        ]
        
        for pattern in malicious_patterns:
            if pattern in file_content:
                return False
        
        return True


# Global file processor instance
file_processor = FileProcessor()

from io import BytesIO
