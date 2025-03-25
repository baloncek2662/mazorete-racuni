from django import template
import json

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key.
    Usage: {{ dictionary|get_item:key }}
    """
    return dictionary.get(key, [])


@register.filter
def split(value, arg):
    """
    Split a string by the provided delimiter.
    Usage: {{ value|split:"delimiter" }}
    """
    return value.split(arg)


@register.filter
def pprint(obj):
    """
    Pretty print an object as JSON.
    Usage: {{ obj|pprint }}
    """
    if obj is None:
        return ""
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)
