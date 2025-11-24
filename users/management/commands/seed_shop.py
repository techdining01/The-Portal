# shop/management/commands/seed_shop.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from decimal import Decimal
from shop.models import Category, Product
import random

class Command(BaseCommand):
    help = "Seed the shop with categories and sample products"

    def handle(self, *args, **options):
        categories = [
            {"name": "School Fees", "description": "Termly and yearly tuition and other school fee items."},
            {"name": "Textbooks", "description": "Recommended textbooks and reference books."},
            {"name": "Uniforms", "description": "School uniforms, PE kits and related accessories."},
            {"name": "Registration Fee", "description": "Admission and registration fees."},
            {"name": "Other", "description": "Miscellaneous shop items and services."},
        ]

        created_cats = {}
        for c in categories:
            slug = slugify(c["name"])
            cat, _ = Category.objects.get_or_create(slug=slug, defaults={"name": c["name"], "description": c["description"]})
            created_cats[c["name"]] = cat
            self.stdout.write(self.style.SUCCESS(f"Category: {cat.name} (slug: {cat.slug})"))

        # Sample products
        sample_products = [
            {"name": "First Term School Fee", "product_type": "school_fee", "price": "15000.00", "category": created_cats["School Fees"], "description":"First term tuition for basic classes."},
            {"name": "Mathematics Textbook - Primary", "product_type": "textbook", "price": "2500.00", "category": created_cats["Textbooks"], "description":"Primary Mathematics textbook - recommended."},
            {"name": "School Uniform (Full Set)", "product_type": "uniform", "price": "8000.00", "category": created_cats["Uniforms"], "description":"Full uniform set including shirt, trousers/ skirt and blazer."},
            {"name": "Admission Registration", "product_type": "registration_fee", "price": "2000.00", "category": created_cats["Registration Fee"], "description":"One-time registration fee for new students."},
            {"name": "Notebooks (5pcs)", "product_type": "other", "price": "500.00", "category": created_cats["Other"], "description":"Pack of 5 ruled notebooks."},
        ]

        for p in sample_products:
            sku = p["name"].lower().replace(" ", "-") + "-" + str(random.randint(100,999))
            prod, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": p["name"],
                    "product_type": p["product_type"],
                    "description": p["description"],
                    "price": Decimal(p["price"]),
                    "category": p["category"],
                    "in_stock": True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created product: {prod.name} (sku: {prod.sku})"))
            else:
                self.stdout.write(self.style.WARNING(f"Product exists: {prod.name}"))
