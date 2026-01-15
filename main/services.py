from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging

from .models import Order, OrderItem, User
from .exceptions import InsufficientBalanceError, InsufficientStockError, EmptyCartError

logger = logging.getLogger(__name__)

#Создание заказа из корзины пользователя
"""
    Args:
        user: Пользователь, создающий заказ
        
    Returns:
        Order: Созданный заказ
        
    Raises:
        EmptyCartError: Если корзина пуста
        InsufficientStockError: Если недостаточно товара на складе
        InsufficientBalanceError: Если недостаточно средств
"""
@transaction.atomic
def create_order(user):
    cart = user.cart
    #select_for_update() для предотвращения гонки (race condition)
    items = cart.items.select_for_update().select_related('product')

    if not items.exists():
        logger.warning(f'Попытка создать заказ из пустой корзины. Пользователь: {user.email}')
        raise EmptyCartError('Корзина пуста')
    
    total_price = Decimal('0.00')

    #Проверка остатков с блокировкой
    for item in items:
        if item.product.stock < item.quantity:
            logger.warning(
                f'Недостаточно товара {item.product.name}'
                f'Нужно: {item.quantity}, в наличии: {item.product.stock}'
            )
            raise InsufficientStockError(
                f'Недостаточно товара "{item.product.name}" на складе.'
                f'Доступно: {item.product.stock}'
            )
        
        total_price += item.product.price * item.quantity

    #Проверка баланса
    user = User.objects.select_for_update().get(pk=user.pk)

    if user.balance < total_price:
        logger.warning(
            f'Недостаточно средств у пользователя {user.email}. '
            f'Нужно: {total_price}, баланс: {user.balance}'
        )
        raise InsufficientBalanceError(
            f'Недостаточно средств. Нужно: {total_price}, баланс: {user.balance}'
        )
    
    #Списание средств
    user.balance -= total_price
    user.save(update_fields=['balance'])


    #Создание заказа
    order = Order.objects.create(
        user=user,
        total_price=total_price,
        status=Order.STATUS_PAID
    )   

    #Создание позиций заказа и обновление остатков
    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            price=item.product.price,
            quantity=item.quantity
        )
        
        #Обновление остатков товаров
        item.product.stock -= item.quantity
        item.product.save(update_fields=['stock'])

        logger.debug(
            f'Обновлены остатки товара {item.product.name}: '
            f'-{item.quantity}, осталось: {item.product.stock}'
        )
    
    #Очистка корзины
    cart.items.all().delete()

    logger.info(
        f'Успешно создан заказ #{order.id} для пользователя {user.email}. '
        f'Сумма: {total_price}, товаров: {items.count()}'
    )
    return order

#Функция пополнения баланса пользвателя
@transaction.atomic
def top_up_balance(user,amount):
    """
    Пополнение баланса пользователя.
    
    Args:
        user: Пользователь
        amount: Сумма для пополнения (положительное число)
        
    Returns:
        User: Обновленный пользователь
        
    Raises:
        ValidationError: Если сумма отрицательная
    """

    if amount <= 0:
        raise ValidationError('Сумма пополнения должна быть больше 0')
    
    user.balance += Decimal(str(amount))
    user.save(update_fields=['balance'])

    logger.info(f'Баланс пользователя {user.email} пополнен на {amount}. Новый баланс: {user.balance}')

    return user