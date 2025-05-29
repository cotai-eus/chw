"""Quote service for generating, managing, and processing quotes."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import io

from app.core.config import settings
from app.crud.crud_quote import crud_quote
from app.crud.crud_tender import crud_tender
from app.crud.crud_supplier import crud_supplier
from app.schemas.quote import QuoteCreate, QuoteItemCreate

logger = logging.getLogger(__name__)


class QuoteService:
    """Service for quote management and generation."""
    
    def __init__(self):
        self.default_validity_days = settings.DEFAULT_QUOTE_VALIDITY_DAYS
        self.tax_rate = settings.DEFAULT_TAX_RATE
    
    async def generate_quote_from_tender(
        self,
        db: AsyncSession,
        tender_id: UUID,
        supplier_id: UUID,
        user_id: UUID,
        pricing_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a quote based on tender requirements.
        
        Args:
            db: Database session
            tender_id: ID of the tender
            supplier_id: ID of the supplier
            user_id: ID of the user creating the quote
            pricing_data: Pricing information for items
            
        Returns:
            Generated quote information
        """
        try:
            # Get tender information
            tender = await crud_tender.get(db, id=tender_id)
            if not tender:
                return {"error": "Tender not found"}
            
            # Get supplier information
            supplier = await crud_supplier.get(db, id=supplier_id)
            if not supplier:
                return {"error": "Supplier not found"}
            
            # Generate quote number
            quote_number = await self._generate_quote_number(db, supplier.company_id)
            
            # Calculate validity date
            valid_until = datetime.utcnow() + timedelta(days=self.default_validity_days)
            
            # Create quote items from tender items
            quote_items = []
            total_amount = Decimal('0.00')
            
            for tender_item in tender.items:
                item_pricing = pricing_data.get(str(tender_item.id), {})
                unit_price = Decimal(str(item_pricing.get('unit_price', 0)))
                quantity = tender_item.quantity
                item_total = unit_price * quantity
                
                quote_item = QuoteItemCreate(
                    tender_item_id=tender_item.id,
                    description=tender_item.description,
                    quantity=quantity,
                    unit=tender_item.unit,
                    unit_price=unit_price,
                    total_price=item_total,
                    specifications=item_pricing.get('specifications', ''),
                    notes=item_pricing.get('notes', '')
                )
                quote_items.append(quote_item)
                total_amount += item_total
            
            # Apply tax
            tax_amount = total_amount * Decimal(str(self.tax_rate))
            total_with_tax = total_amount + tax_amount
            
            # Create quote
            quote_data = QuoteCreate(
                quote_number=quote_number,
                tender_id=tender_id,
                supplier_id=supplier_id,
                total_amount=total_with_tax,
                tax_amount=tax_amount,
                valid_until=valid_until,
                terms_conditions=pricing_data.get('terms_conditions', ''),
                notes=pricing_data.get('notes', ''),
                delivery_terms=pricing_data.get('delivery_terms', ''),
                payment_terms=pricing_data.get('payment_terms', ''),
                items=quote_items
            )
            
            # Save quote
            quote = await crud_quote.create_with_items(db, obj_in=quote_data, user_id=user_id)
            
            logger.info(f"Quote {quote_number} generated for tender {tender_id}")
            return {
                "quote_id": quote.id,
                "quote_number": quote_number,
                "total_amount": float(total_with_tax),
                "valid_until": valid_until
            }
            
        except Exception as e:
            logger.error(f"Failed to generate quote: {str(e)}")
            return {"error": str(e)}
    
    async def calculate_quote_pricing(
        self,
        items: List[Dict[str, Any]],
        markup_percentage: Optional[float] = None,
        discount_percentage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate quote pricing with markup and discounts.
        
        Args:
            items: List of items with base pricing
            markup_percentage: Markup percentage to apply
            discount_percentage: Discount percentage to apply
            
        Returns:
            Calculated pricing information
        """
        try:
            subtotal = Decimal('0.00')
            calculated_items = []
            
            for item in items:
                base_price = Decimal(str(item.get('base_price', 0)))
                quantity = item.get('quantity', 1)
                
                # Apply markup
                if markup_percentage:
                    markup_amount = base_price * Decimal(str(markup_percentage / 100))
                    unit_price = base_price + markup_amount
                else:
                    unit_price = base_price
                
                item_total = unit_price * quantity
                subtotal += item_total
                
                calculated_items.append({
                    "id": item.get('id'),
                    "description": item.get('description'),
                    "quantity": quantity,
                    "base_price": float(base_price),
                    "unit_price": float(unit_price),
                    "total_price": float(item_total),
                    "markup_applied": float(markup_amount) if markup_percentage else 0
                })
            
            # Apply discount
            discount_amount = Decimal('0.00')
            if discount_percentage:
                discount_amount = subtotal * Decimal(str(discount_percentage / 100))
            
            discounted_subtotal = subtotal - discount_amount
            
            # Calculate tax
            tax_amount = discounted_subtotal * Decimal(str(self.tax_rate))
            total_amount = discounted_subtotal + tax_amount
            
            return {
                "items": calculated_items,
                "subtotal": float(subtotal),
                "discount_amount": float(discount_amount),
                "discounted_subtotal": float(discounted_subtotal),
                "tax_amount": float(tax_amount),
                "total_amount": float(total_amount),
                "markup_percentage": markup_percentage,
                "discount_percentage": discount_percentage,
                "tax_rate": self.tax_rate
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate pricing: {str(e)}")
            return {"error": str(e)}
    
    async def generate_quote_pdf(
        self,
        db: AsyncSession,
        quote_id: UUID
    ) -> Optional[bytes]:
        """
        Generate PDF document for a quote.
        
        Args:
            db: Database session
            quote_id: ID of the quote
            
        Returns:
            PDF bytes or None if failed
        """
        try:
            # Get quote with related data
            quote = await crud_quote.get_with_details(db, id=quote_id)
            if not quote:
                return None
            
            # Create PDF buffer
            buffer = io.BytesIO()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                topMargin=1*inch,
                bottomMargin=1*inch,
                leftMargin=1*inch,
                rightMargin=1*inch
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor('#2E86AB')
            )
            
            # Build PDF content
            content = []
            
            # Title
            content.append(Paragraph(f"QUOTE #{quote.quote_number}", title_style))
            content.append(Spacer(1, 20))
            
            # Quote details
            quote_info = [
                ['Quote Number:', quote.quote_number],
                ['Date:', quote.created_at.strftime('%Y-%m-%d')],
                ['Valid Until:', quote.valid_until.strftime('%Y-%m-%d')],
                ['Tender:', quote.tender.title],
                ['Supplier:', quote.supplier.name]
            ]
            
            quote_table = Table(quote_info, colWidths=[2*inch, 4*inch])
            quote_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
            ]))
            
            content.append(quote_table)
            content.append(Spacer(1, 30))
            
            # Items table
            items_data = [['Description', 'Qty', 'Unit', 'Unit Price', 'Total']]
            
            for item in quote.items:
                items_data.append([
                    item.description,
                    str(item.quantity),
                    item.unit,
                    f"${item.unit_price:.2f}",
                    f"${item.total_price:.2f}"
                ])
            
            items_table = Table(items_data, colWidths=[3*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch])
            items_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
            ]))
            
            content.append(items_table)
            content.append(Spacer(1, 20))
            
            # Total section
            subtotal = quote.total_amount - quote.tax_amount
            total_data = [
                ['Subtotal:', f"${subtotal:.2f}"],
                ['Tax:', f"${quote.tax_amount:.2f}"],
                ['Total:', f"${quote.total_amount:.2f}"]
            ]
            
            total_table = Table(total_data, colWidths=[1.5*inch, 1*inch])
            total_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(total_table)
            
            # Terms and conditions
            if quote.terms_conditions:
                content.append(Spacer(1, 30))
                content.append(Paragraph("Terms and Conditions:", styles['Heading2']))
                content.append(Paragraph(quote.terms_conditions, styles['Normal']))
            
            # Build PDF
            doc.build(content)
            
            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info(f"PDF generated for quote {quote.quote_number}")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate PDF for quote {quote_id}: {str(e)}")
            return None
    
    async def compare_quotes(
        self,
        db: AsyncSession,
        tender_id: UUID
    ) -> Dict[str, Any]:
        """
        Compare all quotes for a tender.
        
        Args:
            db: Database session
            tender_id: ID of the tender
            
        Returns:
            Quote comparison analysis
        """
        try:
            # Get all quotes for the tender
            quotes = await crud_quote.get_by_tender(db, tender_id=tender_id)
            
            if not quotes:
                return {"error": "No quotes found for this tender"}
            
            # Analyze quotes
            comparison = {
                "tender_id": str(tender_id),
                "total_quotes": len(quotes),
                "quotes": [],
                "statistics": {
                    "lowest_price": None,
                    "highest_price": None,
                    "average_price": None,
                    "price_variance": None
                }
            }
            
            prices = []
            
            for quote in quotes:
                quote_info = {
                    "quote_id": str(quote.id),
                    "quote_number": quote.quote_number,
                    "supplier_name": quote.supplier.name,
                    "total_amount": float(quote.total_amount),
                    "submitted_at": quote.created_at,
                    "valid_until": quote.valid_until,
                    "status": quote.status
                }
                comparison["quotes"].append(quote_info)
                prices.append(float(quote.total_amount))
            
            # Calculate statistics
            if prices:
                comparison["statistics"]["lowest_price"] = min(prices)
                comparison["statistics"]["highest_price"] = max(prices)
                comparison["statistics"]["average_price"] = sum(prices) / len(prices)
                
                if len(prices) > 1:
                    variance = sum((p - comparison["statistics"]["average_price"]) ** 2 for p in prices) / len(prices)
                    comparison["statistics"]["price_variance"] = variance ** 0.5
            
            # Sort by price
            comparison["quotes"].sort(key=lambda x: x["total_amount"])
            
            logger.info(f"Quote comparison completed for tender {tender_id}")
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare quotes: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_quote_number(self, db: AsyncSession, company_id: UUID) -> str:
        """Generate unique quote number."""
        try:
            # Get count of quotes for this company this year
            current_year = datetime.utcnow().year
            count = await crud_quote.count_by_company_year(db, company_id, current_year)
            
            # Generate quote number
            quote_number = f"Q{current_year}-{count + 1:04d}"
            
            return quote_number
            
        except Exception as e:
            logger.error(f"Failed to generate quote number: {str(e)}")
            return f"Q{datetime.utcnow().year}-{datetime.utcnow().timestamp():.0f}"


# Global instance
quote_service = QuoteService()
