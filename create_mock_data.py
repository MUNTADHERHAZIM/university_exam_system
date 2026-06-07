import os
import django
import random
from django.utils import timezone
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_exam.settings')
django.setup()

from django.contrib.auth.models import User
from exams.models import Exam, Question, ExamAttempt, AttemptAnswer, QuestionOption
from accounts.models import Profile

def create_mock_data():
    print("--- Starting Mock Data Creation ---")
    
    # 1. Create/Get Student
    student_username = 'student_test_user' # Changed to avoid conflicts
    student_user, created = User.objects.get_or_create(username=student_username, defaults={'first_name': 'طالب', 'last_name': 'تجريبي'})
    if created:
        student_user.set_password('password123')
        student_user.save()
        Profile.objects.get_or_create(user=student_user, role='student')
        print(f"Created student: {student_user.username}")
    else:
        print(f"Using existing student: {student_user.username}")

    # 2. Create/Get Exam
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(profile__role='admin').first()
    if not admin_user:
        print("Error: No admin/superuser found to create exam.")
        return

    exam, created = Exam.objects.get_or_create(
        title='اختبار تجريبي للمراقبة الحية',
        defaults={
            'created_by': admin_user,
            'duration': 60,
            'pass_mark': 50,
            'total_marks': 100,
            'status': 'active',
            'description': 'هذا الاختبار مخصص لتجربة نظام المراقبة الحية والإحصائيات.'
        }
    )
    if created:
        print(f"Created mock exam: {exam.title}")
    else:
        # Ensure it is active
        exam.status = 'active'
        exam.save()
        print(f"Using existing exam: {exam.title}")

    # 3. Add Questions if none
    if exam.questions.count() == 0:
        q1 = Question.objects.create(exam=exam, text='ما هي عاصمة العراق؟', marks=20, question_type='mcq_single', order=1)
        QuestionOption.objects.create(question=q1, text='بغداد', is_correct=True)
        QuestionOption.objects.create(text='البصرة', is_correct=False, question=q1)
        
        q2 = Question.objects.create(exam=exam, text='اشرح عملية التمثيل الضوئي باختصار.', marks=30, question_type='short_answer', order=2)
        q3 = Question.objects.create(exam=exam, text='صح أم خطأ: الأرض كروية.', marks=10, question_type='true_false', order=3)
        print("Added 3 questions to the exam.")
        exam.recalculate_total_marks()

    # 4. Create Active Attempt (Ongoing)
    # Delete old unsubmitted attempts for this student to ensure a fresh one
    ExamAttempt.objects.filter(student=student_user, is_submitted=False).delete()
    
    attempt = ExamAttempt.objects.create(
        student=student_user,
        exam=exam,
        started_at=timezone.now() - timedelta(minutes=5),
        is_submitted=False
    )
    print(f"Started ongoing attempt for {student_user.username}")

    # 5. Add Live Answers
    # We use selected_options (TextField) for MCQ
    q1 = exam.questions.get(order=1)
    opt = q1.options.first()
    AttemptAnswer.objects.create(
        attempt=attempt, 
        question=q1, 
        selected_options=str(opt.id),
        is_graded=False
    )
    
    q2 = exam.questions.get(order=2)
    AttemptAnswer.objects.create(
        attempt=attempt, 
        question=q2, 
        answer_text='عملية الغذاء في النبات باستخدام ضوء الشمس.',
        is_graded=False
    )
    
    print("Simulated live answers for 2/3 questions.")

    # 6. Create some Submitted Attempts for Statistics
    for i in range(1, 4):
        u_name = f'student_stat_v{i}'
        u, u_created = User.objects.get_or_create(username=u_name, defaults={'first_name': f'طالب_{i}', 'last_name': 'إحصاء'})
        if u_created:
            Profile.objects.get_or_create(user=u, role='student')
        
        if not ExamAttempt.objects.filter(student=u, exam=exam, is_submitted=True).exists():
            score = random.randint(35, 95)
            sa = ExamAttempt.objects.create(
                student=u,
                exam=exam,
                started_at=timezone.now() - timedelta(hours=1),
                submitted_at=timezone.now() - timedelta(minutes=30),
                is_submitted=True,
                final_score=score,
                is_fully_graded=True,
                time_spent_seconds=random.randint(600, 1800)
            )
            print(f"Created submitted attempt for {u.username} with score {score}")

    print("--- Mock Data Creation Complete ---")
    print(f"ACTIVE ATTEMPT ID: {attempt.id}")
    print("Now refresh the monitoring page.")

if __name__ == "__main__":
    create_mock_data()
