from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListAPIView
from django.utils.dateparse import parse_datetime
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from datetime import datetime



from .models import (
    Store,
    ProductCategory,
    ProductSubCategory,
    InventoryItem,InventoryMovement
)
from .serializers import (
    StoreSerializer,
    ProductCategorySerializer,
    ProductSubCategorySerializer,
    InventoryItemSerializer,InventoryMovementSerializer
)

# ── Store CRUD ─────────────────────────────────────────────

class StoreListCreate(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        qs = Store.objects.all()
        return Response(StoreSerializer(qs, many=True).data)

    def post(self, request):
        ser = StoreSerializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=201)
        return Response(ser.errors, status=400)

class StoreDetail(APIView):
    
    permission_classes = [AllowAny]
    def get(self, request, pk):
        s = get_object_or_404(Store, pk=pk)
        return Response(StoreSerializer(s).data)

    def put(self, request, pk):
        s = get_object_or_404(Store, pk=pk)
        ser = StoreSerializer(s, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data)
        return Response(ser.errors, status=400)

    def delete(self, request, pk):
        s = get_object_or_404(Store, pk=pk)
        s.delete()
        return Response(status=204)


# ── Category CRUD ─────────────────────────────────────────

class ProductCategoryListCreate(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        qs = ProductCategory.objects.all()
        return Response(ProductCategorySerializer(qs, many=True).data)

    def post(self, request):
        ser = ProductCategorySerializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=201)
        return Response(ser.errors, status=400)
    
    

