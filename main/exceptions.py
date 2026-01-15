from rest_framework.exceptions import APIException
from rest_framework import status

class InsufficientBalanceError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Недостаточно средств на балансе'
    default_code = 'insufficient_balance'

class InsufficientStockError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Недостаточно товара на складе'
    default_code = 'insufficient_stock'

class EmptyCartError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Корзина пуста'
    default_code = 'empty_cart'