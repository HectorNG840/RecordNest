from django import template

register = template.Library()


@register.filter
def index(value, i):
    try:
        return value[i]
    except (IndexError, TypeError):
        return None
    
@register.filter
def smart_range(current_page, total_pages):
    current_page = int(current_page)
    total_pages = int(total_pages)
    page_list = []

    if total_pages <= 7:
        return range(1, total_pages + 1)

    if current_page > 3:
        page_list.append(1)
        if current_page > 4:
            page_list.append("...")

    for i in range(current_page - 2, current_page + 3):
        if 1 <= i <= total_pages:
            page_list.append(i)

    if current_page < total_pages - 2:
        if current_page < total_pages - 3:
            page_list.append("...")
        page_list.append(total_pages)

    return page_list
