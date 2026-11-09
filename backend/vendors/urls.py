from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VendorViewSet

app_name = 'vendors'

router = DefaultRouter()
router.register(r'', VendorViewSet, basename='vendor')

urlpatterns = [
    path('', include(router.urls)),
]
