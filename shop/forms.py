from django import forms
from .models import ShopItem

class ShopItemForm(forms.ModelForm):
    class Meta:
        model = ShopItem
        fields = ["name", "description", "price", "stock", "image", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }
