from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import logging

from django.dispatch import receiver

from main.managers import UserManager

logger = logging.getLogger(__name__)

#Пользователь
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()
    
    @property
    def cart(self):
        """Получение или создание корзины пользователя"""
        cart, _ = Cart.objects.get_or_create(user=self)
        return cart

    def __str__(self):
        return self.email


#Товар
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.price}, остаток: {self.stock})'


#Корзина
class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_cart',
    )

    @property
    def total_price(self):
        return sum(
            (item.get_total_price() for item in self.items.all()),
            Decimal('0.00')
        )
    
    @property
    def items_count(self):
        return self.items.count()

    def __str__(self):
        return f'Cart of {self.user}'


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product'],
                name='unique_cart_product'
            )
        ]

    def get_total_price(self):
        return self.product.price * self.quantity
    
    def __str__(self):
        return f'{self.product.name} * {self.quantity}'

#Заказ
class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Order #{self.id}'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    quantity = models.PositiveIntegerField()

    def get_total_price(self):
        return self.price * self.quantity
