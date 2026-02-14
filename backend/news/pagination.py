from rest_framework.pagination import PageNumberPagination


class FlexiblePageNumberPagination(PageNumberPagination):
    """
    Pagination that respects `page_size` query parameter from the frontend.
    
    Usage: ?page=1&page_size=50
    Default: 18, Max: 200
    """
    page_size = 18
    page_size_query_param = 'page_size'
    max_page_size = 200
