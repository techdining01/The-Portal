from django.http import JsonResponse
from .models import Item, Order
from django.views.decorators.http import require_GET

@require_GET
def api_items(request):
    items = Item.objects.filter(active=True)
    data = [{"id": i.id, "name": i.name, "price": float(i.price)} for i in items]
    return JsonResponse({"items": data})

@require_GET
def api_order_status(request, reference):
    order = Order.objects.filter(reference=reference).first()
    if not order:
        return JsonResponse({"error": "not found"}, status=404)
    return JsonResponse({"reference": order.reference, "status": order.status, "amount": float(order.amount)})
