from django.urls import path
from .views import (
    ProductCreateView,
    ProductListView,
    CartView,
    AddToCartView,
    ProductUpdateDeleteView,
    RemoveFromCartView,
    UpdateCartItemView,
    CreateOrderView,
    ProfileView,
    TopUpBalanceView,
    RegisterView
)

urlpatterns = [
    path('products/', ProductListView.as_view()),
    path('products/create/', ProductCreateView.as_view()),
    path('products/<int:pk>/', ProductUpdateDeleteView.as_view()),

    path('cart/', CartView.as_view()),
    path('cart/add/', AddToCartView.as_view()),
    path('cart/remove/<int:product_id>/', RemoveFromCartView.as_view()),
    path('cart/update/<int:product_id>/', UpdateCartItemView.as_view()),

    path('orders/create/', CreateOrderView.as_view()),

    path('profile/', ProfileView.as_view()),
    path('balance/top-up/', TopUpBalanceView.as_view()),

    path('register/', RegisterView.as_view(), name='register'),
]