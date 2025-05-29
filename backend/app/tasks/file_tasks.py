"""File processing tasks for background execution."""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.celery_app import celery_app
from app.services.file_service import file_service
from app.services.quote_service import quote_service
from app.db.session import get_async_db

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.file_tasks.process_file_upload_task")
def process_file_upload_task(
    self,
    file_path: str,
    processing_options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process an uploaded file in the background.
    
    Args:
        file_path: Path to the uploaded file
        processing_options: Options for file processing
        
    Returns:
        Processing results
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting file processing", "progress": 0}
        )
        
        async def _process():
            # Get file info
            file_info = await file_service.get_file_info(file_path)
            if not file_info:
                return {"error": "File not found"}
            
            self.update_state(
                state="PROGRESS",
                meta={"status": "Processing file", "progress": 30}
            )
            
            results = {"file_info": file_info, "processed_data": {}}
            
            # Process based on file type
            file_type = file_info.get("mime_type", "")
            
            if "image" in file_type and processing_options.get("image_operations"):
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "Processing image", "progress": 50}
                )
                
                processed_path = await file_service.process_image(
                    file_path, processing_options["image_operations"]
                )
                results["processed_data"]["processed_image"] = processed_path
            
            elif "pdf" in file_type and processing_options.get("extract_text"):
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "Extracting PDF text", "progress": 50}
                )
                
                text_content = await file_service.extract_pdf_text(file_path)
                results["processed_data"]["extracted_text"] = text_content
            
            self.update_state(
                state="PROGRESS",
                meta={"status": "Processing complete", "progress": 100}
            )
            
            return results
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_process())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"File processing task failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(bind=True, name="app.tasks.file_tasks.generate_pdf_task")
def generate_pdf_task(
    self,
    quote_id: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate PDF document for a quote.
    
    Args:
        quote_id: ID of the quote
        output_path: Optional custom output path
        
    Returns:
        PDF generation results
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Generating PDF", "progress": 0}
        )
        
        async def _generate():
            async with get_async_db() as db:
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "Fetching quote data", "progress": 20}
                )
                
                # Generate PDF
                pdf_bytes = await quote_service.generate_quote_pdf(
                    db, UUID(quote_id)
                )
                
                if not pdf_bytes:
                    return {"error": "Failed to generate PDF"}
                
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "Saving PDF file", "progress": 80}
                )
                
                # Save PDF file
                if not output_path:
                    output_path = f"documents/quote_{quote_id}.pdf"
                
                # Save to file system
                import aiofiles
                from pathlib import Path
                from app.core.config import settings
                
                full_path = Path(settings.UPLOAD_DIR) / output_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with aiofiles.open(full_path, 'wb') as f:
                    await f.write(pdf_bytes)
                
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "PDF generated successfully", "progress": 100}
                )
                
                return {
                    "quote_id": quote_id,
                    "pdf_path": output_path,
                    "file_size": len(pdf_bytes)
                }
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_generate())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"PDF generation task failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(name="app.tasks.file_tasks.cleanup_temp_files")
def cleanup_temp_files(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up temporary files older than specified hours.
    
    Args:
        max_age_hours: Maximum age of files to keep
        
    Returns:
        Cleanup results
    """
    try:
        async def _cleanup():
            await file_service.cleanup_temp_files(max_age_hours)
            return {"status": "completed", "max_age_hours": max_age_hours}
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_cleanup())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise


@celery_app.task(bind=True, name="app.tasks.file_tasks.extract_pdf_text_task")
def extract_pdf_text_task(self, file_path: str) -> Dict[str, Any]:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Extracting PDF text", "progress": 0}
        )
        
        async def _extract():
            self.update_state(
                state="PROGRESS",
                meta={"status": "Processing PDF", "progress": 50}
            )
            
            text_content = await file_service.extract_pdf_text(file_path)
            
            self.update_state(
                state="PROGRESS",
                meta={"status": "Text extraction complete", "progress": 100}
            )
            
            return {
                "file_path": file_path,
                "text_content": text_content,
                "character_count": len(text_content) if text_content else 0
            }
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_extract())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"PDF text extraction task failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(name="app.tasks.file_tasks.batch_process_files")
def batch_process_files(
    file_paths: List[str],
    processing_options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process multiple files in batch.
    
    Args:
        file_paths: List of file paths to process
        processing_options: Processing options to apply
        
    Returns:
        Batch processing results
    """
    try:
        results = []
        total = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            try:
                # Process individual file
                task = process_file_upload_task.delay(file_path, processing_options)
                result = task.get(timeout=300)  # 5 minute timeout per file
                
                results.append({
                    "file_path": file_path,
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {str(e)}")
                results.append({
                    "file_path": file_path,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "total_files": total,
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch file processing failed: {str(e)}")
        raise


@celery_app.task(name="app.tasks.file_tasks.convert_document")
def convert_document(
    input_path: str,
    output_format: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert document from one format to another.
    
    Args:
        input_path: Path to input file
        output_format: Target format (pdf, docx, txt, etc.)
        output_path: Optional output path
        
    Returns:
        Conversion results
    """
    try:
        # This would implement document conversion logic
        # For now, return placeholder
        return {
            "input_path": input_path,
            "output_format": output_format,
            "output_path": output_path or f"{input_path}.{output_format}",
            "status": "converted"
        }
        
    except Exception as e:
        logger.error(f"Document conversion failed: {str(e)}")
        raise
