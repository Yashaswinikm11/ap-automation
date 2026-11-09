import re
from rest_framework import serializers
from .models import Vendor


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'
        read_only_fields = ('onboarding_status',)

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and not (
            user.is_superuser or user.role in ('admin', 'clerk')
        ):
            for field_name in ('bank_account', 'bank_ifsc', 'bank_name', 'bank_branch'):
                fields.pop(field_name, None)
        return fields

    def validate_gstin(self, value):
        if not value:
            return value

        value = value.strip().upper()
        if len(value) != 15:
            raise serializers.ValidationError(
                "GSTIN must be exactly 15 characters long."
            )

        gstin_regex = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        if not re.match(gstin_regex, value):
            raise serializers.ValidationError(
                "Invalid GSTIN format. Expected 15 characters (e.g. 29ABCDE1234F1Z5)."
            )

        try:
            state_code = int(value[:2])
            if state_code < 1 or state_code > 37:
                raise serializers.ValidationError(
                    "GSTIN state code must be between 01 and 37."
                )
        except ValueError:
            raise serializers.ValidationError(
                "GSTIN state code must be numeric."
            )

        return value
