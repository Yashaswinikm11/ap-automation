from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, PurchaseOrderViewSet, GoodsReceiptNoteViewSet

app_name = 'invoices'

router = DefaultRouter()
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'grns', GoodsReceiptNoteViewSet, basename='grn')
router.register(r'', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]
