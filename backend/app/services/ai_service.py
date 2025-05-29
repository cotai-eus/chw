"""AI Processing Service for tender analysis and quote generation."""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.crud_tender import crud_tender
from app.crud.crud_quote import crud_quote
from app.db.models.tender import Tender
from app.db.models.quote import Quote
from app.schemas.quote import QuoteCreate, QuoteItemCreate

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered tender analysis and quote generation."""
    
    def __init__(self):
        self.ollama_url = settings.OLLAMA_URL
        self.model_name = settings.OLLAMA_MODEL_NAME
    
    async def analyze_tender(
        self,
        tender: Tender,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Analyze a tender document using AI to extract key information.
        
        Args:
            tender: The tender to analyze
            db: Database session
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Prepare tender data for analysis
            tender_data = {
                "title": tender.title,
                "description": tender.description,
                "requirements": tender.requirements or "",
                "budget": float(tender.budget) if tender.budget else None,
                "deadline": tender.deadline.isoformat() if tender.deadline else None,
                "delivery_terms": tender.delivery_terms or "",
                "payment_terms": tender.payment_terms or "",
            }
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(tender_data)
            
            # Call Ollama API
            analysis_result = await self._call_ollama(prompt)
            
            # Parse and structure the response
            structured_analysis = self._parse_analysis_result(analysis_result)
            
            logger.info(f"Successfully analyzed tender {tender.id}")
            return structured_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing tender {tender.id}: {str(e)}")
            return {
                "error": "Failed to analyze tender",
                "message": str(e)
            }
    
    async def generate_quote_suggestions(
        self,
        tender: Tender,
        supplier_context: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Generate quote suggestions based on tender requirements and supplier capabilities.
        
        Args:
            tender: The tender to quote for
            supplier_context: Information about the supplier's capabilities
            db: Database session
            
        Returns:
            Dictionary with quote suggestions
        """
        try:
            # Prepare context for quote generation
            context = {
                "tender": {
                    "title": tender.title,
                    "description": tender.description,
                    "requirements": tender.requirements or "",
                    "budget": float(tender.budget) if tender.budget else None,
                    "items": [
                        {
                            "description": item.description,
                            "quantity": item.quantity,
                            "unit": item.unit,
                            "specifications": item.specifications or ""
                        }
                        for item in tender.items
                    ]
                },
                "supplier": supplier_context
            }
            
            # Create quote generation prompt
            prompt = self._create_quote_prompt(context)
            
            # Call Ollama API
            suggestions = await self._call_ollama(prompt)
            
            # Parse and structure the response
            structured_suggestions = self._parse_quote_suggestions(suggestions)
            
            logger.info(f"Generated quote suggestions for tender {tender.id}")
            return structured_suggestions
            
        except Exception as e:
            logger.error(f"Error generating quote suggestions for tender {tender.id}: {str(e)}")
            return {
                "error": "Failed to generate quote suggestions",
                "message": str(e)
            }
    
    async def optimize_pricing(
        self,
        quote_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Optimize pricing for a quote based on market conditions and competition.
        
        Args:
            quote_data: The quote data to optimize
            market_context: Market information and competitor analysis
            
        Returns:
            Dictionary with pricing optimization suggestions
        """
        try:
            # Prepare optimization context
            context = {
                "quote": quote_data,
                "market": market_context or {}
            }
            
            # Create optimization prompt
            prompt = self._create_optimization_prompt(context)
            
            # Call Ollama API
            optimization = await self._call_ollama(prompt)
            
            # Parse and structure the response
            structured_optimization = self._parse_optimization_result(optimization)
            
            logger.info("Successfully optimized pricing")
            return structured_optimization
            
        except Exception as e:
            logger.error(f"Error optimizing pricing: {str(e)}")
            return {
                "error": "Failed to optimize pricing",
                "message": str(e)
            }
    
    async def _call_ollama(self, prompt: str) -> str:
        """Make API call to Ollama service."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "max_tokens": 2000
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
                
        except httpx.RequestError as e:
            logger.error(f"Request error calling Ollama: {str(e)}")
            raise Exception(f"Failed to connect to AI service: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling Ollama: {str(e)}")
            raise Exception(f"AI service returned error: {str(e)}")
    
    def _create_analysis_prompt(self, tender_data: Dict[str, Any]) -> str:
        """Create prompt for tender analysis."""
        return f"""
        Analyze the following tender document and provide a structured analysis:

        Tender Information:
        - Title: {tender_data['title']}
        - Description: {tender_data['description']}
        - Requirements: {tender_data['requirements']}
        - Budget: {tender_data['budget']}
        - Deadline: {tender_data['deadline']}
        - Delivery Terms: {tender_data['delivery_terms']}
        - Payment Terms: {tender_data['payment_terms']}

        Please provide analysis in the following JSON format:
        {{
            "complexity": "low|medium|high",
            "risk_factors": ["factor1", "factor2"],
            "key_requirements": ["req1", "req2"],
            "technical_specifications": ["spec1", "spec2"],
            "compliance_requirements": ["comp1", "comp2"],
            "estimated_effort": "description",
            "recommendations": ["rec1", "rec2"],
            "potential_challenges": ["challenge1", "challenge2"]
        }}
        """
    
    def _create_quote_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for quote generation."""
        return f"""
        Generate quote suggestions based on the tender requirements and supplier capabilities:

        Tender: {json.dumps(context['tender'], indent=2)}
        Supplier: {json.dumps(context['supplier'], indent=2)}

        Please provide suggestions in the following JSON format:
        {{
            "suggested_total_price": 0.0,
            "pricing_strategy": "competitive|premium|value",
            "item_suggestions": [
                {{
                    "description": "item description",
                    "quantity": 1,
                    "unit_price": 0.0,
                    "total_price": 0.0,
                    "justification": "pricing rationale"
                }}
            ],
            "value_propositions": ["prop1", "prop2"],
            "competitive_advantages": ["adv1", "adv2"],
            "delivery_suggestions": "delivery approach",
            "risk_mitigation": ["risk1 mitigation", "risk2 mitigation"]
        }}
        """
    
    def _create_optimization_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for pricing optimization."""
        return f"""
        Optimize the pricing for this quote based on market conditions:

        Context: {json.dumps(context, indent=2)}

        Please provide optimization suggestions in the following JSON format:
        {{
            "optimized_total": 0.0,
            "adjustment_percentage": 0.0,
            "optimization_rationale": "explanation",
            "item_adjustments": [
                {{
                    "item_id": "id",
                    "original_price": 0.0,
                    "optimized_price": 0.0,
                    "adjustment_reason": "reason"
                }}
            ],
            "market_positioning": "below|at|above market rate",
            "win_probability": "low|medium|high",
            "recommendations": ["rec1", "rec2"]
        }}
        """
    
    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        """Parse and validate analysis result."""
        try:
            # Try to extract JSON from the response
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # Fallback to basic parsing
                return {
                    "complexity": "medium",
                    "analysis": result,
                    "parsed": False
                }
        except json.JSONDecodeError:
            return {
                "complexity": "medium",
                "analysis": result,
                "parsed": False
            }
    
    def _parse_quote_suggestions(self, result: str) -> Dict[str, Any]:
        """Parse and validate quote suggestions."""
        try:
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {
                    "suggested_total_price": 0.0,
                    "suggestions": result,
                    "parsed": False
                }
        except json.JSONDecodeError:
            return {
                "suggested_total_price": 0.0,
                "suggestions": result,
                "parsed": False
            }
    
    def _parse_optimization_result(self, result: str) -> Dict[str, Any]:
        """Parse and validate optimization result."""
        try:
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {
                    "optimized_total": 0.0,
                    "optimization": result,
                    "parsed": False
                }
        except json.JSONDecodeError:
            return {
                "optimized_total": 0.0,
                "optimization": result,
                "parsed": False
            }


# Global instance
ai_service = AIService()
