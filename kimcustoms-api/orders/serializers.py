from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from customers.models import Customer
from payments.models import Payment
from payments.security import hash_payment_token, new_payment_token
from products.models import Product

from .models import Customization, Order, OrderItem


class OrderItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    personalization = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class OrderSerializer(serializers.ModelSerializer):
    payment_token = serializers.CharField(read_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    phone = serializers.CharField(write_only=True)

    payment_method = serializers.ChoiceField(
        choices=Payment.Method.choices,
        write_only=True,
    )

    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = (
            "order_number",
            "status",

            "first_name",
            "last_name",
            "email",
            "phone",

            "items",

            "subtotal",
            "delivery_fee",
            "total",

            "delivery_address",
            "delivery_city",
            "notes",

            "payment_method",
            "payment_token",
            "created_at",
        )

        read_only_fields = (
            "order_number",
            "status",
            "subtotal",
            "delivery_fee",
            "total",
            "created_at",
        )

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError(
                "Your order must contain at least one item."
            )

        product_ids = [item["product_id"] for item in items]

        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True,
        )

        product_map = {
            product.id: product
            for product in products
        }

        errors = []

        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            product = product_map.get(product_id)

            if not product:
                errors.append(
                    f"Product {product_id} is unavailable."
                )
                continue

            if quantity > product.stock_quantity:
                errors.append(
                    f"{product.name} only has "
                    f"{product.stock_quantity} item(s) in stock."
                )

        if errors:
            raise serializers.ValidationError(errors)

        return items

    def generate_order_number(self):
        while True:
            order_number = (
                f"KC-"
                f"{uuid4().hex[:8].upper()}"
            )

            if not Order.objects.filter(
                order_number=order_number
            ).exists():
                return order_number

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")

        payment_method = validated_data.pop(
            "payment_method"
        )

        first_name = validated_data.pop(
            "first_name"
        )

        last_name = validated_data.pop(
            "last_name"
        )

        email = validated_data.pop(
            "email"
        ).strip().lower()

        phone = validated_data.pop(
            "phone"
        ).strip()

        # -----------------------------
        # CUSTOMER
        # -----------------------------

        customer = (
            Customer.objects.filter(
                email__iexact=email
            )
            .first()
        )

        if customer:
            customer.first_name = first_name
            customer.last_name = last_name
            customer.phone = phone
            customer.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "phone",
                    "updated_at",
                ]
            )
        else:
            customer = Customer.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
            )

        # -----------------------------
        # ORDER
        # -----------------------------

        order = Order.objects.create(
            customer=customer,
            order_number=self.generate_order_number(),
            status=(
                Order.Status.PAYMENT_PENDING
                if payment_method
                in [
                    Payment.Method.MPESA,
                    Payment.Method.CARD,
                ]
                else Order.Status.PENDING
            ),
            subtotal=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("0.00"),
            **validated_data,
        )

        subtotal = Decimal("0.00")

        # -----------------------------
        # ORDER ITEMS
        # -----------------------------

        for item_data in items_data:
            product = Product.objects.get(
                id=item_data["product_id"],
                is_active=True,
            )

            quantity = item_data["quantity"]

            # IMPORTANT:
            # Price comes from the database,
            # never from the frontend.
            unit_price = product.price

            item_subtotal = (
                unit_price * quantity
            )

            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                unit_price=unit_price,
                quantity=quantity,
                subtotal=item_subtotal,
            )

            personalization = item_data.get(
                "personalization",
                "",
            ).strip()

            if personalization:
                Customization.objects.create(
                    order_item=order_item,
                    personalization=personalization,
                )

            subtotal += item_subtotal

        # -----------------------------
        # TOTALS
        # -----------------------------

        delivery_fee = Decimal("0.00")

        order.subtotal = subtotal
        order.delivery_fee = delivery_fee
        order.total = subtotal + delivery_fee

        order.save(
            update_fields=[
                "subtotal",
                "delivery_fee",
                "total",
                "updated_at",
            ]
        )

        # -----------------------------
        # PAYMENT
        # -----------------------------

        payment_token = new_payment_token()
        Payment.objects.create(
            order=order,
            method=payment_method,
            amount=order.total,
            status=Payment.Status.PENDING,
            initiation_token_hash=hash_payment_token(payment_token),
            initiation_token_expires_at=(
                timezone.now()
                + timedelta(seconds=settings.MPESA_INITIATION_TOKEN_TTL_SECONDS)
            ),
        )
        # Returned once, only to the checkout caller. The database retains
        # its SHA-256 hash, never the bearer token itself.
        order.payment_token = payment_token

        return order
