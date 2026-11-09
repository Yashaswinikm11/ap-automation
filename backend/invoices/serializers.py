from rest_framework import serializers
from .models import (
    PurchaseOrder,
    PurchaseOrderLineItem,
    GoodsReceiptNote,
    GRNLineItem,
    Invoice,
    InvoiceLineItem,
    MatchResult,
)
from vendors.models import Vendor


class VendorSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('id', 'name', 'gstin', 'onboarding_status')


class PurchaseOrderLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderLineItem
        fields = '__all__'
        extra_kwargs = {'purchase_order': {'required': False}}


class PurchaseOrderSerializer(serializers.ModelSerializer):
    line_items = PurchaseOrderLineItemSerializer(many=True, required=False)
    vendor_details = VendorSummarySerializer(source='vendor', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = '__all__'

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items', [])
        po = PurchaseOrder.objects.create(**validated_data)
        for item_data in line_items_data:
            PurchaseOrderLineItem.objects.create(purchase_order=po, **item_data)
        return po

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if line_items_data is not None:
            instance.line_items.all().delete()
            for item_data in line_items_data:
                PurchaseOrderLineItem.objects.create(purchase_order=instance, **item_data)

        return instance


class GRNLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GRNLineItem
        fields = '__all__'
        extra_kwargs = {'grn': {'required': False}}


class GoodsReceiptNoteSerializer(serializers.ModelSerializer):
    line_items = GRNLineItemSerializer(many=True, required=False)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    received_by_username = serializers.CharField(source='received_by.username', read_only=True)

    class Meta:
        model = GoodsReceiptNote
        fields = '__all__'

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items', [])
        grn = GoodsReceiptNote.objects.create(**validated_data)
        for item_data in line_items_data:
            GRNLineItem.objects.create(grn=grn, **item_data)
        return grn

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if line_items_data is not None:
            instance.line_items.all().delete()
            for item_data in line_items_data:
                GRNLineItem.objects.create(grn=instance, **item_data)

        return instance


class MatchResultSerializer(serializers.ModelSerializer):
    matched_by_username = serializers.CharField(source='matched_by.username', read_only=True)

    class Meta:
        model = MatchResult
        fields = '__all__'


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = '__all__'
        extra_kwargs = {'invoice': {'required': False}}


class InvoiceSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemSerializer(many=True, required=False)
    vendor_details = VendorSummarySerializer(source='vendor', read_only=True)
    purchase_order_details = PurchaseOrderSerializer(source='purchase_order', read_only=True)
    match_result = MatchResultSerializer(read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    effective_vendor_name = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = (
            'status',
            'validation_errors',
            'is_duplicate',
            'duplicate_of',
            'uploaded_by',
            'ocr_raw_text',
            'ocr_confidence',
        )

    def get_effective_vendor_name(self, obj):
        if obj.vendor:
            return obj.vendor.name
        return obj.vendor_name or ''

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items', [])
        invoice = Invoice.objects.create(**validated_data)
        for item_data in line_items_data:
            InvoiceLineItem.objects.create(invoice=invoice, **item_data)
        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if line_items_data is not None:
            instance.line_items.all().delete()
            for item_data in line_items_data:
                InvoiceLineItem.objects.create(invoice=instance, **item_data)

        return instance
