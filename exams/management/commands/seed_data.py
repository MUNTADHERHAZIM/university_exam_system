import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile, College, Department
from exams.models import Exam, Question, QuestionOption, QuestionBlank, Course
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Populates the database with university test data: Colleges, Departments, Students, Exams, and Questions.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- بدء عملية توليد البيانات التجريبية ---'))

        # 1. Create Admin if not exists
        admin_user, created = User.objects.get_or_create(username='admin_test', is_staff=True, is_superuser=True)
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            Profile.objects.get_or_create(user=admin_user, role='admin')
            self.stdout.write(f'تم إنشاء الأدمن: {admin_user.username}')

        # 2. Colleges & Departments
        colleges_data = {
            'كلية الحاسبات وتقنية المعلومات': ['علوم الحاسب', 'نظم المعلومات'],
            'كلية الهندسة': ['الهندسة المدنية', 'الهندسة الكهربائية'],
            'كلية العلوم': ['الرياضيات', 'الفيزياء']
        }

        created_depts = []
        for c_name, depts in colleges_data.items():
            college, _ = College.objects.get_or_create(name=c_name)
            for d_name in depts:
                dept, _ = Department.objects.get_or_create(name=d_name, college=college)
                created_depts.append(dept)
        
        self.stdout.write('تم إنشاء الكليات والأقسام بنجاح.')

        # 3. Courses
        courses_list = [
            ('مقدمة في البرمجة', created_depts[0]),
            ('قواعد البيانات', created_depts[1]),
            ('الإحصاء الهندسي', created_depts[2]),
            ('الخوارزميات', created_depts[0]),
            ('أمن المعلومات', created_depts[1])
        ]
        
        created_courses = []
        for name, dept in courses_list:
            course, _ = Course.objects.get_or_create(name=name, department=dept)
            created_courses.append(course)
        
        self.stdout.write('تم إنشاء المقررات بنجاح.')

        # 4. Students
        for i in range(1, 11):
            s_user, created = User.objects.get_or_create(username=f'student{i}')
            if created:
                s_user.set_password('pass123')
                s_user.first_name = f'طالب_{i}'
                s_user.last_name = 'تجريبي'
                s_user.save()
                profile, _ = Profile.objects.get_or_create(user=s_user, role='student')
                profile.department = random.choice(created_depts)
                profile.save()
        
        self.stdout.write('تم إنشاء 10 طلاب تجريبيين.')

        # 5. Exams & Questions
        exam_titles = ['أساسيات لغة بايثون', 'مفاهيم قواعد البيانات المتقدمة', 'اختبار تجريبي شامل']
        for title in exam_titles:
            exam, created = Exam.objects.get_or_create(
                title=title,
                created_by=admin_user,
                defaults={
                    'subject': 'علوم الحاسب',
                    'duration': 60,
                    'total_marks': 100,
                    'pass_mark': 50,
                    'status': 'active',
                    'start_date': timezone.now(),
                    'end_date': timezone.now() + timedelta(days=30),
                    'course': random.choice(created_courses)
                }
            )
            
            if created:
                # Add 5 Questions to each exam
                for j in range(1, 6):
                    q = Question.objects.create(
                        exam=exam,
                        question_type='mcq_single',
                        text=f'السؤال التجريبي رقم {j} بخصوص {title}',
                        marks=20,
                        order=j
                    )
                    # Options
                    for k in range(1, 5):
                        QuestionOption.objects.create(
                            question=q,
                            text=f'الإجابة {k}',
                            is_correct=(k == 1),
                            order=k
                        )
                
                # Add a True/False
                tf_q = Question.objects.create(
                    exam=exam,
                    question_type='true_false',
                    text=f'هل تعتبر {title} من المواضيع الهامة؟',
                    marks=10,
                    order=6,
                    tf_answer=True
                )
        
        self.stdout.write('تم إنشاء 3 اختبارات مفعلة مع أسئلتها.')
        self.stdout.write(self.style.SUCCESS('--- تم الانتهاء من توليد البيانات بنجاح ---'))
