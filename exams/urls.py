from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Exam management (admin)
    path('exams/', views.exam_list, name='exam_list'),
    path('exams/create/', views.exam_create, name='exam_create'),
    path('exams/<int:pk>/edit/', views.exam_edit, name='exam_edit'),
    path('exams/<int:pk>/delete/', views.exam_delete, name='exam_delete'),
    path('exams/<int:pk>/statistics/', views.exam_statistics, name='exam_statistics'),
    path('exams/<int:pk>/duplicate/', views.exam_duplicate, name='exam_duplicate'),
    path('exams/<int:pk>/monitor/', views.exam_live_monitor, name='exam_live_monitor'),
    path('exams/<int:pk>/api/monitor/', views.api_live_monitor, name='api_live_monitor'),
    path('exams/<int:pk>/api/override/', views.api_save_override, name='exam_api_save_override'),

    # Questions
    path('exams/<int:exam_pk>/questions/add/', views.question_add, name='question_add'),
    path('questions/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('questions/<int:pk>/delete/', views.question_delete, name='question_delete'),

    # Student exam flow
    path('exams/<int:pk>/start/', views.exam_start, name='exam_start'),
    path('attempts/<int:pk>/take/', views.exam_take, name='exam_take'),
    path('attempts/<int:pk>/submit/', views.exam_submit, name='exam_submit'),
    path('attempts/<int:attempt_pk>/save-answer/', views.save_answer_ajax, name='save_answer_ajax'),
    path('attempts/<int:attempt_pk>/violation/', views.log_violation_ajax, name='log_violation_ajax'),

    # Results
    path('attempts/<int:pk>/result/', views.exam_result, name='exam_result'),
    path('results/', views.results_list, name='results_list'),
    path('results/export/', views.export_results, name='export_results'),
    path('attempts/<int:pk>/grade/', views.grade_attempt, name='grade_attempt'),

    # Monitoring
    path('monitoring/', views.monitoring, name='monitoring'),
    path('monitoring/data/', views.monitoring_data_api, name='monitoring_data_api'),
    path('attempts/<int:attempt_pk>/force-submit/', views.force_submit, name='force_submit'),

    # Students
    path('students/', views.students_list, name='students_list'),

    # Notifications
    path('notifications/api/', views.notifications_api, name='notifications_api'),
    path('api/notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('api/contact/submit/', views.contact_api_submit, name='contact_api_submit'),
    # Chat
    path('attempts/<int:attempt_id>/chat/send/', views.send_chat_message, name='send_chat_message'),
    path('attempts/<int:attempt_id>/chat/messages/', views.get_chat_messages, name='get_chat_messages'),
    path('attempts/<int:attempt_pk>/certificate/', views.generate_certificate, name='generate_certificate'),
    path('about/', views.about_system, name='about_system'),
]
