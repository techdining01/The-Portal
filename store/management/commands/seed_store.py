from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from store.models import Category, Product
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Seed the database with sample store data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding store data...')
        
        # Create categories
        categories = self.create_categories()
        
        # Create products
        self.create_products(categories)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded store with sample data!')
        )

    def create_categories(self):
        categories_data = [
            {
                'name': 'School Uniforms',
                'description': 'Complete school uniform sets and individual pieces'
            },
            {
                'name': 'Textbooks',
                'description': 'Educational textbooks for all classes and subjects'
            },
            {
                'name': 'Exercise Books',
                'description': 'Ruled and plain exercise books for various subjects'
            },
            {
                'name': 'Writing Materials',
                'description': 'Pens, pencils, erasers, and other writing tools'
            },
            {
                'name': 'School Bags',
                'description': 'School backpacks and carrying cases'
            },
            {
                'name': 'Sports Wear',
                'description': 'Sports uniforms and physical education gear'
            },
            {
                'name': 'Art Supplies',
                'description': 'Drawing materials, paints, and craft supplies'
            },
            {
                'name': 'Shoes & Footwear',
                'description': 'School shoes, sandals, and sports shoes'
            },
            {
                'name': 'Science Kits',
                'description': 'Laboratory equipment and science experiment kits'
            },
            {
                'name': 'Electronics',
                'description': 'Calculators, tablets, and educational electronics'
            }
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')

        return categories

    def create_products(self, categories):
        products_data = [
            # School Uniforms
            {
                'name': 'Complete Boys Uniform Set',
                'description': 'Full set including shirt, trousers, tie, and belt. Made from durable, comfortable cotton blend fabric.',
                'price': 12500.00,
                'category': categories['School Uniforms'],
                'stock': 45
            },
            {
                'name': 'Complete Girls Uniform Set',
                'description': 'Full set including blouse, skirt, tie, and belt. Premium quality fabric with school colors.',
                'price': 11800.00,
                'category': categories['School Uniforms'],
                'stock': 38
            },
            {
                'name': 'School Blazer',
                'description': 'Premium school blazer with school emblem. Available in all sizes.',
                'price': 8500.00,
                'category': categories['School Uniforms'],
                'stock': 25
            },
            {
                'name': 'PE T-Shirt',
                'description': 'Cotton sports t-shirt for physical education classes. School colors with logo.',
                'price': 2500.00,
                'category': categories['School Uniforms'],
                'stock': 60
            },

            # Textbooks
            {
                'name': 'New General Mathematics SS1',
                'description': 'Comprehensive mathematics textbook for Senior Secondary 1 students. Latest curriculum.',
                'price': 3200.00,
                'category': categories['Textbooks'],
                'stock': 85
            },
            {
                'name': 'Essential English Language SS2',
                'description': 'English language textbook covering grammar, comprehension, and literature.',
                'price': 2800.00,
                'category': categories['Textbooks'],
                'stock': 72
            },
            {
                'name': 'Basic Science & Technology JSS3',
                'description': 'Integrated science textbook for Junior Secondary School year 3.',
                'price': 2950.00,
                'category': categories['Textbooks'],
                'stock': 58
            },
            {
                'name': 'Nigerian History & Government',
                'description': 'Comprehensive guide to Nigerian history and civic education.',
                'price': 2650.00,
                'category': categories['Textbooks'],
                'stock': 42
            },

            # Exercise Books
            {
                'name': '40-Leaf Exercise Book (Pack of 10)',
                'description': 'Pack of 10 ruled 40-leaf exercise books. Perfect for daily classwork.',
                'price': 1800.00,
                'category': categories['Exercise Books'],
                'stock': 120
            },
            {
                'name': '80-Leaf Note Book',
                'description': 'Single 80-leaf hardcover notebook for subjects requiring more notes.',
                'price': 450.00,
                'category': categories['Exercise Books'],
                'stock': 95
            },
            {
                'name': 'Graph Book (5-pack)',
                'description': 'Pack of 5 graph paper books for mathematics and science subjects.',
                'price': 1200.00,
                'category': categories['Exercise Books'],
                'stock': 65
            },
            {
                'name': 'Drawing Sketch Book',
                'description': 'A4 size sketch book for art and technical drawing classes.',
                'price': 850.00,
                'category': categories['Exercise Books'],
                'stock': 40
            },

            # Writing Materials
            {
                'name': 'Ballpoint Pen (Pack of 12)',
                'description': 'Pack of 12 blue ink ballpoint pens. Smooth writing, long-lasting.',
                'price': 600.00,
                'category': categories['Writing Materials'],
                'stock': 200
            },
            {
                'name': 'Mathematical Set',
                'description': 'Complete mathematical set including compass, divider, protractor, and ruler.',
                'price': 1500.00,
                'category': categories['Writing Materials'],
                'stock': 75
            },
            {
                'name': 'HB Pencils (Pack of 10)',
                'description': 'Pack of 10 high-quality HB pencils for writing and drawing.',
                'price': 400.00,
                'category': categories['Writing Materials'],
                'stock': 150
            },
            {
                'name': 'Eraser & Sharpener Combo',
                'description': 'Set of 2 erasers and 1 pencil sharpener. Durable and efficient.',
                'price': 250.00,
                'category': categories['Writing Materials'],
                'stock': 180
            },

            # School Bags
            {
                'name': 'Premium School Backpack',
                'description': 'Durable water-resistant backpack with multiple compartments and laptop sleeve.',
                'price': 7500.00,
                'category': categories['School Bags'],
                'stock': 35
            },
            {
                'name': 'Sports Duffel Bag',
                'description': 'Spacious duffel bag for sports equipment and PE gear.',
                'price': 5200.00,
                'category': categories['School Bags'],
                'stock': 28
            },
            {
                'name': 'Lunch Bag & Bottle Set',
                'description': 'Insulated lunch bag with matching water bottle. BPA-free materials.',
                'price': 3200.00,
                'category': categories['School Bags'],
                'stock': 45
            },

            # Sports Wear
            {
                'name': 'Football Jersey Set',
                'description': 'Complete football kit including jersey, shorts, and socks. School colors.',
                'price': 6800.00,
                'category': categories['Sports Wear'],
                'stock': 30
            },
            {
                'name': 'Sports Shorts',
                'description': 'Comfortable sports shorts for various physical activities.',
                'price': 2200.00,
                'category': categories['Sports Wear'],
                'stock': 55
            },
            {
                'name': 'Track Suit',
                'description': 'Full track suit for athletics and outdoor activities.',
                'price': 8900.00,
                'category': categories['Sports Wear'],
                'stock': 22
            },

            # Art Supplies
            {
                'name': 'Water Color Paint Set',
                'description': '24-color watercolor paint set with brush and mixing palette.',
                'price': 3500.00,
                'category': categories['Art Supplies'],
                'stock': 40
            },
            {
                'name': 'Colored Pencils (24-pack)',
                'description': 'Set of 24 vibrant colored pencils for art projects.',
                'price': 2800.00,
                'category': categories['Art Supplies'],
                'stock': 52
            },
            {
                'name': 'Drawing Board A3',
                'description': 'Professional A3 drawing board for technical drawing classes.',
                'price': 4200.00,
                'category': categories['Art Supplies'],
                'stock': 18
            },

            # Shoes & Footwear
            {
                'name': 'School Black Shoes',
                'description': 'Comfortable black leather school shoes with non-slip soles.',
                'price': 6500.00,
                'category': categories['Shoes & Footwear'],
                'stock': 48
            },
            {
                'name': 'Sports Running Shoes',
                'description': 'Lightweight running shoes for sports and physical education.',
                'price': 7800.00,
                'category': categories['Shoes & Footwear'],
                'stock': 36
            },
            {
                'name': 'School Sandals',
                'description': 'Comfortable school sandals with adjustable straps.',
                'price': 4200.00,
                'category': categories['Shoes & Footwear'],
                'stock': 42
            },

            # Science Kits
            {
                'name': 'Basic Chemistry Set',
                'description': 'Beginner chemistry set with safe experiments and lab equipment.',
                'price': 12500.00,
                'category': categories['Science Kits'],
                'stock': 15
            },
            {
                'name': 'Microscope Kit',
                'description': 'Student microscope with slides and preparation tools.',
                'price': 18500.00,
                'category': categories['Science Kits'],
                'stock': 12
            },
            {
                'name': 'Physics Experiment Kit',
                'description': 'Kit for basic physics experiments including mechanics and electricity.',
                'price': 9500.00,
                'category': categories['Science Kits'],
                'stock': 20
            },

            # Electronics
            {
                'name': 'Scientific Calculator',
                'description': 'Advanced scientific calculator with 300+ functions for mathematics and science.',
                'price': 4500.00,
                'category': categories['Electronics'],
                'stock': 65
            },
            {
                'name': 'Educational Tablet',
                'description': '7-inch educational tablet with pre-loaded learning apps and parental controls.',
                'price': 28500.00,
                'category': categories['Electronics'],
                'stock': 25
            },
            {
                'name': 'Digital Dictionary',
                'description': 'Electronic dictionary with 500,000+ words and thesaurus.',
                'price': 8200.00,
                'category': categories['Electronics'],
                'stock': 30
            }
        ]

        created_count = 0
        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'description': prod_data['description'],
                    'price': prod_data['price'],
                    'category': prod_data['category'],
                    'stock': prod_data['stock']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'Created product: {product.name} - ₦{product.price}')

        self.stdout.write(f'Created {created_count} products')