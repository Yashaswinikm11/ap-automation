from rest_framework import serializers
from .models import PaymentRequest, PaymentAdvice
from invoices.serializers import InvoiceSerializer


class PaymentAdviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAdvice
        fields = '__all__'
        extra_kwargs = {'payment_request': {'required': False}}


class PaymentRequestSerializer(serializers.ModelSerializer):
    advice = PaymentAdviceSerializer(read_only=True)
    invoice_details = InvoiceSerializer(source='invoice', read_only=True)
    vendor_name = serializers.SerializerMethodField()
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    initiated_by_username = serializers.CharField(source='initiated_by.username', read_only=True)

    class Meta:
        model = PaymentRequest
        fields = '__all__'
        read_only_fields = ('status', 'paid_at', 'initiated_by')

    def validate(self, attrs):
        invoice = attrs.get('invoice', getattr(self.instance, 'invoice', None))
        amount = attrs.get('amount', getattr(self.instance, 'amount', None))
        if invoice is None:
            return attrs
        if invoice.status != 'approved':
            raise serializers.ValidationError({
                'invoice': 'Payment requests can only be created for approved invoices.'
            })
        if amount is not None and amount != invoice.total_amount:
            raise serializers.ValidationError({
                'amount': 'Payment amount must equal the approved invoice total.'
            })
        existing_payments = PaymentRequest.objects.filter(invoice=invoice).exclude(
            status__in=['cancelled', 'failed']
        )
        if self.instance:
            existing_payments = existing_payments.exclude(pk=self.instance.pk)
        if existing_payments.exists():
            raise serializers.ValidationError({
                'invoice': 'An active payment request already exists for this invoice.'
            })
        return attrs

    def get_vendor_name(self, obj):
        if obj.invoice:
            if obj.invoice.vendor:
                return obj.invoice.vendor.name
            return obj.invoice.vendor_name or ''
        return ''
