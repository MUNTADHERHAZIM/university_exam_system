from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import Department, College
from .security_utils import encrypt_data, decrypt_data
import json

class Course(models.Model):
    SEMESTER_CHOICES = [
        ('first', 'الفصل الأول'),
        ('second', 'الفصل الثاني'),
        ('summer', 'الفصل الصيفي'),
    ]
    LEVEL_CHOICES = [
        (1, 'المستوى الأول'),
        (2, 'المستوى الثاني'),
        (3, 'المستوى الثالث'),
        (4, 'المستوى الرابع'),
    ]
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses', verbose_name='القسم')
    name = models.CharField(max_length=200, verbose_name='اسم المادة / المقرر')
    code = models.CharField(max_length=20, blank=True, verbose_name='رمز المادة')
    instructor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='taught_courses', verbose_name='الأستاذ المسؤول'
    )
    level = models.PositiveIntegerField(
        choices=LEVEL_CHOICES, null=True, blank=True,
        verbose_name='المستوى الدراسي'
    )
    semester = models.CharField(
        max_length=10, choices=SEMESTER_CHOICES, blank=True,
        verbose_name='الفصل الدراسي'
    )
    is_active = models.BooleanField(default=True, verbose_name='مادة فعّالة')

    class Meta:
        verbose_name = 'المادة'
        verbose_name_plural = 'المواد'
        ordering = ['department__college__name', 'department__name', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name

    def get_college(self):
        return self.department.college if self.department else None


class Exam(models.Model):
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('closed', 'مغلق'),
    ]
    title = models.CharField(max_length=255, verbose_name='عنوان الاختبار')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='exams', verbose_name='المادة الملحقة')
    subject = models.CharField(max_length=100, blank=True, verbose_name='المادة (اختياري)')
    description = models.TextField(blank=True, verbose_name='الوصف / التعليمات')
    duration = models.PositiveIntegerField(default=90, verbose_name='المدة (بالدقائق)')
    total_marks = models.PositiveIntegerField(default=100, verbose_name='الدرجة الكلية')
    pass_mark = models.PositiveIntegerField(default=50, verbose_name='درجة النجاح')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='الحالة')
    use_course_bank = models.BooleanField(default=False, verbose_name='استخدام بنك أسئلة المادة')
    shuffle_questions = models.BooleanField(default=False, verbose_name='ترتيب عشوائي للأسئلة')
    allow_review = models.BooleanField(default=True, verbose_name='السماح بمراجعة الأسئلة')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_exams', verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ البداية')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الانتهاء')
    max_attempts = models.PositiveIntegerField(default=1, verbose_name='أقصى عدد محاولات')
    assigned_students = models.ManyToManyField(User, related_name='assigned_exams', blank=True, verbose_name='الطلاب المخصصون')
    assigned_colleges = models.ManyToManyField(College, related_name='assigned_exams', blank=True, verbose_name='الكليات المستهدفة')
    assigned_departments = models.ManyToManyField(Department, related_name='assigned_exams', blank=True, verbose_name='الأقسام المستهدفة')
    random_question_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='عدد الأسئلة العشوائية')

    # Advanced Settings
    is_mock = models.BooleanField(default=False, verbose_name='اختبار تجريبي (للتدريب)')
    require_seb = models.BooleanField(default=False, verbose_name='يتطلب متصفح آمن (SEB)')
    require_camera = models.BooleanField(default=False, verbose_name='يتطلب تحقق بالكاميرا')
    blind_grading = models.BooleanField(default=False, verbose_name='تفعيل التصحيح الأعمى (إخفاء أسماء الطلاب)')

    class Meta:
        verbose_name = 'اختبار'
        verbose_name_plural = 'الاختبارات'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_question_count(self):
        if self.random_question_count:
            return min(self.random_question_count, self.questions.count())
        return self.questions.count()

    def get_questions_total_marks(self):
        """Calculates the sum of marks of all questions currently in the exam."""
        total = self.questions.aggregate(models.Sum('marks'))['marks__sum'] or 0
        return total

    def recalculate_total_marks(self):
        """Updates the total_marks field to match the sum of question marks and saves."""
        self.total_marks = self.get_questions_total_marks()
        self.save(update_fields=['total_marks'])
        return self.total_marks

    def is_available(self):
        if self.status != 'active':
            return False
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class StudentExamOverride(models.Model):
    """Overrides for specific students (extra attempts, extra time)"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='student_overrides')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_overrides')
    extra_attempts = models.PositiveIntegerField(default=0, verbose_name='محاولات إضافية')
    extra_time_minutes = models.PositiveIntegerField(default=0, verbose_name='وقت إضافي (بالدقائق)')

    class Meta:
        verbose_name = 'استثناء طالب'
        verbose_name_plural = 'استثناءات الطلاب'
        unique_together = ['exam', 'student']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.exam.title} Override"

    def get_attempt_count(self):
        return self.attempts.filter(is_submitted=True).count()

    def get_average_score(self):
        attempts = self.attempts.filter(is_submitted=True)
        if not attempts.exists():
            return 0
        total = sum(a.get_total_score() for a in attempts)


class Question(models.Model):
    TYPE_CHOICES = [
        ('mcq_single', 'اختيار من متعدد - إجابة واحدة'),
        ('mcq_multi', 'اختيار من متعدد - إجابات متعددة'),
        ('true_false', 'صح أو خطأ'),
        ('fill_blank', 'ملء الفراغ'),
        ('short_answer', 'إجابة قصيرة'),
        ('essay', 'مقالي'),
        ('matching', 'مطابقة'),
        ('ordering', 'ترتيب'),
        ('code', 'سؤال برمجي'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'سهل'),
        ('medium', 'متوسط'),
        ('hard', 'صعب'),
    ]
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions', null=True, blank=True, verbose_name='الاختبار')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='question_bank', null=True, blank=True, verbose_name='المادة (بنك الأسئلة)')
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='نوع السؤال')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium', verbose_name='مستوى الصعوبة')
    text = models.TextField(verbose_name='نص السؤال')
    marks = models.PositiveIntegerField(default=5, verbose_name='الدرجة')
    order = models.PositiveIntegerField(default=0, verbose_name='الترتيب')
    explanation = models.TextField(blank=True, verbose_name='الشرح / التغذية الراجعة')
    image = models.ImageField(upload_to='question_images/', blank=True, null=True, verbose_name='صورة مرفقة (اختياري)')
    learning_outcome = models.CharField(max_length=255, blank=True, verbose_name='مخرجات التعلم المستهدفة')
    
    # Code question specific
    code_language = models.CharField(max_length=20, default='python', verbose_name='لغة البرمجة')
    code_template = models.TextField(blank=True, verbose_name='كود البداية (Template)')
    # For true/false
    tf_answer = models.BooleanField(null=True, blank=True, verbose_name='الإجابة (صح/خطأ)')
    # For essay - grading rubric
    rubric = models.TextField(blank=True, verbose_name='معايير التقييم')

    class Meta:
        verbose_name = 'سؤال'
        verbose_name_plural = 'الأسئلة'
        ordering = ['order', 'id']

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.text[:60]}"

    def is_auto_graded(self):
        return self.question_type in ['mcq_single', 'mcq_multi', 'true_false', 'fill_blank', 'matching', 'ordering']


class QuestionOption(models.Model):
    """Options for MCQ questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.TextField(verbose_name='نص الخيار')
    is_correct = models.BooleanField(default=False, verbose_name='صحيح')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'خيار'
        verbose_name_plural = 'الخيارات'

    def __str__(self):
        return f"{self.text[:40]} {'✓' if self.is_correct else ''}"


