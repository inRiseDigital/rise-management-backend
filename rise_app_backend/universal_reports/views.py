"""
Universal Report Views

Provides completely generic report generation for ANY Django model or data structure.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.apps import apps
from django.utils.dateparse import parse_date
from utils.universal_pdf_generator import generate_universal_pdf
import base64


class UniversalReportView(APIView):
    """
    Universal report generator that can create reports for ANY model or data.

    Query Parameters:
        - model: Model name (e.g., "Machine", "Store", "KitchenExpense")
        - app: App label (e.g., "oil_extraction", "stores", "kitchen")
        - format: "json" or "pdf" (default: "pdf")
        - title: Custom report title (optional)
        - start_date: Filter by date field >= start_date (optional)
        - end_date: Filter by date field <= end_date (optional)
        - date_field: Which date field to filter on (default: "date" or "created_at")

    Examples:
        /api/universal-report/?app=oil_extraction&model=Machine&format=pdf
        /api/universal-report/?app=stores&model=Store&format=json
        /api/universal-report/?app=kitchen&model=KitchenExpense&start_date=2025-09-01&end_date=2025-09-30
    """
    permission_classes = [AllowAny]

    def get(self, request):
        app_label = request.GET.get('app')
        model_name = request.GET.get('model')
        format_type = request.GET.get('format', 'pdf')
        custom_title = request.GET.get('title')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        date_field = request.GET.get('date_field', 'date')

        # Validation
        if not app_label or not model_name:
            return Response({
                "error": "Both 'app' and 'model' parameters are required",
                "example": "/api/universal-report/?app=oil_extraction&model=Machine"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get the model dynamically
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            return Response({
                "error": f"Model '{model_name}' not found in app '{app_label}'",
                "tip": "Check spelling and ensure the app and model exist"
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            # Query the model
            queryset = Model.objects.all()

            # Apply date filtering if provided
            if start_date and end_date:
                # Try common date field names
                date_fields = [date_field, 'date', 'created_at', 'created', 'timestamp']
                applied_filter = False

                for field_name in date_fields:
                    if hasattr(Model, field_name):
                        try:
                            start = parse_date(start_date)
                            end = parse_date(end_date)
                            filter_kwargs = {f"{field_name}__range": (start, end)}
                            queryset = queryset.filter(**filter_kwargs)
                            applied_filter = True
                            break
                        except Exception:
                            continue

                if not applied_filter:
                    return Response({
                        "error": f"Could not apply date filter. No recognized date field found.",
                        "available_fields": [f.name for f in Model._meta.get_fields()]
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Order by date or id
            if hasattr(Model, 'date'):
                queryset = queryset.order_by('-date')
            elif hasattr(Model, 'created_at'):
                queryset = queryset.order_by('-created_at')
            else:
                queryset = queryset.order_by('-id')

            data = list(queryset)
            count = len(data)

            # Generate title
            if custom_title:
                title = custom_title
            else:
                # Auto-generate title from model name
                title = f"{model_name} Report"
                if start_date and end_date:
                    title += f" ({start_date} to {end_date})"

            # Metadata
            metadata = {
                "total_records": count,
                "model": model_name,
                "app": app_label
            }
            if start_date and end_date:
                metadata["date_range"] = f"{start_date} to {end_date}"

            # Return JSON format
            if format_type == "json":
                # Serialize the queryset
                serialized_data = []
                for item in data:
                    item_dict = {}
                    for field in Model._meta.get_fields():
                        if not field.name.startswith('_') and hasattr(item, field.name):
                            value = getattr(item, field.name)
                            # Convert to JSON-serializable format
                            if hasattr(value, 'isoformat'):
                                item_dict[field.name] = value.isoformat()
                            elif value is None:
                                item_dict[field.name] = None
                            else:
                                item_dict[field.name] = str(value)
                    serialized_data.append(item_dict)

                return Response({
                    "title": title,
                    "metadata": metadata,
                    "data": serialized_data
                })

            # Generate PDF
            filename = f"{app_label}_{model_name}_report.pdf"
            if start_date and end_date:
                filename = f"{app_label}_{model_name}_report_{start_date}_to_{end_date}.pdf"

            # Generate PDF using universal generator
            response = generate_universal_pdf(
                title=title,
                data=data,
                description=f"Total Records: {count}",
                metadata=metadata,
                filename=filename
            )

            return response

        except Exception as e:
            return Response({
                "error": f"Failed to generate report: {str(e)}",
                "model": model_name,
                "app": app_label
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UniversalReportFromDataView(APIView):
    """
    Generate PDF from provided data (not from database query).

    This accepts data that was already retrieved by MCP tools and generates a PDF.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        title = request.data.get('title', 'Report')
        data = request.data.get('data', [])
        description = request.data.get('description', '')
        metadata = request.data.get('metadata', {})

        if not isinstance(data, list) or len(data) == 0:
            return Response({
                "success": False,
                "error": "Data must be a non-empty list"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Generate PDF using universal generator
            response = generate_universal_pdf(
                title=title,
                data=data,
                description=description,
                metadata=metadata,
                filename=f"{title.replace(' ', '_').lower()}.pdf"
            )

            # Convert to base64
            pdf_content = response.content
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return Response({
                "success": True,
                "pdf_data": pdf_base64,
                "filename": response.get('Content-Disposition', '').split('filename=')[-1].strip('"'),
                "file_size": len(pdf_content)
            })

        except Exception as e:
            return Response({
                "success": False,
                "error": f"Failed to generate PDF: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UniversalReportBase64View(APIView):
    """
    Same as UniversalReportView but returns PDF as base64 (for MCP integration).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Reuse the logic from UniversalReportView
        universal_view = UniversalReportView()
        universal_view.request = request
        universal_view.format_kwarg = None

        # Force PDF format
        request.GET = request.GET.copy()
        if 'format' not in request.GET:
            request.GET['format'] = 'pdf'

        response = universal_view.get(request)

        # If it's a regular Response (JSON error), return it
        if isinstance(response, Response):
            return response

        # If it's an HttpResponse (PDF), convert to base64
        try:
            pdf_content = response.content
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            # Extract metadata from request
            app_label = request.GET.get('app')
            model_name = request.GET.get('model')
            filename = response.get('Content-Disposition', '').split('filename=')[-1].strip('"')

            return Response({
                "success": True,
                "pdf_data": pdf_base64,
                "filename": filename,
                "file_size": len(pdf_content),
                "model": model_name,
                "app": app_label
            })

        except Exception as e:
            return Response({
                "error": f"Failed to encode PDF: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
