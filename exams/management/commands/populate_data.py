import random
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import College, Department, Profile
from exams.models import Course, Exam, Question, QuestionOption, ExamAttempt, AttemptAnswer, ChatMessage
from django.utils import timezone

class Command(BaseCommand):
    help = 'Populates the database with professional university demo data'

    def handle(self, *args, **kwargs):
        self.stdout.write('🚀 بدء عملية توليد البيانات التجريبية...')
        
        # 1. إنشاء الكليات
        eng_college, _ = College.objects.get_or_create(name='كلية الهندسة وتكنولوجيا المعلومات')
        sci_college, _ = College.objects.get_or_create(name='كلية العلوم والآداب')
        med_college, _ = College.objects.get_or_create(name='كلية الطب والعلوم الصحية')
        
        # 2. إنشاء الأقسام
        cs_dept, _ = Department.objects.get_or_create(college=eng_college, name='علوم الحاسوب')
        cyber_dept, _ = Department.objects.get_or_create(college=eng_college, name='الأمن السيبراني')
        math_dept, _ = Department.objects.get_or_create(college=sci_college, name='الرياضيات والفيزياء')
        nurse_dept, _ = Department.objects.get_or_create(college=med_college, name='التمريض')
        
        # 3. إنشاء المواد (Courses)
        courses_data = [
            (cs_dept, 'برمجة بايثون المتقدمة', 'CS202'),
            (cs_dept, 'هياكل البيانات والخوارزميات', 'CS301'),
            (cyber_dept, 'أساسيات التشفير', 'CYB101'),
            (math_dept, 'الإحصاء الحيوي', 'MA205'),
        ]
        courses = []
        for dept, name, code in courses_data:
            c, _ = Course.objects.get_or_create(department=dept, name=name, code=code)
            courses.append(c)
            
        # 4. إنشاء الحسابات (Roles)
        # Admin / Professor
        prof_user, created = User.objects.get_or_create(username='dr_ahmed', email='ahmed@univ.edu')
        if created:
            prof_user.set_password('pass123')
            prof_user.first_name = 'د.أحمد'
            prof_user.last_name = 'القحطاني'
            prof_user.is_staff = True
            prof_user.save()
            Profile.objects.update_or_create(user=prof_user, defaults={'role': 'admin', 'academic_department': cs_dept})
            
        # Assistant / Proctor
        ast_user, created = User.objects.get_or_create(username='ast_muna', email='muna@univ.edu')
        if created:
            ast_user.set_password('pass123')
            ast_user.first_name = 'أ.منى'
            ast_user.last_name = 'الحربي'
            ast_user.save()
            Profile.objects.update_or_create(user=ast_user, defaults={'role': 'assistant', 'academic_department': cs_dept})
            
        # Students (توليد 10 طلاب)
        students = []
        for i in range(1, 11):
            s_user, created = User.objects.get_or_create(username=f'student_{i}', email=f's{i}@univ.edu')
            if created:
                s_user.set_password('pass123')
                s_user.first_name = f'طالب_{i}'
                s_user.last_name = 'الجامعي'
                s_user.save()
                Profile.objects.update_or_create(user=s_user, defaults={
                    'role': 'student', 
                    'academic_department': cs_dept if i <= 7 else cyber_dept, 
                    'student_id': f'202400{i}'
                })
            students.append(s_user)
            
        # 5. إنشاء اختبار برمجي متكامل (Python Exam)
        python_exam, created = Exam.objects.get_or_create(
            title='الاختبار النهائي لبرمجة بايثون',
            course=courses[0],
            defaults={
                'duration': 90,
                'total_marks': 100,
                'pass_mark': 60,
                'status': 'active',
                'created_by': prof_user,
                'subject': 'برمجة'
            }
        )
        
        if created:
            # Q1: MCQ Single (10 marks)
            q1 = Question.objects.create(exam=python_exam, text='أي من هذه الكلمات المحجوزة تستخدم لتعريف دالة في بايثون؟', question_type='mcq_single', marks=10)
            QuestionOption.objects.create(question=q1, text='function', is_correct=False)
            QuestionOption.objects.create(question=q1, text='def', is_correct=True)
            QuestionOption.objects.create(question=q1, text='define', is_correct=False)
            
            # Q2: MCQ Multi (20 marks)
            q2 = Question.objects.create(exam=python_exam, text='اختر أنواع البيانات الأساسية في بايثون (اختر أكثر من واحد):', question_type='mcq_multi', marks=20)
            QuestionOption.objects.create(question=q2, text='int', is_correct=True)
            QuestionOption.objects.create(question=q2, text='string', is_correct=True)
            QuestionOption.objects.create(question=q2, text='char', is_correct=False)
            
            # Q3: Essay (20 marks)
            Question.objects.create(exam=python_exam, text='اشرح ميزة الـ Dynamic Typing في لغة بايثون وفوائدها.', question_type='essay', marks=20)
            
            # Q4: Code Question (50 marks) - THE BIG ONE
            Question.objects.create(
                exam=python_exam, 
                text='المطلوب: اكتب كود بلغة بايثون لاستقبال قائمة من الأرقام، وحساب المتوسط الحسابي لها، وطباعته.', 
                question_type='code', 
                marks=50,
                code_language='python',
                code_template='# Write your solution below\n# Numbers = [10, 20, 30, 40]\n'
            )
            
        # 6. توليد بعض النتائج التجريبية (Attempts)
        for s in students[:3]:
            # Create a submitted attempt for some students
            attempt, a_created = ExamAttempt.objects.get_or_create(
                student=s, 
                exam=python_exam,
                defaults={
                    'is_submitted': True,
                    'submitted_at': timezone.now(),
                    'final_score': random.randint(70, 95),
                    'is_fully_graded': True
                }
            )
            if a_created:
                attempt.grade = attempt.calculate_grade()
                attempt.save()
                
        self.stdout.write(self.style.SUCCESS('✨ تمت العملية بنجاح! تم إضافة كليات، أقسام، مواد، 12 مستخدم، واختبار برمجي متكامل.'))
