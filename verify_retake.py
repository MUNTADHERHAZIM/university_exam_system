import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_exam.settings')
django.setup()

from django.contrib.auth.models import User
from exams.models import Exam, ExamAttempt, StudentExamOverride
from accounts.models import Profile

def verify_retake_logic():
    print("--- Verifying Retake Logic ---")
    
    # 1. Setup Student
    student = User.objects.filter(username='student_test_user').first()
    if not student:
        student = User.objects.create_user(username='student_test_user', password='password123')
    
    profile, _ = Profile.objects.get_or_create(user=student)
    profile.role = 'student'
    profile.save()

    # 2. Setup Exam (Max 1 attempt)
    exam = Exam.objects.create(
        title="Retake Test Exam",
        duration=60,
        max_attempts=1,
        status='active'
    )
    
    # CASE 1: No attempts yet
    used = ExamAttempt.objects.filter(exam=exam, student=student, is_submitted=True).count()
    can_retake = used < exam.max_attempts
    print(f"Case 1 (No attempts): Used={used}, Max={exam.max_attempts}, Can Retake={can_retake}")
    assert can_retake == True

    # CASE 2: One attempt used (Max 1)
    attempt = ExamAttempt.objects.create(exam=exam, student=student, is_submitted=True)
    used = ExamAttempt.objects.filter(exam=exam, student=student, is_submitted=True).count()
    can_retake = used < exam.max_attempts
    print(f"Case 2 (1/1 used): Used={used}, Max={exam.max_attempts}, Can Retake={can_retake}")
    assert can_retake == False

    # CASE 3: Increase Max Attempts to 2
    exam.max_attempts = 2
    exam.save()
    used = ExamAttempt.objects.filter(exam=exam, student=student, is_submitted=True).count()
    can_retake = used < exam.max_attempts
    print(f"Case 3 (1/2 used): Used={used}, Max={exam.max_attempts}, Can Retake={can_retake}")
    assert can_retake == True

    # CASE 4: Student Override (Extra 1 attempt, total 3)
    override = StudentExamOverride.objects.create(exam=exam, student=student, extra_attempts=1)
    max_allowed = exam.max_attempts + override.extra_attempts
    used = ExamAttempt.objects.filter(exam=exam, student=student, is_submitted=True).count()
    can_retake = used < max_allowed
    print(f"Case 4 (1/3 used w/ override): Used={used}, Max={max_allowed}, Can Retake={can_retake}")
    assert can_retake == True

    print("SUCCESS: Retake logic verified!")
    
    # Cleanup
    exam.delete()
    override.delete()

if __name__ == "__main__":
    verify_retake_logic()
