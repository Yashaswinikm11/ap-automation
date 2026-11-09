from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentRequestViewSet, PaymentAdviceViewSet

app_name = 'payments'

router = DefaultRouter()
router.register(r'advices', PaymentAdviceViewSet, basename='payment-advice')
router.register(r'requests', PaymentRequestViewSet, basename='payment-request')

urlpatterns = [
    path('', include(router.urls)),
]
