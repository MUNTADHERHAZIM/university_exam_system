import os
import django
import random
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_exam.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Profile, College, Department
from exams.models import Course, Exam, Question, QuestionOption

def seed_data():
    print("Clearing old data...")
    User.objects.all().delete()
    College.objects.all().delete()

    print("Creating Superuser (admin / admin)...")
    admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    Profile.objects.create(user=admin, role='admin')

    print("Creating Colleges and Departments...")
    c_eng = College.objects.create(name='كلية الهندسة وتكنولوجيا المعلومات', code='ENG')
    c_sci = College.objects.create(name='كلية العلوم والآداب', code='SCI')

    d_cs = Department.objects.create(college=c_eng, name='علوم الحاسوب', code='CS')
    d_cy = Department.objects.create(college=c_eng, name='الأمن السيبراني', code='CYB')
    d_it = Department.objects.create(college=c_eng, name='تقنية المعلومات', code='IT')
    
    d_math = Department.objects.create(college=c_sci, name='الرياضيات', code='MATH')

    print("Creating Instructors...")
    instructors = []
    for i in range(1, 4):
        inst = User.objects.create_user(f'instructor_{i}', f'inst{i}@univ.edu', 'password123')
        inst.first_name = f'أستاذ {i}'
        inst.save()
        Profile.objects.create(user=inst, role='admin', college=c_eng, academic_department=d_cs)
        instructors.append(inst)

    print("Creating Students...")
    students = []
    for i in range(1, 21):
        dept = random.choice([d_cs, d_cy, d_it])
        level = random.choice([1, 2, 3, 4])
        st = User.objects.create_user(f'student_{i}', f'st{i}@univ.edu', 'password123')
        st.first_name = f'طالب {i}'
        st.save()
        Profile.objects.create(user=st, role='student', college=c_eng, academic_department=dept, level=level, student_id=f'202400{i}')
        students.append(st)

    print("Creating Courses and Question Banks...")
    courses_data = [
        ('مقدمة في البرمجة', 'CS101', d_cs, 1),
        ('قواعد البيانات', 'CS201', d_cs, 2),
        ('أمن الشبكات', 'CYB301', d_cy, 3),
        ('هندسة البرمجيات', 'IT401', d_it, 4),
    ]

    for name, code, dept, level in courses_data:
        course = Course.objects.create(
            name=name, code=code, department=dept, level=level, semester='first', instructor=instructors[0]
        )
        
        # Add 15 questions to each course's bank
        for q in range(1, 16):
            diff = random.choice(['easy', 'medium', 'hard'])
            question = Question.objects.create(
                course=course,
                question_type='mcq_single',
                text=f'هذا سؤال عينة رقم {q} في مادة {name}. (المستوى: {diff})',
                difficulty=diff,
                marks=5,
            )
            QuestionOption.objects.create(question=question, text='الخيار الأول الصحيح', is_correct=True, order=1)
            QuestionOption.objects.create(question=question, text='خيار خاطئ أ', is_correct=False, order=2)
            QuestionOption.objects.create(question=question, text='خيار خاطئ ب', is_correct=False, order=3)
            QuestionOption.objects.create(question=question, text='خيار خاطئ ج', is_correct=False, order=4)

    print("Creating Sample Exams...")
    course = Course.objects.first()
    exam = Exam.objects.create(
        title=f'اختبار عشوائي - {course.name}',
        course=course,
        duration=60,
        total_marks=50,
        pass_mark=25,
        status='active',
        use_course_bank=True,
        random_question_count=10,
        created_by=instructors[0],
        start_date=timezone.now() - timedelta(days=1),
        end_date=timezone.now() + timedelta(days=5),
    )
    exam.assigned_students.set(students)

    print("Data seeded successfully!")

if __name__ == '__main__':
    seed_data()
