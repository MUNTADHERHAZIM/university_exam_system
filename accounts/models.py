from django.db import models
from django.contrib.auth.models import User


class College(models.Model):
    name = models.CharField(max_length=100, verbose_name='اسم الكلية')
    
    class Meta:
        verbose_name = 'الكلية'
        verbose_name_plural = 'الكليات'

    def __str__(self):
        return self.name


class Department(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='departments', verbose_name='الكلية')
    name = models.CharField(max_length=100, verbose_name='اسم القسم')

    class Meta:
        verbose_name = 'القسم'
        verbose_name_plural = 'الأقسام'

    def __str__(self):
        return f"{self.name} - {self.college.name}"


class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'مشرف / أستاذ'),
        ('assistant', 'مراقب / مصحح'),
        ('student', 'طالب'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    student_id = models.CharField(max_length=20, blank=True, verbose_name='الرقم الجامعي')
    department_text = models.CharField(max_length=100, blank=True, verbose_name='القسم (نص)')
    academic_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='القسم الأكاديمي المعتمد')
    phone = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')

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
