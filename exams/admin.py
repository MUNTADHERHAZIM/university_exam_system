from django.contrib import admin
from .models import (
    Exam, Question, QuestionOption, QuestionBlank, MatchingPair,
    OrderingItem, ExamAttempt, AttemptAnswer, ViolationLog, Course, ContactMessage
)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'is_resolved', 'created_at']
    list_filter = ['is_resolved', 'created_at']
    search_fields = ['user__username', 'subject', 'message']
    readonly_fields = ['created_at']

admin.site.register(Course)


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4


class QuestionBlankInline(admin.TabularInline):
    model = QuestionBlank
    extra = 1


class MatchingPairInline(admin.TabularInline):
    model = MatchingPair
    extra = 4


class OrderingItemInline(admin.TabularInline):
    model = OrderingItem
    extra = 4


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['question_type', 'text', 'marks', 'order']


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'status', 'duration', 'total_marks', 'created_by', 'created_at']
    list_filter = ['status', 'subject']
    search_fields = ['title', 'subject']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text_preview', 'question_type', 'exam', 'marks', 'order']
    list_filter = ['question_type', 'exam']
    inlines = [QuestionOptionInline, QuestionBlankInline, MatchingPairInline, OrderingItemInline]

    def text_preview(self, obj):
        return obj.text[:60]
    text_preview.short_description = 'السؤال'


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'is_submitted', 'final_score', 'grade', 'violations_count', 'submitted_at']
    list_filter = ['is_submitted', 'is_fully_graded', 'exam']
    search_fields = ['student__username', 'student__first_name']


@admin.register(ViolationLog)
class ViolationLogAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'violation_type', 'timestamp']
    list_filter = ['violation_type']


from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_maintenance_mode']
    
    def has_add_permission(self, request):
        # Prevent adding more than one instance
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
