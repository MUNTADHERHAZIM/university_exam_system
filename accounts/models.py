from django.db import models
from django.contrib.auth.models import User


class College(models.Model):
    name = models.CharField(max_length=100, verbose_name='اسم الكلية')
    code = models.CharField(max_length=10, blank=True, verbose_name='رمز الكلية')
    description = models.TextField(blank=True, verbose_name='الوصف')

    class Meta:
        verbose_name = 'الكلية'
        verbose_name_plural = 'الكليات'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_departments_count(self):
        return self.departments.count()

    def get_students_count(self):
        return Profile.objects.filter(
            role='student',
            academic_department__college=self
        ).count()

    def get_instructors_count(self):
        return Profile.objects.filter(
            role='admin',
            college=self
        ).count()


class Department(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='departments', verbose_name='الكلية')
    name = models.CharField(max_length=100, verbose_name='اسم القسم')
    code = models.CharField(max_length=10, blank=True, verbose_name='رمز القسم')
    head_of_department = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='headed_departments', verbose_name='رئيس القسم'
    )

    class Meta:
        verbose_name = 'القسم'
        verbose_name_plural = 'الأقسام'
        ordering = ['college__name', 'name']

    def __str__(self):
        return f"{self.name} - {self.college.name}"

    def get_students_count(self):
        return Profile.objects.filter(
            role='student',
            academic_department=self
        ).count()

    def get_courses_count(self):
        from exams.models import Course
        return Course.objects.filter(department=self).count()


class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'أستاذ'),
        ('assistant', 'مراقب / مصحح'),
        ('student', 'طالب'),
    ]
    LEVEL_CHOICES = [
        (1, 'المستوى الأول'),
        (2, 'المستوى الثاني'),
        (3, 'المستوى الثالث'),
        (4, 'المستوى الرابع'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    allowed_roles = models.JSONField(default=list, blank=True, verbose_name='الصلاحيات المتعددة', help_text='يخزن قائمة بالأدوار المسموحة لهذا المستخدم')
    student_id = models.CharField(max_length=20, blank=True, verbose_name='الرقم الجامعي')
    department_text = models.CharField(max_length=100, blank=True, verbose_name='القسم (نص)')
    college = models.ForeignKey(
        College, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='profiles', verbose_name='الكلية'
    )
    academic_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='القسم الأكاديمي'
    )
    level = models.PositiveIntegerField(
        choices=LEVEL_CHOICES, null=True, blank=True,
        verbose_name='المستوى الدراسي'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    is_active_account = models.BooleanField(default=True, verbose_name='حساب فعّال')
    generated_password = models.CharField(
        max_length=50, blank=True, verbose_name='كلمة المرور المولّدة',
        help_text='تُحفظ مؤقتاً لغرض الطباعة والتصدير'
    )
    created_by_admin = models.BooleanField(default=False, verbose_name='أنشئ بواسطة الإدارة')
    batch_id = models.CharField(max_length=50, blank=True, verbose_name='معرف الدفعة')
    
    # Advanced Settings
    extra_time_percentage = models.PositiveIntegerField(default=0, verbose_name='نسبة الوقت الإضافي (%)', help_text='الوقت الإضافي المخصص للطالب للحالات الخاصة (مثلاً 50 يعني زيادة 50% من وقت الاختبار الأصلي)')

    class Meta:
        verbose_name = 'ملف المستخدم'
        verbose_name_plural = 'ملفات المستخدمين'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    def is_admin(self):
        return self.role == 'admin'

    def is_assistant(self):
        return self.role == 'assistant'

    def is_student(self):
        return self.role == 'student'

    def get_college_name(self):
        if self.college:
            return self.college.name
        if self.academic_department:
            return self.academic_department.college.name
        return '-'

    def get_department_name(self):
        if self.academic_department:
            return self.academic_department.name
        return self.department_text or '-'

    def get_role_display_safe(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    def get_allowed_roles_list(self):
        # Fallback to current role if allowed_roles is empty (for legacy data)
        if not self.allowed_roles:
            return [self.role]
        return self.allowed_roles
        
    def get_allowed_roles_display(self):
        roles_dict = dict(self.ROLE_CHOICES)
        return [roles_dict.get(r, r) for r in self.get_allowed_roles_list()]

    def get_level_display_safe(self):
        if self.level:
            return self.get_level_display()
        return '-'
