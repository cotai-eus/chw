"""File service for handling file uploads, storage, and processing."""

import aiofiles
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any, BinaryIO
from datetime import datetime

from fastapi import UploadFile, HTTPException
import aiofiles.os
from PIL import Image
import PyPDF2

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """Service for file upload, storage, and processing."""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.max_file_size = settings.MAX_FILE_SIZE
        self.allowed_extensions = settings.ALLOWED_FILE_EXTENSIONS
        self.allowed_mime_types = settings.ALLOWED_MIME_TYPES
        
        # Create upload directories
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        (self.upload_dir / "documents").mkdir(exist_ok=True)
        (self.upload_dir / "images").mkdir(exist_ok=True)
        (self.upload_dir / "temp").mkdir(exist_ok=True)
    
    async def upload_file(
        self,
        file: UploadFile,
        subfolder: str = "documents",
        allowed_types: Optional[List[str]] = None,
        max_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Upload and store a file.
        
        Args:
            file: The uploaded file
            subfolder: Subfolder to store the file in
            allowed_types: Optional list of allowed MIME types
            max_size: Optional max file size in bytes
            
        Returns:
            Dictionary with file information
        """
        try:
            # Validate file
            await self._validate_file(file, allowed_types, max_size)
            
            # Generate unique filename
            file_extension = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create file path
            file_dir = self.upload_dir / subfolder
            file_dir.mkdir(exist_ok=True)
            file_path = file_dir / unique_filename
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Get file info
            file_info = await self._get_file_info(file_path, file.filename)
            
            logger.info(f"File uploaded successfully: {unique_filename}")
            return file_info
            
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def upload_multiple_files(
        self,
        files: List[UploadFile],
        subfolder: str = "documents",
        allowed_types: Optional[List[str]] = None,
        max_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Upload multiple files."""
        uploaded_files = []
        
        for file in files:
            try:
                file_info = await self.upload_file(
                    file=file,
                    subfolder=subfolder,
                    allowed_types=allowed_types,
                    max_size=max_size
                )
                uploaded_files.append(file_info)
            except Exception as e:
                logger.error(f"Failed to upload file {file.filename}: {str(e)}")
                # Continue with other files
                continue
        
        return uploaded_files
    
    async def get_file(self, file_path: str) -> Optional[bytes]:
        """Retrieve file content."""
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return None
            
            async with aiofiles.open(full_path, 'rb') as f:
                return await f.read()
                
        except Exception as e:
            logger.error(f"Failed to get file {file_path}: {str(e)}")
            return None
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file."""
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                await aiofiles.os.remove(full_path)
                logger.info(f"File deleted: {file_path}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False
    
    async def process_image(
        self,
        file_path: str,
        operations: Dict[str, Any]
    ) -> Optional[str]:
        """
        Process an image with specified operations.
        
        Args:
            file_path: Path to the image file
            operations: Dictionary of operations to perform
                      e.g., {"resize": (800, 600), "format": "JPEG"}
        
        Returns:
            Path to the processed image
        """
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return None
            
            # Open image
            with Image.open(full_path) as img:
                # Apply operations
                if "resize" in operations:
                    size = operations["resize"]
                    img = img.resize(size, Image.Resampling.LANCZOS)
                
                if "rotate" in operations:
                    angle = operations["rotate"]
                    img = img.rotate(angle, expand=True)
                
                if "crop" in operations:
                    box = operations["crop"]
                    img = img.crop(box)
                
                # Save processed image
                output_format = operations.get("format", "PNG")
                processed_filename = f"processed_{uuid.uuid4()}.{output_format.lower()}"
                processed_path = self.upload_dir / "images" / processed_filename
                
                img.save(processed_path, format=output_format)
                
                relative_path = f"images/{processed_filename}"
                logger.info(f"Image processed: {relative_path}")
                return relative_path
                
        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {str(e)}")
            return None
    
    async def extract_pdf_text(self, file_path: str) -> Optional[str]:
        """Extract text content from a PDF file."""
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return None
            
            text_content = ""
            with open(full_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            
            return text_content.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract PDF text from {file_path}: {str(e)}")
            return None
    
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a file."""
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return None
            
            return await self._get_file_info(full_path)
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {str(e)}")
            return None
    
    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary files older than specified hours."""
        try:
            temp_dir = self.upload_dir / "temp"
            if not temp_dir.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            
            for file_path in temp_dir.iterdir():
                if file_path.is_file():
                    file_stat = await aiofiles.os.stat(file_path)
                    if file_stat.st_mtime < cutoff_time:
                        await aiofiles.os.remove(file_path)
                        logger.info(f"Cleaned up temp file: {file_path.name}")
                        
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {str(e)}")
    
    async def _validate_file(
        self,
        file: UploadFile,
        allowed_types: Optional[List[str]] = None,
        max_size: Optional[int] = None
    ):
        """Validate uploaded file."""
        # Check file size
        max_size = max_size or self.max_file_size
        if file.size and file.size > max_size:
            raise ValueError(f"File size ({file.size}) exceeds maximum allowed size ({max_size})")
        
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            raise ValueError(f"File extension {file_extension} not allowed")
        
        # Check MIME type
        allowed_types = allowed_types or self.allowed_mime_types
        if file.content_type not in allowed_types:
            raise ValueError(f"MIME type {file.content_type} not allowed")
        
        # Reset file pointer
        await file.seek(0)
    
    async def _get_file_info(
        self,
        file_path: Path,
        original_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get file information."""
        stat = await aiofiles.os.stat(file_path)
        
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Calculate relative path from upload directory
        relative_path = file_path.relative_to(self.upload_dir)
        
        return {
            "filename": file_path.name,
            "original_name": original_name or file_path.name,
            "path": str(relative_path),
            "size": stat.st_size,
            "mime_type": mime_type,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "extension": file_path.suffix.lower()
        }


# Global instance
file_service = FileService()
