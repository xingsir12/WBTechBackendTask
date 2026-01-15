from rest_framework import serializers


class AddToCartRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class UpdateCartItemRequestSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class TopUpBalanceRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
