from django.urls import path
from .views import (
  StoreListCreate, StoreDetail,
  ProductCategoryListCreate, ProductCategoryDetail,
  ProductSubCategoryListCreate, ProductSubCategoryDetail,
  InventoryItemListCreate, InventoryItemDetail,
  InventoryReceive, InventoryIssue,
  InventoryFilterView,ProductSubCategoryByCategory, MovementListView,get_store_by_name
)

urlpatterns = [
    # Stores
    path("add_stores/", StoreListCreate.as_view(),   name="store-list-create"),
    path("add_stores/<int:pk>/", StoreDetail.as_view(),       name="store-detail"),

    # Categories
    path("categories/",           ProductCategoryListCreate.as_view(), name="cat-list-create"),
    path("categories/<int:pk>/",  ProductCategoryDetail.as_view(),     name="cat-detail"),

    # Subcategories
    path("subcategories/",        ProductSubCategoryListCreate.as_view(), name="subcat-list-create"),
    path("subcategories/<int:pk>/",ProductSubCategoryDetail.as_view(),   name="subcat-detail"),

    # Inventory items
    path("inventory/",            InventoryItemListCreate.as_view(), name="inv-list-create"),
    path("inventory/<int:pk>/",   InventoryItemDetail.as_view(),     name="inv-detail"),

    # Stock operations
    path("inventory/receive/<int:pk>/", InventoryReceive.as_view(),  name="inv-receive"),
    path("inventory/issue/<int:pk>/",   InventoryIssue.as_view(),    name="inv-issue"),

    # Filtering
    path("inventory/filter/",     InventoryFilterView.as_view(), name="inv-filter"),
    
    #subcategory by category
    path("subcategories/category/<int:category>/", ProductSubCategoryByCategory.as_view(), name="subcat-by-category"),
    
    path("inventory/movements/",        MovementListView.as_view(), name="inventory-movements"),
    
    path("by_name/", get_store_by_name.as_view(), name="get_store_by_name"),
    
    
    

]