class ProductCategoryDetail(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        obj = get_object_or_404(ProductCategory, pk=pk)
        return Response(ProductCategorySerializer(obj).data)

    def put(self, request, pk):
        obj = get_object_or_404(ProductCategory, pk=pk)
        ser = ProductCategorySerializer(obj, data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data)
        return Response(ser.errors, status=400)

    def delete(self, request, pk):
        obj = get_object_or_404(ProductCategory, pk=pk)
        obj.delete()
        return Response(status=204)


# ── Subcategory CRUD ─────────────────────────────────────

class ProductSubCategoryListCreate(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        qs = ProductSubCategory.objects.select_related("category").all()
        return Response(ProductSubCategorySerializer(qs, many=True).data)

    def post(self, request):
        ser = ProductSubCategorySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=201)
    
    

class ProductSubCategoryDetail(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        obj = get_object_or_404(ProductSubCategory, pk=pk)
        return Response(ProductSubCategorySerializer(obj).data)

    def put(self, request, pk):
        obj = get_object_or_404(ProductSubCategory, pk=pk)
        ser = ProductSubCategorySerializer(obj, data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data)
        return Response(ser.errors, status=400)

    def delete(self, request, pk):
        obj = get_object_or_404(ProductSubCategory, pk=pk)
        obj.delete()
        return Response(
            {"ok": True, "message": "Subcategory deleted"},
            status=status.HTTP_200_OK
        )
    
# get subcategory by category id. 
class ProductSubCategoryByCategory(APIView):
    permission_classes = [AllowAny]
    def get(self, request, category):
        """
        GET /stores/subcategories/category/<category>/
        Returns only the sub‐SKUs for the given category ID.
        """
        qs = ProductSubCategory.objects.filter(category_id=category)
        serializer = ProductSubCategorySerializer(qs, many=True)
        return Response(serializer.data)
    
# ── InventoryItem CRUD ───────────────────────────────────

class InventoryItemListCreate(APIView):
    permission_classes = [AllowAny]
    def get(self, request):

        """
        GET /stores/inventory/
        Returns all inventory items in the system, selecting related store, category, and subcategory.
        """ 

        qs = InventoryItem.objects.select_related("store","category","subcategory").all()
        return Response(InventoryItemSerializer(qs, many=True).data)

    def post(self, request):
        """
        POST /stores/inventory/
        Create a new inventory item.
        Data must contain keys for 'store', 'category', 'subcategory', 'units_in_stock', and 'unit_cost'.
        Returns the newly created inventory item data. 
        """

        ser = InventoryItemSerializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=201)
        return Response(ser.errors, status=400)

class InventoryItemDetail(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        obj = get_object_or_404(InventoryItem, pk=pk)
        return Response(InventoryItemSerializer(obj).data)

    def put(self, request, pk):
        obj = get_object_or_404(InventoryItem, pk=pk)
        ser = InventoryItemSerializer(obj, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data)
        return Response(ser.errors, status=400)

    def delete(self, request, pk):
        obj = get_object_or_404(InventoryItem, pk=pk)
        obj.delete()
        return Response(status=204)


# ── Stock Operations ───────────────────────────────────────
class InventoryReceive(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        units = request.data.get("units")
        cost  = request.data.get("cost_per_unit")

        if units is None or cost is None:
            return Response({"error": "Both 'units' and 'cost_per_unit' are required"}, status=400)

        # Updates stock and writes a movement row (Option A)
        item.receive(units, cost)
        return Response(InventoryItemSerializer(item).data)


class InventoryIssue(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        units = request.data.get("units")

        if units is None:
            return Response({"error": "'units' is required"}, status=400)

        try:
            # Decreases stock and writes a movement row (Option A)
            item.issue(units)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=400)

        return Response(InventoryItemSerializer(item).data)


class MovementListView(ListAPIView):
    """List history with simple filters: ?direction=IN|OUT&store_id=&item_id=&start=&end="""
    permission_classes = [AllowAny]
    serializer_class = InventoryMovementSerializer

    def get_queryset(self):
        qs = (InventoryMovement.objects
              .select_related("item", "item__store", "item__category", "item__subcategory"))

        direction = self.request.query_params.get("direction")  # IN / OUT
        store_id  = self.request.query_params.get("store_id")
        item_id   = self.request.query_params.get("item_id")
        start     = self.request.query_params.get("start")       # ISO datetime
        end       = self.request.query_params.get("end")

        if direction in {"IN", "OUT"}:
            qs = qs.filter(direction=direction)
        if store_id:
            qs = qs.filter(item__store_id=store_id)
        if item_id:
            qs = qs.filter(item_id=item_id)
        if start:
            qs = qs.filter(occurred_at__gte=parse_datetime(start))
        if end:
            qs = qs.filter(occurred_at__lte=parse_datetime(end))

        return qs.order_by("-occurred_at")


# ── Filter endpoint ────────────────────────────────────────

class InventoryFilterView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        store_id = request.GET.get("store")
        cat_id   = request.GET.get("category")
        sub_id   = request.GET.get("sub")

        if not store_id:
            return Response({"error":"store param required"}, status=400)
        store = get_object_or_404(Store, pk=store_id)

        qs = InventoryItem.objects.filter(store_id=store_id)
        if cat_id:
            qs = qs.filter(category_id=cat_id)
            if sub_id:
                qs = qs.filter(subcategory_id=sub_id)
            else:
                category = get_object_or_404(ProductCategory, pk=cat_id)
                if category.subcategories.exists():
                    qs = qs.filter(subcategory__category_id=cat_id)
                else:
                    qs = qs.filter(subcategory__isnull=True)

        data = InventoryItemSerializer(qs, many=True).data
        return Response({"store":store.name, "items":data})

class get_store_by_name(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        name = request.GET.get("name")
        if not name:
            return Response({"error": "name query param required"}, status=400)

        obj = get_object_or_404(Store, name__iexact=name)  # case-insensitive, optional
        return Response(StoreSerializer(obj).data)


class InventoryReportDetails(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        GET /stores/inventory/report-details/
        Returns comprehensive inventory details for report generation including:
        - Total inventory items count
        - Items by store breakdown
        - Items by category breakdown
        - Low stock items (units < 10)
        - High value items summary
        - Total inventory value
        """

        # Get all inventory items with related data
        items = InventoryItem.objects.select_related("store", "category", "subcategory").all()

        # Basic stats
        total_items = items.count()
        total_value = sum(item.total_cost for item in items)

        # Items by store
        stores_summary = {}
        for item in items:
            store_name = item.store.name
            if store_name not in stores_summary:
                stores_summary[store_name] = {"count": 0, "total_value": 0}
            stores_summary[store_name]["count"] += 1
            stores_summary[store_name]["total_value"] += item.total_cost

        # Items by category
        categories_summary = {}
        for item in items:
            category_name = item.category.name if item.category else "Uncategorized"
            if category_name not in categories_summary:
                categories_summary[category_name] = {"count": 0, "total_value": 0}
            categories_summary[category_name]["count"] += 1
            categories_summary[category_name]["total_value"] += item.total_cost

        # Low stock items (less than 10 units)
        low_stock_items = []
        for item in items:
            if item.units_in_stock < 10:
                low_stock_items.append({
                    "id": item.id,
                    "store": item.store.name,
                    "category": item.category.name if item.category else None,
                    "subcategory": item.subcategory.name if item.subcategory else None,
                    "units_in_stock": item.units_in_stock,
                    "unit_cost": item.unit_cost
                })

        # High value items (top 10 by total cost)
        high_value_items = []
        sorted_items = sorted(items, key=lambda x: x.total_cost, reverse=True)[:10]
        for item in sorted_items:
            high_value_items.append({
                "id": item.id,
                "store": item.store.name,
                "category": item.category.name if item.category else None,
                "subcategory": item.subcategory.name if item.subcategory else None,
                "units_in_stock": item.units_in_stock,
                "unit_cost": item.unit_cost,
                "total_cost": item.total_cost
            })

        return Response({
            "summary": {
                "total_items": total_items,
                "total_inventory_value": float(total_value),
                "low_stock_count": len(low_stock_items),
                "stores_count": len(stores_summary),
                "categories_count": len(categories_summary)
            },
            "stores_breakdown": [
                {
                    "store_name": store,
                    "item_count": data["count"],
                    "total_value": float(data["total_value"])
                }
                for store, data in stores_summary.items()
            ],
            "categories_breakdown": [
                {
                    "category_name": category,
                    "item_count": data["count"],
                    "total_value": float(data["total_value"])
                }
                for category, data in categories_summary.items()
            ],
            "low_stock_items": low_stock_items,
            "high_value_items": high_value_items
        })


class InventoryReportPDFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        GET /stores/inventory/report-pdf/
        Generates a comprehensive PDF report of current inventory including:
        - Summary statistics
        - Items by store breakdown
        - Items by category breakdown
        - Low stock items
        - High value items
        """
        try:
            # Get all inventory items with related data
            items = InventoryItem.objects.select_related("store", "category", "subcategory").all()

            # Basic stats
            total_items = items.count()
            total_value = sum(item.total_cost for item in items)

            # Items by store
            stores_summary = {}
            for item in items:
                store_name = item.store.name
                if store_name not in stores_summary:
                    stores_summary[store_name] = {"count": 0, "total_value": 0, "items": []}
                stores_summary[store_name]["count"] += 1
                stores_summary[store_name]["total_value"] += item.total_cost
                stores_summary[store_name]["items"].append(item)

            # Items by category
            categories_summary = {}
            for item in items:
                category_name = item.category.name if item.category else "Uncategorized"
                if category_name not in categories_summary:
                    categories_summary[category_name] = {"count": 0, "total_value": 0, "items": []}
                categories_summary[category_name]["count"] += 1
                categories_summary[category_name]["total_value"] += item.total_cost
                categories_summary[category_name]["items"].append(item)

            # Low stock items (less than 10 units)
            low_stock_items = [item for item in items if item.units_in_stock < 10]

            # Create PDF response
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="inventory_report_{timestamp}.pdf"'

            pdf = canvas.Canvas(response, pagesize=A4)
            width, height = A4

            # Title
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawCentredString(width/2, height - 2*cm, "INVENTORY REPORT")

            # Summary section
            pdf.setFont("Helvetica", 12)
            pdf.drawCentredString(width/2, height - 2.7*cm, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            current_y = height - 4*cm
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(2*cm, current_y, "SUMMARY")
            current_y -= 0.7*cm

            pdf.setFont("Helvetica", 10)
            pdf.drawString(2*cm, current_y, f"Total Items: {total_items}")
            pdf.drawString(8*cm, current_y, f"Total Value: Rs. {total_value:,.2f}")
            current_y -= 0.5*cm
            pdf.drawString(2*cm, current_y, f"Number of Stores: {len(stores_summary)}")
            pdf.drawString(8*cm, current_y, f"Number of Categories: {len(categories_summary)}")
            current_y -= 0.5*cm
            pdf.drawString(2*cm, current_y, f"Low Stock Items: {len(low_stock_items)}")
            current_y -= 1.5*cm

            # Items by Store section
            if current_y < 6*cm:
                pdf.showPage()
                current_y = height - 2*cm

            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(2*cm, current_y, "INVENTORY BY STORE")
            current_y -= 1*cm

            for store_name, data in stores_summary.items():
                if current_y < 4*cm:
                    pdf.showPage()
                    current_y = height - 2*cm

                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(2*cm, current_y, f"{store_name}")
                pdf.drawRightString(width - 2*cm, current_y, f"Items: {data['count']}, Value: Rs. {data['total_value']:,.2f}")
                current_y -= 0.7*cm

                # Table for items in this store
                table_data = [['Item ID', 'Category', 'Subcategory', 'Stock', 'Unit Cost', 'Total']]
                for item in data['items'][:10]:  # Limit to first 10 items per store
                    table_data.append([
                        str(item.id),
                        item.category.name if item.category else 'N/A',
                        item.subcategory.name if item.subcategory else 'N/A',
                        f"{item.units_in_stock:.1f}",
                        f"Rs. {item.unit_cost:.2f}",
                        f"Rs. {item.total_cost:.2f}"
                    ])

                table = Table(table_data, colWidths=[1.5*cm, 3*cm, 3*cm, 2*cm, 2.5*cm, 2.5*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                table_height = len(table_data) * 0.4*cm
                if current_y - table_height < 2*cm:
                    pdf.showPage()
                    current_y = height - 2*cm

                table.wrapOn(pdf, width, height)
                table.drawOn(pdf, 2*cm, current_y - table_height)
                current_y -= (table_height + 1.5*cm)

            # Low Stock Items section
            if low_stock_items:
                if current_y < 6*cm:
                    pdf.showPage()
                    current_y = height - 2*cm

                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawString(2*cm, current_y, "LOW STOCK ITEMS (< 10 units)")
                current_y -= 1*cm

                table_data = [['Store', 'Category', 'Subcategory', 'Stock', 'Unit Cost']]
                for item in low_stock_items:
                    table_data.append([
                        item.store.name,
                        item.category.name if item.category else 'N/A',
                        item.subcategory.name if item.subcategory else 'N/A',
                        f"{item.units_in_stock:.1f}",
                        f"Rs. {item.unit_cost:.2f}"
                    ])

                table = Table(table_data, colWidths=[3*cm, 3*cm, 3*cm, 2*cm, 3*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                table_height = len(table_data) * 0.4*cm
                if current_y - table_height < 2*cm:
                    pdf.showPage()
                    current_y = height - 2*cm

                table.wrapOn(pdf, width, height)
                table.drawOn(pdf, 2*cm, current_y - table_height)

            pdf.save()
            return response

        except Exception as e:
            return Response(
                {"error": f"Failed to generate inventory PDF report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
