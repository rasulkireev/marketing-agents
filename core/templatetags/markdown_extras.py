import markdown as md
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter()
@stringfilter
def markdown(value):
    md_instance = md.Markdown(extensions=["tables"])

    html = md_instance.convert(value)

    return mark_safe(html)