class QuestionBlank(models.Model):
    """Accepted answers for fill-in-the-blank"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='blanks')
    accepted_answer = models.CharField(max_length=255, verbose_name='الإجابة المقبولة')
    case_sensitive = models.BooleanField(default=False, verbose_name='حساس لحالة الأحرف')

    class Meta:
        verbose_name = 'إجابة الفراغ'
        verbose_name_plural = 'إجابات الفراغات'


class MatchingPair(models.Model):
    """Pairs for matching questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='pairs')
    left_text = models.CharField(max_length=255, verbose_name='النص الأيسر (المصطلح)')
    right_text = models.CharField(max_length=255, verbose_name='النص الأيمن (التعريف)')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'زوج المطابقة'
        verbose_name_plural = 'أزواج المطابقة'


class OrderingItem(models.Model):
    """Items for ordering questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='order_items')
    text = models.CharField(max_length=255, verbose_name='نص العنصر')
    correct_position = models.PositiveIntegerField(verbose_name='الموضع الصحيح')

    class Meta:
        ordering = ['correct_position']
        verbose_name = 'عنصر الترتيب'
        verbose_name_plural = 'عناصر الترتيب'


class ExamAttempt(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts', verbose_name='الاختبار')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attempts', verbose_name='الطالب')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    violations_count = models.PositiveIntegerField(default=0, verbose_name='عدد المخالفات')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0, verbose_name='الوقت المستغرق (ثانية)')
    final_score = models.FloatField(null=True, blank=True, verbose_name='الدرجة النهائية')
    grade = models.CharField(max_length=5, blank=True, verbose_name='التقدير')
    is_fully_graded = models.BooleanField(default=False, verbose_name='مصحح بالكامل')
    grader_notes = models.TextField(blank=True, verbose_name='ملاحظات المصحح')

    class Meta:
        verbose_name = 'محاولة اختبار'
        verbose_name_plural = 'محاولات الاختبارات'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.exam.title}"

    def get_total_score(self):
        if self.final_score is not None:
            return self.final_score
        return sum(a.earned_marks or 0 for a in self.answers.all())

    def get_percentage(self):
        score = self.get_total_score()
        if not self.exam.total_marks or self.exam.total_marks == 0:
            return 0.0
        return round((score / self.exam.total_marks) * 100, 1)

    def calculate_grade(self):
        pct = self.get_percentage()
        if pct >= 90: return 'A+'
        elif pct >= 85: return 'A'
        elif pct >= 80: return 'B+'
        elif pct >= 75: return 'B'
        elif pct >= 70: return 'C+'
        elif pct >= 65: return 'C'
        elif pct >= 60: return 'D+'
        elif pct >= 50: return 'D'
        else: return 'F'

    def needs_manual_grading(self):
        return self.answers.filter(is_graded=False).exists()

    def get_time_spent_display(self):
        minutes = self.time_spent_seconds // 60
        seconds = self.time_spent_seconds % 60
        return f"{minutes}د {seconds}ث"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers', verbose_name='المحاولة')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='instances', verbose_name='السؤال')
    selected_options = models.TextField(blank=True, verbose_name='الخيارات المختارة (MCQ)')
    answer_text = models.TextField(blank=True, verbose_name='النص (مقالي/فراغات)')
    matching_answer = models.TextField(blank=True, verbose_name='إجابة المطابقة (JSON)')
    ordering_answer = models.TextField(blank=True, verbose_name='إجابة الترتيب')
    earned_marks = models.FloatField(null=True, blank=True, verbose_name='الدرجة المكتسبة')
    is_graded = models.BooleanField(default=False, verbose_name='تم التصحيح')
    grader_comment = models.TextField(blank=True, verbose_name='ملاحظات المصحح')
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_answers')

    def save(self, *args, **kwargs):
        # Encrypt sensitive fields before saving
        if self.answer_text and not self.answer_text.startswith('gAAAA'):
            self.answer_text = encrypt_data(self.answer_text)
        if self.matching_answer and not self.matching_answer.startswith('gAAAA'):
            self.matching_answer = encrypt_data(self.matching_answer)
        if self.ordering_answer and not self.ordering_answer.startswith('gAAAA'):
            self.ordering_answer = encrypt_data(self.ordering_answer)
        super().save(*args, **kwargs)

    @property
    def decrypted_text(self):
        return decrypt_data(self.answer_text)

    @property
    def decrypted_matching(self):
        return decrypt_data(self.matching_answer)

    @property
    def decrypted_ordering(self):
        return decrypt_data(self.ordering_answer)

    class Meta:
        verbose_name = 'إجابة'
        verbose_name_plural = 'الإجابات'
        unique_together = ['attempt', 'question']

    def __str__(self):
        return f"{self.attempt.student.get_full_name()} - Q{self.question.id}"


class ViolationLog(models.Model):
    VIOLATION_TYPES = [
        ('tab_switch', 'تحويل التبويب'),
        ('window_blur', 'مغادرة النافذة'),
        ('copy_attempt', 'محاولة نسخ'),
        ('right_click', 'نقر يمين'),
        ('devtools', 'أدوات المطور'),
        ('fullscreen_exit', 'الخروج من الشاشة الكاملة'),
    ]
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='violations')
    violation_type = models.CharField(max_length=30, choices=VIOLATION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'مخالفة'
        verbose_name_plural = 'المخالفات'
        ordering = ['-timestamp']


class ProctorSnapshot(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='snapshots')
    image = models.ImageField(upload_to='proctor_snapshots/%Y/%m/%d/')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'لقطة شاشة مراقبة'
        verbose_name_plural = 'لقطات شاشة المراقبة'
        ordering = ['-timestamp']


class Notification(models.Model):
    TYPES = [
        ('new_exam', 'اختبار جديد'),
        ('result_ready', 'نتيجة جاهزة'),
        ('exam_reminder', 'تذكير باختبار'),
        ('grading_done', 'تم التصحيح'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPES, default='new_exam')
    title = models.CharField(max_length=255, verbose_name='العنوان')
    message = models.TextField(blank=True, verbose_name='الرسالة')
    link = models.CharField(max_length=500, blank=True, verbose_name='الرابط')
    is_read = models.BooleanField(default=False, verbose_name='مقروءة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} -> {self.user.username}"


class SiteSettings(models.Model):
    """
    Singleton model to store global site settings like Maintenance Mode.
    """
    is_maintenance_mode = models.BooleanField(
        default=False, 
        verbose_name="تفعيل وضع الصيانة",
        help_text="عند التفعيل، سيتم تحويل جميع الزوار لصفحة الصيانة (لا ينطبق على الإدارة)."
    )
    maintenance_message = models.TextField(
        default="بناءً على التحديثات الطارئة، الموقع حاليًا تحت الصيانة. نعتذر عن الإزعاج وسنعود قريباً!",
        verbose_name="رسالة الصيانة",
        blank=True
    )

    class Meta:
        verbose_name = 'إعدادات النظام'
        verbose_name_plural = 'إعدادات النظام'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "إعدادات النظام العامة"


class ChatMessage(models.Model):
    """Real-time messages between Proctor/Assistant and Student during exam"""
    attempt = models.ForeignKey('ExamAttempt', on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    message = models.TextField(verbose_name="الرسالة")
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        verbose_name = 'رسالة دردشة'
        verbose_name_plural = 'رسائل الدردشة'

class ContactMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_messages', verbose_name='المستخدم')
    subject = models.CharField(max_length=200, verbose_name='الموضوع')
    message = models.TextField(verbose_name='الرسالة')
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False, verbose_name='تم الرد / المعالجة')

    class Meta:
        verbose_name = 'رسالة تواصل'
        verbose_name_plural = 'رسائل التواصل'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.subject}"


class GradeAuditLog(models.Model):
    attempt = models.ForeignKey('ExamAttempt', on_delete=models.CASCADE, related_name='grade_audit_logs', verbose_name='المحاولة')
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='grade_audit_logs', verbose_name='السؤال')
    old_mark = models.FloatField(null=True, blank=True, verbose_name='الدرجة السابقة')
    new_mark = models.FloatField(verbose_name='الدرجة الجديدة')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='المُعدِّل')
    modified_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التعديل')

    class Meta:
        verbose_name = 'سجل تعديل درجة'
        verbose_name_plural = 'سجلات تعديل الدرجات'
        ordering = ['-modified_at']

    def __str__(self):
        return f"تعديل بواسطة {self.modified_by} - Q{self.question.id}"
