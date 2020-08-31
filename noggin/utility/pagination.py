import math

from flask import current_app, request


class PagedResult:
    def __init__(self, items=None, total=None, page_size=None, page_number=None):
        self.items = items or []
        self.total = total or len(self.items)
        self.page_size = page_size
        self.page_number = page_number

    @property
    def total_pages(self):
        if self.page_size == 0:
            return 1
        return math.ceil(self.total / self.page_size)

    @property
    def has_previous_page(self):
        return self.page_number > 1

    @property
    def has_next_page(self):
        return self.page_number < self.total_pages

    def page_url(self, page_number):
        if page_number < 1 or page_number > self.total_pages:
            return None
        qs = dict(request.args)
        qs.update({"page_size": self.page_size, "page_number": page_number})
        qs = "&".join(f"{k}={v}" for k, v in qs.items())
        return f"{request.path}?{qs}"

    def __repr__(self):
        return f"<PagedResult items=[{len(self.items)} items] page={self.page_number}>"

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise ValueError("Unsupported operation")
        return all(
            [
                getattr(self, attr) == getattr(other, attr)
                for attr in ["items", "total", "page_size", "page_number"]
            ]
        )


def paginated_find(ipa, representation, *args, **kwargs):
    pkey_name = representation.get_ipa_pkey()
    object_name = representation.ipa_object
    find_method = getattr(ipa, f"{object_name}_find")
    # Get parameters from the query string
    try:
        page_number = int(request.args.get('page_number'))
    except (TypeError, ValueError):
        page_number = 1
    try:
        page_size = int(request.args.get('page_size'))
    except (TypeError, ValueError):
        page_size = current_app.config["PAGE_SIZE"]
    # If we don't want pagination, take a shortcut
    if page_size == 0:
        results = find_method(*args, **kwargs, all=True)["result"]
        return PagedResult(
            items=[representation(result) for result in results],
            page_size=page_size,
            page_number=page_number,
        )
    # Get all primary keys regardless of paging
    pkeys = find_method(pkey_only=True, *args, **kwargs)["result"]
    total = len(pkeys)
    # Find out which items we need for this page
    first = (page_number - 1) * page_size
    last = first + page_size
    pkeys_page = [item[pkey_name][0] for item in pkeys[first:last]]
    if pkeys_page:
        # Batch-request the items in the page
        batch_methods = [
            {
                "method": f"{object_name}_show",
                "params": [args, {pkey_name: pkey, 'all': True}],
            }
            for pkey in pkeys_page
        ]
        items = [
            representation(result['result'])
            for result in ipa.batch(a_methods=batch_methods)['results']
        ]
    else:
        items = []

    return PagedResult(
        items=items, page_size=page_size, page_number=page_number, total=total,
    )
