from rest_framework import serializers


class StkPushSerializer(serializers.Serializer):
    payment_token = serializers.CharField(max_length=128, write_only=True)
    phone_number = serializers.CharField(max_length=30)

    def validate(self, attrs):
        idempotency_key = self.context["request"].headers.get("Idempotency-Key", "").strip()
        if not idempotency_key:
            raise serializers.ValidationError(
                {"Idempotency-Key": "This request header is required."}
            )
        if len(idempotency_key) > 128:
            raise serializers.ValidationError(
                {"Idempotency-Key": "Must be 128 characters or fewer."}
            )
        attrs["idempotency_key"] = idempotency_key
        return attrs
