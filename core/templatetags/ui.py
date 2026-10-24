"""Iconițe SVG inline: {% load ui %} … {% icon "home" %}"""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Iconițe cu contur (stroke), viewBox 24×24
STROKE = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h5v-6h4v6h5V9.5"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5"/>'
             '<circle cx="17" cy="9" r="2.8"/><path d="M16.5 14.6c2.6.2 4.4 1.9 5 5.4"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "table": '<path d="M8 4h8v5a4 4 0 0 1-8 0V4Z"/><path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4"/>'
             '<path d="M12 13v4M8 21h8M9.5 17h5"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "shield": '<path d="M12 3 4.5 6v5.5c0 4.6 3.1 8.3 7.5 9.5 4.4-1.2 7.5-4.9 7.5-9.5V6L12 3Z"/>',
    "news": '<rect x="3" y="4" width="15" height="16" rx="2"/><path d="M18 8h3v10a2 2 0 0 1-2 2"/>'
            '<path d="M7 8h7M7 12h7M7 16h4"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 7 8.5-7"/>',
    "bag": '<path d="M5 8h14l-1.2 12.2a1 1 0 0 1-1 .8H7.2a1 1 0 0 1-1-.8L5 8Z"/><path d="M9 10V6a3 3 0 0 1 6 0v4"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h10"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "prev": '<path d="m15 5-7 7 7 7"/>',
    "next": '<path d="m9 5 7 7-7 7"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "instagram": '<rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/>'
                 '<circle cx="17.2" cy="6.8" r=".6" fill="currentColor"/>',
    "youtube": '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="m10 9.2 5 2.8-5 2.8V9.2Z" fill="currentColor"/>',
}

# Iconițe pline (fill)
FILL = {
    "facebook": '<path d="M13.5 21v-7.5h2.6l.4-3h-3V8.6c0-.9.3-1.5 1.6-1.5h1.6V4.4c-.3 0-1.2-.1-2.3-.1-2.3 0-3.9 1.4-3.9 '
                '4v2.2H7.9v3h2.6V21h3Z"/>',
    "tiktok": '<path d="M16.6 3c.3 2.3 1.6 3.7 3.9 3.9v2.6c-1.4.1-2.6-.3-3.9-1.1v5.4c0 3.6-2.7 6.2-6 6.2-3.5 0-6-2.8-5.7-6.3.3-3 '
              '2.9-5.3 6.2-5.1v2.8c-1.6-.3-3.2.6-3.4 2.4-.2 1.6 1 3 2.7 3 1.6 0 2.9-1.3 2.9-3.2V3h3.3Z"/>',
}


@register.simple_tag
def icon(name, size=22, cls=""):
    if name in FILL:
        body, attrs = FILL[name], 'fill="currentColor"'
    else:
        body = STROKE.get(name, STROKE["arrow"])
        attrs = 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
    return format_html(
        '<svg class="icon {}" width="{}" height="{}" viewBox="0 0 24 24" {} aria-hidden="true" focusable="false">{}</svg>',
        cls, size, size, mark_safe(attrs), mark_safe(body))


@register.filter
def words(value):
    """„Portocaliu în suflet” -> ["Portocaliu", "în", "suflet"] (pentru titlul mare cu cuvinte alternate)."""
    return str(value or "").split()


@register.filter
def longest_word(value):
    return max((len(w) for w in str(value or "").split()), default=1)
