"""
Universal PDF Generator Utility

This module provides a completely generic PDF generation system that can handle
ANY data structure without hardcoding specific fields or models.

It intelligently detects data structure and creates appropriate PDF reports.
"""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.http import HttpResponse
from datetime import datetime, date
from decimal import Decimal


class UniversalPDFGenerator:
    """
    A completely generic PDF generator that works with any data structure.

    Usage:
        generator = UniversalPDFGenerator(
            title="My Report",
            data=[{...}, {...}, ...],
            description="Report description"
        )
        pdf_bytes = generator.generate()
    """

    def __init__(self, title, data, description=None, metadata=None):
        """
        Args:
            title: Report title (e.g., "Oil Extraction Machines")
            data: List of dictionaries or Django model instances
            description: Optional subtitle/description
            metadata: Optional dict with additional info (e.g., date ranges, totals)
        """
        self.title = title
        self.data = data
        self.description = description
        self.metadata = metadata or {}
        self.width, self.height = A4

    def _serialize_value(self, value):
        """Convert any Python value to a string suitable for PDF display."""
        if value is None:
            return 'N/A'
        elif isinstance(value, (datetime, date)):
            return value.strftime("%Y-%m-%d")
        elif isinstance(value, Decimal):
            return f"{float(value):.2f}"
        elif isinstance(value, bool):
            return 'Yes' if value else 'No'
        elif isinstance(value, (list, tuple)):
            return ', '.join(str(v) for v in value)
        elif isinstance(value, dict):
            return str(value)
        else:
            return str(value)

    def _extract_dict_from_item(self, item):
        """Extract dictionary from various types (dict, Django model, etc.)."""
        if isinstance(item, dict):
            return item

        # Django model instance
        if hasattr(item, '__dict__'):
            # Get all fields, excluding internal Django fields
            result = {}
            for key, value in item.__dict__.items():
                if not key.startswith('_'):
                    result[key] = value
            return result

        return {}

    def _clean_field_name(self, field_name):
        """Convert field names to human-readable format."""
        # Remove common suffixes
        field_name = field_name.replace('_id', '').replace('_at', '')

        # Convert snake_case to Title Case
        words = field_name.split('_')
        return ' '.join(word.capitalize() for word in words)

    def _detect_columns(self):
        """Automatically detect columns from data structure."""
        if not self.data:
            return []

        # Get first item to detect structure
        first_item = self._extract_dict_from_item(self.data[0])

        # Filter out unwanted columns
        excluded_fields = {'id', 'created_at', 'updated_at', 'password', 'token'}

        columns = []
        for key in first_item.keys():
            if key not in excluded_fields and not key.startswith('_'):
                columns.append({
                    'key': key,
                    'label': self._clean_field_name(key),
                    'width': self._estimate_column_width(key, first_item[key])
                })

        return columns

    def _estimate_column_width(self, key, sample_value):
        """Estimate appropriate column width based on content."""
        # Base width on field name length and sample value
        name_length = len(self._clean_field_name(key))
        value_length = len(str(sample_value)) if sample_value else 10

        estimated_chars = max(name_length, min(value_length, 30))

        # Convert to cm (rough approximation)
        width = (estimated_chars * 0.2) + 1
        return min(max(width, 2.5), 6) * cm  # Between 2.5cm and 6cm

    def generate(self):
        """Generate PDF and return as bytes."""
        from io import BytesIO

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        # Header
        current_y = self.height - 2*cm
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(self.width/2, current_y, self.title.upper())
        current_y -= 0.7*cm

        # Description
        if self.description:
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(self.width/2, current_y, self.description)
            current_y -= 0.6*cm

        # Metadata (e.g., date ranges, totals)
        if self.metadata:
            pdf.setFont("Helvetica", 9)
            for key, value in self.metadata.items():
                label = self._clean_field_name(key)
                pdf.drawRightString(self.width - 2*cm, current_y, f"{label}: {value}")
                current_y -= 0.5*cm

        current_y -= 1*cm

        # Detect columns
        columns = self._detect_columns()

        if not columns:
            # No data
            pdf.setFont("Helvetica", 12)
            pdf.drawCentredString(self.width/2, current_y, "No data available")
            pdf.save()
            buffer.seek(0)
            return buffer.getvalue()

        # Build table data
        table_data = [[col['label'] for col in columns]]

        for item in self.data:
            item_dict = self._extract_dict_from_item(item)
            row = []
            for col in columns:
                value = item_dict.get(col['key'])
                serialized = self._serialize_value(value)
                # Truncate long values
                if len(serialized) > 50:
                    serialized = serialized[:47] + '...'
                row.append(serialized)
            table_data.append(row)

        # Calculate column widths
        col_widths = [col['width'] for col in columns]
        total_width = sum(col_widths)

        # Adjust if too wide
        max_width = self.width - 3*cm
        if total_width > max_width:
            scale_factor = max_width / total_width
            col_widths = [w * scale_factor for w in col_widths]

        # Create table
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        # Draw table with pagination
        table_height = len(table_data) * 0.5*cm

        if current_y - table_height < 2*cm:
            # Need new page
            pdf.showPage()
            current_y = self.height - 3*cm

        table.wrapOn(pdf, self.width, self.height)
        table.drawOn(pdf, 1.5*cm, current_y - table_height)

        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()

    def generate_response(self, filename=None):
        """Generate PDF and return as Django HttpResponse."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.pdf"

        pdf_bytes = self.generate()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


def generate_universal_pdf(title, data, description=None, metadata=None, filename=None):
    """
    Convenience function to generate PDF from any data.

    Args:
        title: Report title
        data: List of dicts or Django model instances
        description: Optional subtitle
        metadata: Optional dict with summary info
        filename: Optional PDF filename

    Returns:
        HttpResponse with PDF

    Example:
        # For any Django model
        machines = Machine.objects.all()
        return generate_universal_pdf(
            title="Oil Extraction Machines",
            data=list(machines),
            metadata={"Total": machines.count()}
        )

        # For any dictionary data
        stores = [{"name": "Store A", "location": "Building 1"}, ...]
        return generate_universal_pdf(
            title="Store List",
            data=stores
        )
    """
    generator = UniversalPDFGenerator(title, data, description, metadata)
    return generator.generate_response(filename)
