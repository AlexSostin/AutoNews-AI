from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/generation/(?P<task_id>\w+)/$', consumers.GenerationConsumer.as_asgi()),
]
