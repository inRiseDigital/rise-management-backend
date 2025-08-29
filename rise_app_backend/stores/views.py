from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListAPIView
from django.utils.dateparse import parse_datetime



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
    def get(self, request, name):
        """
        GET /stores/store/name/<name>/
        Returns store details for the given store name.
        """
        obj = get_object_or_404(Store, name=name)
        return Response(StoreSerializer(obj).data)

