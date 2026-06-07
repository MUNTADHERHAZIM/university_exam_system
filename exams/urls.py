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
    path('exams/<int:pk>/statistics/export/', views.export_exam_results_excel, name='export_exam_results_excel'),
    path('exams/<int:pk>/duplicate/', views.exam_duplicate, name='exam_duplicate'),
    path('exams/<int:pk>/monitor/', views.exam_live_monitor, name='exam_live_monitor'),
    path('exams/<int:pk>/api/monitor/', views.api_live_monitor, name='api_live_monitor'),
    path('exams/<int:pk>/api/override/', views.api_save_override, name='exam_api_save_override'),

    # Questions
    path('exams/<int:exam_pk>/questions/add/', views.question_add, name='question_add'),
    path('questions/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('questions/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('exams/<int:exam_pk>/import/', views.import_questions, name='import_questions'),
    path('exams/<int:exam_pk>/import-excel/', views.import_questions_excel, name='import_questions_excel'),
    path('exams/<int:exam_pk>/export/', views.export_questions, name='export_questions'),
    path('samples/questions/excel/', views.download_sample_excel, name='download_sample_excel'),
    path('samples/questions/word/', views.download_sample_word, name='download_sample_word'),

    # Student exam flow
    path('exams/<int:pk>/start/', views.exam_start, name='exam_start'),
    path('attempts/<int:pk>/take/', views.exam_take, name='exam_take'),
    path('attempts/<int:pk>/submit/', views.exam_submit, name='exam_submit'),
    path('attempts/<int:attempt_pk>/save-answer/', views.save_answer_ajax, name='save_answer_ajax'),
    path('attempts/<int:attempt_pk>/violation/', views.log_violation_ajax, name='log_violation_ajax'),
    path('attempts/<int:attempt_pk>/snapshot/', views.upload_proctor_snapshot, name='upload_proctor_snapshot'),
    path('attempts/<int:attempt_pk>/snapshots/api/', views.attempt_snapshots_api, name='attempt_snapshots_api'),

    # Results
    path('attempts/<int:pk>/result/', views.exam_result, name='exam_result'),
    path('results/', views.results_list, name='results_list'),
    path('results/export/', views.export_results, name='export_results'),
    path('attempts/<int:pk>/grade/', views.grade_attempt, name='grade_attempt'),

    # Monitoring
    path('monitoring/', views.monitoring, name='monitoring'),
    path('monitoring/data/', views.monitoring_data_api, name='monitoring_data_api'),
    path('attempts/<int:attempt_pk>/live-answers/', views.attempt_live_answers_api, name='attempt_live_answers_api'),
    path('attempts/<int:attempt_pk>/force-submit/', views.force_submit, name='force_submit'),

    # Students and Instructors
    path('students/', views.students_list, name='students_list'),
    path('instructors/', views.instructors_list, name='instructors_list'),
    path('students/export/', views.export_students_excel, name='export_students_excel'),

    # Notifications
    path('notifications/api/', views.notifications_api, name='notifications_api'),
    path('api/notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('api/contact/submit/', views.contact_api_submit, name='contact_api_submit'),
    
    # Chat
    path('attempts/<int:attempt_id>/chat/send/', views.send_chat_message, name='send_chat_message'),
    path('attempts/<int:attempt_id>/chat/messages/', views.get_chat_messages, name='get_chat_messages'),
    path('attempts/<int:attempt_pk>/certificate/', views.generate_certificate, name='generate_certificate'),
    path('about/', views.about_system, name='about_system'),

    # ─── Account Management ─────────────────────────────────────────────
    path('accounts/manage/', views.account_management, name='account_management'),
    path('accounts/generate/single/', views.generate_single_account, name='generate_single_account'),
    path('accounts/generate/bulk/', views.generate_bulk_accounts, name='generate_bulk_accounts'),
    path('accounts/export/excel/', views.export_accounts_excel, name='export_accounts_excel'),
    path('accounts/print/', views.print_account_cards, name='print_account_cards'),
    path('accounts/template/download/', views.download_bulk_template, name='download_bulk_template'),
    path('accounts/switch-role/', views.switch_role, name='switch_role'),
    path('accounts/<int:pk>/delete/', views.delete_account, name='delete_account'),
    path('accounts/<int:pk>/edit/', views.edit_account, name='edit_account'),
    path('accounts/<int:pk>/reset-password/', views.reset_account_password, name='reset_account_password'),

    # ─── Academic Structure ──────────────────────────────────────────────
    path('academic/', views.academic_structure, name='academic_structure'),
    path('academic/college/add/', views.add_college, name='add_college'),
    path('academic/college/<int:pk>/edit/', views.edit_college, name='edit_college'),
    path('academic/college/<int:pk>/delete/', views.delete_college, name='delete_college'),
    path('academic/department/add/', views.add_department, name='add_department'),
    path('academic/department/<int:pk>/edit/', views.edit_department, name='edit_department'),
    path('academic/department/<int:pk>/delete/', views.delete_department, name='delete_department'),
    path('academic/course/add/', views.add_course, name='add_course'),
    path('academic/course/<int:pk>/edit/', views.edit_course, name='edit_course'),
    path('academic/course/<int:pk>/delete/', views.delete_course, name='delete_course'),

    # ─── Cascading APIs ─────────────────────────────────────────────────
    path('api/departments/', views.api_departments_by_college, name='api_departments_by_college'),
    path('api/courses/', views.api_courses_by_department, name='api_courses_by_department'),
    path('api/students/by-dept/', views.api_students_by_department, name='api_students_by_department'),
]
