from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/proctor/(?P<attempt_id>\d+)/$', consumers.ExamProctorConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<attempt_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/exam-monitor/(?P<exam_id>\d+)/$', consumers.ExamMonitorConsumer.as_asgi()),
]
