from decimal import Decimal

from django.shortcuts import get_object_or_404
from main.permissions import IsAdmin
from main.serializer import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import Product, CartItem
from .serializer import (
    ProductSerializer,
    CartSerializer,
    OrderSerializer,
    UserRegistrationSerializer
)
from .services import create_order, top_up_balance
from .exceptions import (
    InsufficientBalanceError,
    InsufficientStockError,
    EmptyCartError
)

from drf_spectacular.utils import extend_schema, OpenApiParameter
from .request_serializers import (
    AddToCartRequestSerializer,
    UpdateCartItemRequestSerializer,
    TopUpBalanceRequestSerializer,
)

# Товары (просмотр для всех)
class ProductListView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=ProductSerializer(many=True),
        description="Получить список активных товаров"
    )
    def get(self, request):
        products = Product.objects.filter(is_active=True)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


# Корзина пользавтеля
class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=CartSerializer,
        description="Получить текущую корзину пользователя"
    )
    def get(self, request):
        serializer = CartSerializer(request.user.cart)
        return Response(serializer.data)
    
# Добавление товара в корзину
class AddToCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=AddToCartRequestSerializer,
        responses={200: dict},
        description="Добавить товар в корзину"
    )
    def post(self, request):
        serializer = AddToCartRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        product = get_object_or_404(Product, id=product_id, is_active=True)

        if quantity > product.stock:
            raise ValidationError({
                'quantity': f'Доступно только {product.stock} шт.'
            })

        item, created = CartItem.objects.get_or_create(
            cart=request.user.cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            if item.quantity + quantity > product.stock:
                raise ValidationError({
                    'quantity': f'Доступно только {product.stock} шт.'
                })
            item.quantity += quantity
            item.save(update_fields=['quantity'])

        return Response({'status': 'added'})


# Удаление товара из корзины
class RemoveFromCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="product_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID товара"
            )
        ],
        responses={204: None},
        description="Удалить товар из корзины"
    )
    def delete(self, request, product_id):
        deleted, _ = CartItem.objects.filter(
            cart=request.user.cart,
            product_id=product_id
        ).delete()

        if deleted == 0:
            raise ValidationError({'product_id': 'Товар отсутствует в корзине'})

        return Response(status=status.HTTP_204_NO_CONTENT)

    
# Обновить количество товаров
class UpdateCartItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=UpdateCartItemRequestSerializer,
        parameters=[
            OpenApiParameter(
                name="product_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID товара"
            )
        ],
        responses={200: dict},
        description="Обновить количество товара в корзине"
    )
    def patch(self, request, product_id):
        serializer = UpdateCartItemRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data['quantity']

        item = get_object_or_404(
            CartItem,
            cart=request.user.cart,
            product_id=product_id
        )
        item.quantity = quantity
        item.save(update_fields=['quantity'])

        return Response({'status': 'updated'})


    
# Создание заказа
class CreateOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={201: OrderSerializer},
        description="Создать заказ из текущей корзины"
    )
    def post(self, request):
        try:
            order = create_order(request.user)
        except EmptyCartError as e:
            return Response({'detail': str(e)}, status=400)
        except (InsufficientStockError, InsufficientBalanceError) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=201)

#=============
# ПОЛЬЗОВАТЕЛЬ
# ============

# Профиль
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=UserSerializer,
        description="Профиль текущего пользователя"
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    
# Регистрация пользователя
class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=UserRegistrationSerializer,
        responses={201: None},
        description="Регистрация нового пользователя"
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Пользователь успешно создан'},
            status=status.HTTP_201_CREATED
        )

    
# Пополнение баланса
class TopUpBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=TopUpBalanceRequestSerializer,
        responses={200: dict, 400: None},
        description="Пополнить баланс пользователя"
    )
    def post(self, request):
        serializer = TopUpBalanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            top_up_balance(request.user, serializer.validated_data['amount'])
        except DjangoValidationError as e:
            raise DRFValidationError({'amount': str(e)})
        
        return Response({'status': 'balance topped up'})

# ADMIN
# Создание товара
class ProductCreateView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=ProductSerializer,
        responses=ProductSerializer,
        description="Создать новый товар (только админ)"
    )
    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        return Response(ProductSerializer(product).data, status=201)
    
# Редактирование и удаление товара
class ProductUpdateDeleteView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=ProductSerializer,
        responses=ProductSerializer,
        description="Обновить товар (только админ)"
    )
    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductSerializer(product).data)

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response(status=204)
