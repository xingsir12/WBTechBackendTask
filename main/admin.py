from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Product, Cart, CartItem, Order, OrderItem

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'balance', 'is_staff', 'is_active')
    ordering = ('email',)
    search_fields = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': ('balance',)}),
        ('Права', {'fields': ('is_staff', 'is_superuser', 'is_active')}),
        ('Даты', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'stock', 'is_active')
    ordering = ('-created_at',)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('get_total_price',)
    
    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = 'Общая стоимость'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'items_count', 'total_price')
    inlines = [CartItemInline]
    readonly_fields = ('total_price',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('get_total_price',)
    
    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = 'Общая стоимость'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('total_price', 'created_at')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)
