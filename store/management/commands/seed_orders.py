from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Product, Order, OrderItem, Transaction
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample orders and transactions'

    def handle(self, *args, **options):
        self.stdout.write('Seeding order data...')
        
        # Get some products and users
        products = list(Product.objects.all()[:10])  # Get first 10 products
        parents = User.objects.filter(role='parent')[:2]
        students = User.objects.filter(role='student')[:3]
        
        if not parents or not products:
            self.stdout.write(self.style.ERROR('Need users and products first! Run seed_users and seed_store_data'))
            return

        # Create sample orders
        orders_data = [
            {
                'user': parents[0],
                'items': [
                    {'product': products[0], 'quantity': 1, 'student': students[0] if students else None},
                    {'product': products[1], 'quantity': 2, 'student': students[0] if students else None},
                ]
            },
            {
                'user': parents[1],
                'items': [
                    {'product': products[2], 'quantity': 1, 'student': students[1] if students else None},
                    {'product': products[3], 'quantity': 1, 'student': students[1] if students else None},
                ]
            },
        ]

        statuses = ['paid', 'shipped', 'delivered', 'pending']

        for i, order_data in enumerate(orders_data):
            # Calculate total amount
            total_amount = sum(
                item['product'].price * item['quantity'] 
                for item in order_data['items']
            )
            
            # Create order
            order = Order.objects.create(
                user=order_data['user'],
                total_amount=total_amount,
                status=statuses[i % len(statuses)],
                payment_verified=(i % len(statuses) != 3),  # pending orders not verified
                created_at=datetime.now() - timedelta(days=random.randint(1, 30))
            )

            # Create order items
            for item_data in order_data['items']:
                OrderItem.objects.create(
                    order=order,
                    product=item_data['product'],
                    quantity=item_data['quantity'],
                    price=item_data['product'].price,
                    student=item_data.get('student')
                )

            # Create transaction for paid orders
            if order.payment_verified:
                transaction = Transaction.objects.create(
                    order=order,
                    paystack_reference=f"PSK_{order.order_number}_{i}",
                    amount=total_amount,
                    payment_status='success',
                    paid_at=order.created_at + timedelta(hours=1),
                    gateway_response='{"status": "success", "message": "Approved"}'
                )

            self.stdout.write(f'Created order: {order.order_number} - ₦{total_amount}')

        self.stdout.write(self.style.SUCCESS('Successfully seeded order data!'))