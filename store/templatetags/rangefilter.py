from django import template
register = template.Library()

@register.filter
def filter_status(queryset, statuses):
    """Filter queryset by status"""
    status_list = statuses.split(',')
    return queryset.filter(status__in=status_list)