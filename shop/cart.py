class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")
        if not cart:
            cart = self.session["cart"] = {}
        self.cart = cart

    def add(self, item_id, quantity=1):
        item_id = str(item_id)
        if item_id in self.cart:
            self.cart[item_id]["qty"] += quantity
        else:
            self.cart[item_id] = {"qty": quantity}
        self.save()

    def remove(self, item_id):
        item_id = str(item_id)
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()

    def clear(self):
        self.session["cart"] = {}
        self.save()

    def save(self):
        self.session.modified = True
