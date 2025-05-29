"""AI processing tasks for background execution."""

import logging
from typing import Dict, Any
from uuid import UUID

from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.db.session import get_async_db
from app.services.ai_service import ai_service
from app.crud.crud_tender import crud_tender
from app.crud.crud_quote import crud_quote

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.ai_tasks.analyze_tender_task")
def analyze_tender_task(self, tender_id: str) -> Dict[str, Any]:
    """
    Analyze a tender document using AI.
    
    Args:
        tender_id: ID of the tender to analyze
        
    Returns:
        Analysis results
    """
    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting tender analysis", "progress": 0}
        )
        
        async def _analyze():
            async with get_async_db() as db:
                # Get tender
                tender = await crud_tender.get(db, id=UUID(tender_id))
                if not tender:
                    return {"error": "Tender not found"}
                
                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "Analyzing tender content", "progress": 50}
                )
                
                # Analyze tender
                analysis = await ai_service.analyze_tender(tender, db)
                
                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "Analysis complete", "progress": 100}
                )
                
                return analysis
        
        # Run async function
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_analyze())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"AI analysis task failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(bind=True, name="app.tasks.ai_tasks.generate_quote_suggestions_task")
def generate_quote_suggestions_task(
    self,
    tender_id: str,
    supplier_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate quote suggestions for a tender.
    
    Args:
        tender_id: ID of the tender
        supplier_context: Supplier capabilities and context
        
    Returns:
        Quote suggestions
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Generating quote suggestions", "progress": 0}
        )
        
        async def _generate():
            async with get_async_db() as db:
                # Get tender
                tender = await crud_tender.get(db, id=UUID(tender_id))
                if not tender:
                    return {"error": "Tender not found"}
                
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "Processing tender requirements", "progress": 30}
                )
                
                # Generate suggestions
                suggestions = await ai_service.generate_quote_suggestions(
                    tender, supplier_context, db
                )
                
                self.update_state(
                    state="PROGRESS",
                    meta={"status": "Suggestions generated", "progress": 100}
                )
                
                return suggestions
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_generate())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Quote suggestion task failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(bind=True, name="app.tasks.ai_tasks.optimize_pricing_task")
def optimize_pricing_task(
    self,
    quote_data: Dict[str, Any],
    market_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Optimize pricing for a quote.
    
    Args:
        quote_data: Quote information
        market_context: Market analysis data
        
    Returns:
        Pricing optimization results
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Analyzing market conditions", "progress": 0}
        )
        
        async def _optimize():
            self.update_state(
                state="PROGRESS",
                meta={"status": "Optimizing pricing strategy", "progress": 50}
            )
            
            # Optimize pricing
            optimization = await ai_service.optimize_pricing(
                quote_data, market_context
            )
            
            self.update_state(
                state="PROGRESS",
                meta={"status": "Optimization complete", "progress": 100}
            )
            
            return optimization
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_optimize())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Pricing optimization task failed: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


@celery_app.task(name="app.tasks.ai_tasks.batch_analyze_tenders")
def batch_analyze_tenders(tender_ids: list) -> Dict[str, Any]:
    """
    Analyze multiple tenders in batch.
    
    Args:
        tender_ids: List of tender IDs to analyze
        
    Returns:
        Batch analysis results
    """
    try:
        results = []
        total = len(tender_ids)
        
        for i, tender_id in enumerate(tender_ids):
            try:
                # Start individual analysis task
                task = analyze_tender_task.delay(tender_id)
                result = task.get(timeout=300)  # 5 minute timeout
                
                results.append({
                    "tender_id": tender_id,
                    "status": "success",
                    "analysis": result
                })
                
            except Exception as e:
                logger.error(f"Failed to analyze tender {tender_id}: {str(e)}")
                results.append({
                    "tender_id": tender_id,
                    "status": "error",
                    "error": str(e)
                })
            
            # Update progress
            progress = ((i + 1) / total) * 100
            current_task.update_state(
                state="PROGRESS",
                meta={"progress": progress, "completed": i + 1, "total": total}
            )
        
        return {
            "status": "completed",
            "total_processed": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {str(e)}")
        raise
