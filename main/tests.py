# main/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from .models import Product, CartItem, Order

User = get_user_model()

# Базовый URL для всех API запросов
API_BASE = '/api/'


class UserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_user_registration(self):
        """Тест регистрации пользователя"""
        data = {
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'newpass123'
        }
        response = self.client.post(f'{API_BASE}register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=data['email']).exists())

    def test_user_login(self):
        """Тест авторизации пользователя"""
        response = self.client.post(f'{API_BASE}token/', {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class ProductTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=Decimal('100.00'),
            stock=10
        )

    def test_get_products(self):
        """Тест получения списка товаров"""
        response = self.client.get(f'{API_BASE}products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Product')


class CartTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('100.00'),
            stock=5
        )

    def test_add_to_cart(self):
        """Тест добавления товара в корзину"""
        response = self.client.post(f'{API_BASE}cart/add/', {
            'product_id': self.product.id,
            'quantity': 2
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'added')
        self.assertEqual(CartItem.objects.count(), 1)
        cart_item = CartItem.objects.first()
        self.assertEqual(cart_item.quantity, 2)

    def test_get_cart(self):
        """Тест получения корзины"""
        CartItem.objects.create(
            cart=self.user.cart,
            product=self.product,
            quantity=1
        )
        response = self.client.get(f'{API_BASE}cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)


class OrderTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            balance=Decimal('500.00')
        )
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('100.00'),
            stock=3
        )
        
        # Добавляем товар в корзину
        CartItem.objects.create(
            cart=self.user.cart,
            product=self.product,
            quantity=2
        )

    def test_create_order_success(self):
        """Тест успешного создания заказа"""
        response = self.client.post(f'{API_BASE}orders/create/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что заказ создан
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.total_price, Decimal('200.00'))
        
        # Проверяем, что баланс списался
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal('300.00'))
        
        # Проверяем, что остатки уменьшились
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_create_order_insufficient_balance(self):
        """Тест создания заказа с недостаточным балансом"""
        self.user.balance = Decimal('50.00')
        self.user.save()
        
        response = self.client.post(f'{API_BASE}orders/create/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_insufficient_stock(self):
        """Тест создания заказа с недостаточным количеством товара"""
        self.product.stock = 1
        self.product.save()
        
        response = self.client.post(f'{API_BASE}orders/create/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BalanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            balance=Decimal('100.00')
        )
        self.client.force_authenticate(user=self.user)

    def test_top_up_balance(self):
        """Тест пополнения баланса"""
        response = self.client.post(f'{API_BASE}balance/top-up/', {'amount': '50.00'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal('150.00'))

    def test_top_up_balance_negative(self):
        """Тест пополнения баланса отрицательной суммой"""
        response = self.client.post(f'{API_BASE}balance/top-up/', {'amount': '-10.00'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)