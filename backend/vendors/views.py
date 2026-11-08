from rest_framework import viewsets
from .models import Vendor
from .serializers import VendorSerializer


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    search_fields = ('name', 'gstin')
    filterset_fields = ('is_active',)