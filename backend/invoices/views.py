from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Invoice
from .serializers import InvoiceSerializer
from .validation import run_validation_pipeline

@method_decorator(csrf_exempt, name='dispatch') # 👈 This fixes the 403 error
class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().order_by('-created_at')
    serializer_class = InvoiceSerializer
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        # Safely assign user if authenticated, otherwise None
        user = self.request.user if self.request.user.is_authenticated else None
        
        # The models.py signal will automatically trigger the OCR!
        serializer.save(uploaded_by=user)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        invoice = self.get_object()
        result = run_validation_pipeline(invoice)
        return Response(result)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != 'validated':
            return Response({'error': 'Invoice must be validated first.'}, status=status.HTTP_400_BAD_REQUEST)
        invoice.status = 'approved'
        invoice.save()
        return Response({'status': 'approved'})