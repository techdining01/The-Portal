import json
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder

class DecimalJSONEncoder(DjangoJSONEncoder):
    """
    JSON encoder that converts Decimal to float
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)