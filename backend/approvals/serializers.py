from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import ApprovalMatrix, ApprovalStep, ApprovalRequest, ApprovalAction
from invoices.serializers import InvoiceSerializer

User = get_user_model()


class ApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalStep
        fields = '__all__'
        extra_kwargs = {'matrix': {'required': False}}

    def validate_approver_role(self, value):
        valid_roles = {role for role, _ in User.ROLE_CHOICES if role != 'viewer'}
        if value not in valid_roles:
            raise serializers.ValidationError('Choose an active approval role: admin, approver, or clerk.')
        return value


class ApprovalMatrixSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, required=False)

    class Meta:
        model = ApprovalMatrix
        fields = '__all__'

    def create(self, validated_data):
        steps_data = validated_data.pop('steps', [])
        matrix = ApprovalMatrix.objects.create(**validated_data)
        for step_data in steps_data:
            ApprovalStep.objects.create(matrix=matrix, **step_data)
        return matrix

    def update(self, instance, validated_data):
        steps_data = validated_data.pop('steps', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if steps_data is not None:
            instance.steps.all().delete()
            for step_data in steps_data:
                ApprovalStep.objects.create(matrix=instance, **step_data)

        return instance


class ApprovalActionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ApprovalAction
        fields = '__all__'
        extra_kwargs = {'request': {'required': False}}


class ApprovalRequestSerializer(serializers.ModelSerializer):
    actions = ApprovalActionSerializer(many=True, read_only=True)
    matrix_name = serializers.CharField(source='matrix.name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    invoice_amount = serializers.DecimalField(source='invoice.total_amount', max_digits=12, decimal_places=2, read_only=True)
    vendor_name = serializers.CharField(source='invoice.vendor.name', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    current_role = serializers.SerializerMethodField()
    escalate_after_days = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = '__all__'

    def get_current_role(self, obj):
        if obj.matrix:
            step = obj.matrix.steps.filter(step_order=obj.current_step).first()
            if step:
                return step.approver_role
        return None

    def get_escalate_after_days(self, obj):
        if obj.matrix:
            step = obj.matrix.steps.filter(step_order=obj.current_step).first()
            if step:
                return step.escalate_after_days
        return None
