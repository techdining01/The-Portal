from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from django.core.files.base import ContentFile

def generate_reportlab_receipt_pdf(order):
    """
    Returns a Django ContentFile-like object suitable for saving to a FileField.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    x = 40
    y = height - 60
    p.setFont("Helvetica-Bold", 14)
    p.drawString(x, y, "BrillsPay - Payment Receipt")
    p.setFont("Helvetica", 10)
    y -= 24
    p.drawString(x, y, f"Reference: {order.reference}")
    y -= 16
    p.drawString(x, y, f"Status: {order.status}")
    y -= 16
    p.drawString(x, y, f"Paid at: {order.paid_at if order.paid_at else 'N/A'}")
    y -= 20

    p.setFont("Helvetica-Bold", 12)
    p.drawString(x, y, "Items:")
    y -= 18
    p.setFont("Helvetica", 10)
    for oi in order.order_items.all():
        line = f"{oi.product.name} x{oi.quantity} — ₦{oi.line_total()}"
        p.drawString(x + 10, y, line)
        y -= 14
        if y < 80:
            p.showPage()
            y = height - 60
    y -= 10
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x, y, f"Total: ₦{order.total}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return ContentFile(buffer.read())
