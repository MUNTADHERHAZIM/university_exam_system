import json
import random
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count, Q
from .models import (
    Course, Exam, Question, QuestionOption, QuestionBlank, MatchingPair,
    OrderingItem, ExamAttempt, AttemptAnswer, ViolationLog, Notification,
    ChatMessage, ContactMessage
)
from .grading import auto_grade_attempt
from accounts.models import Profile
import csv
from django.http import HttpResponse
from django.db.models import F, Max, Min


def require_role(roles):
    if isinstance(roles, str):
        roles = [roles]
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                if request.user.profile.role not in roles:
                    return HttpResponseForbidden("غير مصرح لك بالوصول")
            except Profile.DoesNotExist:
                return HttpResponseForbidden("غير مصرح لك بالوصول")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
def dashboard(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if created and (request.user.is_superuser or request.user.is_staff):
        profile.role = 'admin'
        profile.save()

    if profile.is_admin() or profile.is_assistant() or request.user.is_superuser:
        if profile.is_admin() or request.user.is_superuser:
            exams = Exam.objects.filter(created_by=request.user)
            total_attempts = ExamAttempt.objects.filter(exam__created_by=request.user, is_submitted=True)
        else:
            # Assistant sees all or specific department exams? Let's say all for now or filter by department
            exams = Exam.objects.all()
            total_attempts = ExamAttempt.objects.filter(is_submitted=True)
            
        pending_grading = total_attempts.filter(is_fully_graded=False).count()
        students_count = User.objects.filter(profile__role='student').count()
        recent_attempts = total_attempts.order_by('-submitted_at')[:5]
        
        context = {
            'profile': profile,
            'exams': exams if profile.is_admin() else None,
            'total_exams': exams.count(),
            'total_attempts': total_attempts.count(),
            'pending_grading': pending_grading,
            'students_count': students_count,
            'recent_attempts': recent_attempts,
            'active_exams': exams.filter(status='active').count(),
            'contact_messages': ContactMessage.objects.filter(is_resolved=False).order_by('-created_at')[:5],
        }
        return render(request, 'exams/dashboard_admin.html', context)
    else:
        available_exams = Exam.objects.filter(status='active').filter(
            Q(assigned_students__isnull=True) | Q(assigned_students=request.user)
        ).distinct()
        my_attempts = ExamAttempt.objects.filter(student=request.user, is_submitted=True).select_related('exam')
        attempted_exam_ids = set(my_attempts.values_list('exam_id', flat=True))
        context = {
            'available_exams': available_exams,
            'my_attempts': my_attempts,
            'attempted_exam_ids': attempted_exam_ids,
            'passed_count': sum(1 for a in my_attempts if a.get_percentage() >= a.exam.pass_mark / a.exam.total_marks * 100),
        }
        return render(request, 'exams/dashboard_student.html', context)


# ─── EXAM MANAGEMENT (Admin) ─────────────────────────────────────────────────

@require_role('admin')
def exam_list(request):
    exams = Exam.objects.filter(created_by=request.user).annotate(
        attempt_count=Count('attempts', filter=Q(attempts__is_submitted=True))
    )
    # Search
    search_q = request.GET.get('q', '').strip()
    if search_q:
        exams = exams.filter(Q(title__icontains=search_q) | Q(subject__icontains=search_q))
    # Subject filter
    subject_filter = request.GET.get('subject', '')
    if subject_filter:
        exams = exams.filter(subject=subject_filter)
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        exams = exams.filter(status=status_filter)

    # Academic filters
    college_id = request.GET.get('college')
    dept_id = request.GET.get('department')
    if college_id:
        exams = exams.filter(course__department__college_id=college_id)
    if dept_id:
        exams = exams.filter(course__department_id=dept_id)

    # Fetch choices for filters
    from accounts.models import College, Department
    colleges = College.objects.all()
    departments = Department.objects.all()
    if college_id:
        departments = departments.filter(college_id=college_id)

    subjects = Exam.objects.filter(created_by=request.user).values_list('subject', flat=True).distinct()
    context = {
        'exams': exams,
        'subjects': subjects,
        'search_q': search_q,
        'subject_filter': subject_filter,
        'status_filter': status_filter,
        'colleges': colleges,
        'departments': departments,
        'selected_college': int(college_id) if college_id else None,
        'selected_dept': int(dept_id) if dept_id else None,
    }
    return render(request, 'exams/exam_list.html', context)


@require_role('admin')
def exam_create(request):
    from accounts.models import College, Department
    if request.method == 'POST':
        exam = Exam.objects.create(
            title=request.POST['title'],
            subject=request.POST['subject'],
            course_id=request.POST.get('course'),
            description=request.POST.get('description', ''),
            duration=int(request.POST.get('duration', 90)),
            total_marks=int(request.POST.get('total_marks', 100)),
            pass_mark=int(request.POST.get('pass_mark', 50)),
            max_attempts=int(request.POST.get('max_attempts', 1)),
            shuffle_questions=request.POST.get('shuffle_questions') == 'on',
            allow_review=request.POST.get('allow_review') == 'on',
            status='draft',
            created_by=request.user,
        )
        messages.success(request, f'تم إنشاء الاختبار "{exam.title}" بنجاح')
        return redirect('exam_edit', pk=exam.pk)
    
    colleges = College.objects.all()
    departments = Department.objects.all()
    courses = Course.objects.all()
    
    return render(request, 'exams/exam_create.html', {
        'colleges': colleges,
        'departments': departments,
        'courses': courses,
    })


@require_role('admin')
def exam_edit(request, pk):
    from accounts.models import College, Department
    exam = get_object_or_404(Exam, pk=pk, created_by=request.user)
    if request.method == 'POST':
        exam.title = request.POST.get('title', exam.title)
        exam.subject = request.POST.get('subject', exam.subject)
        exam.course_id = request.POST.get('course') or None
        exam.description = request.POST.get('description', exam.description)
        exam.duration = int(request.POST.get('duration', exam.duration))
        exam.total_marks = int(request.POST.get('total_marks', exam.total_marks))
        exam.pass_mark = int(request.POST.get('pass_mark', exam.pass_mark))
        exam.max_attempts = int(request.POST.get('max_attempts', exam.max_attempts))
        exam.status = request.POST.get('status', exam.status)
        exam.shuffle_questions = request.POST.get('shuffle_questions') == 'on'
        exam.allow_review = request.POST.get('allow_review') == 'on'
        
        # Advanced Features
        random_count = request.POST.get('random_question_count')
        exam.random_question_count = int(random_count) if random_count else None
        
        # Handle scheduling dates
        start_date_str = request.POST.get('start_date', '')
        end_date_str = request.POST.get('end_date', '')
        exam.start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
        exam.end_date = datetime.fromisoformat(end_date_str) if end_date_str else None
        old_status = Exam.objects.get(pk=pk).status
        exam.save()
        
        assigned_ids = request.POST.getlist('assigned_students')
        if assigned_ids:
            exam.assigned_students.set(assigned_ids)
        else:
            exam.assigned_students.clear()

        # Notify students when exam becomes active
        if old_status != 'active' and exam.status == 'active':
            students = User.objects.filter(profile__role='student')
            for student in students:
                create_notification(
                    user=student,
                    notification_type='new_exam',
                    title=f'اختبار جديد: {exam.title}',
                    message=f'تم نشر اختبار جديد في مادة {exam.subject}',
                    link=f'/exams/{exam.pk}/start/',
                )
        messages.success(request, 'تم حفظ التعديلات وحفظ الإعدادات المتقدمة بنجاح')
        return redirect('exam_edit', pk=exam.pk)

    questions = exam.questions.prefetch_related('options', 'blanks', 'pairs', 'order_items')
    all_students = User.objects.filter(profile__role='student').order_by('first_name', 'username')
    assigned_ids = list(exam.assigned_students.values_list('id', flat=True))
    overrides = exam.student_overrides.select_related('student')
    
    colleges = College.objects.all()
    departments = Department.objects.all()
    courses = Course.objects.all()
    
    context = {
        'exam': exam,
        'questions': questions,
        'all_students': all_students,
        'assigned_ids': assigned_ids,
        'overrides': overrides,
        'colleges': colleges,
        'departments': departments,
        'courses': courses,
    }
    return render(request, 'exams/exam_edit.html', context)

def about_system(request):
    faqs = [
        {
            'q': 'كيف يمكنني البدء في استخدام النظام؟',
            'a': 'يمكنك البدء بإنشاء حساب طالب أو التواصل مع الإدارة لإعطائك صلاحيات أستاذ لإنشاء الاختبارات.'
        },
        {
            'q': 'هل يدعم النظام الهواتف المحمولة؟',
            'a': 'نعم، النظام مصمم بشكل متجاوب بالكامل ليعمل على كافة الشاشات والأجهزة اللوحية.'
        },
        {
            'q': 'كيف يتم ضمان نزاهة الاختبارات؟',
            'a': 'يعتمد النظام على تقنيات مراقبة تفاعلية مثل كشف محاولات الغش، تسجيل المخالفات تلقائياً، ومنع الخروج من المتصفح.'
        },
    ]
    return render(request, 'exams/about_system.html', {'faqs': faqs})


@require_role('admin')
def exam_live_monitor(request, pk):
    exam = get_object_or_404(Exam, pk=pk, created_by=request.user)
    return render(request, 'exams/exam_live_monitor.html', {'exam': exam})


@require_role('admin')
def api_live_monitor(request, pk):
    exam = get_object_or_404(Exam, pk=pk, created_by=request.user)
    
    recent_limit = timezone.now() - timezone.timedelta(hours=exam.duration)
    active_attempts = ExamAttempt.objects.filter(
        exam=exam,
        started_at__gte=recent_limit
    ).select_related('student', 'exam').order_by('-started_at')

    data = []
    now = timezone.now()
    for attempt in active_attempts:
        override = exam.student_overrides.filter(student=attempt.student).first()
        extra_time = override.extra_time_minutes if override else 0
        total_time_seconds = (exam.duration + extra_time) * 60
        elapsed = (now - attempt.started_at).total_seconds()
        
        if attempt.is_submitted:
            status = 'submitted'
            time_left_str = 'منتهي'
            pct = attempt.get_percentage()
        else:
            time_remaining = max(0, int(total_time_seconds - elapsed))
            if time_remaining == 0:
                status = 'time_up'
            else:
                status = 'active'
            
            m, s = divmod(time_remaining, 60)
            time_left_str = f"{m}د {s}ث"
            pct = None

        data.append({
            'student_name': attempt.student.get_full_name() or attempt.student.username,
            'status': status,
            'violations': attempt.violations_count,
            'time_left': time_left_str,
            'started_at': attempt.started_at.strftime('%H:%M'),
            'score_pct': pct,
            'ip': attempt.ip_address,
            'attempt_id': attempt.id,
        })

    return JsonResponse({'attempts': data})


@require_role('admin')
@require_POST
def api_save_override(request, pk):
    exam = get_object_or_404(Exam, pk=pk, created_by=request.user)
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        extra_attempts = int(data.get('extra_attempts', 0))
        extra_time = int(data.get('extra_time_minutes', 0))
        
        student = get_object_or_404(User, pk=student_id, profile__role='student')
        
        from .models import StudentExamOverride
        override, created = StudentExamOverride.objects.update_or_create(
            exam=exam,
            student=student,
            defaults={
                'extra_attempts': extra_attempts,
                'extra_time_minutes': extra_time
            }
        )
        return JsonResponse({'status': 'success', 'msg': 'تم حفظ الاستثناء بنجاح'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=400)


@require_role('admin')
def exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk, created_by=request.user)
    if request.method == 'POST':
        title = exam.title
        exam.delete()
        messages.success(request, f'تم حذف الاختبار "{title}"')
        return redirect('exam_list')
    return render(request, 'exams/exam_confirm_delete.html', {'exam': exam})


# ─── QUESTION MANAGEMENT ─────────────────────────────────────────────────────

def _save_question_components(question, request):
    qtype = question.question_type
    
    # Handle True/False
    if qtype == 'true_false':
        question.tf_answer = request.POST.get('tf_answer') == 'true'
        question.save()

    # Handle MCQ options
    elif qtype in ['mcq_single', 'mcq_multi']:
        question.options.all().delete()
        options = request.POST.getlist('option_text')
        corrects = request.POST.getlist('option_correct')
        for i, opt_text in enumerate(options):
            if opt_text.strip():
                QuestionOption.objects.create(
                    question=question,
                    text=opt_text.strip(),
                    is_correct=(str(i) in corrects),
                    order=i,
                )

    # Handle Fill blank
    elif qtype == 'fill_blank':
        question.blanks.all().delete()
        answers = request.POST.getlist('blank_answer')
        for ans in answers:
            if ans.strip():
                QuestionBlank.objects.create(
                    question=question,
                    accepted_answer=ans.strip(),
                    case_sensitive=False,
                )

    # Handle Matching
    elif qtype == 'matching':
        question.pairs.all().delete()
        lefts = request.POST.getlist('left_text')
        rights = request.POST.getlist('right_text')
        for i, (l, r) in enumerate(zip(lefts, rights)):
            if l.strip() and r.strip():
                MatchingPair.objects.create(
                    question=question,
                    left_text=l.strip(),
                    right_text=r.strip(),
                    order=i,
                )

    # Handle Ordering
    elif qtype == 'ordering':
        question.order_items.all().delete()
        items = request.POST.getlist('order_item')
        for i, item in enumerate(items):
            if item.strip():
                OrderingItem.objects.create(
                    question=question,
                    text=item.strip(),
                    correct_position=i,
                )

    # Handle Code
    elif qtype == 'code':
        question.code_language = request.POST.get('code_language', 'python')
        question.code_template = request.POST.get('code_template', '')
        question.save()


@require_role('admin')
def question_add(request, exam_pk):
    exam = get_object_or_404(Exam, pk=exam_pk, created_by=request.user)
    if request.method == 'POST':
        qtype = request.POST['question_type']
        marks = int(request.POST.get('marks', 5))
        order = exam.questions.count() + 1

        question = Question.objects.create(
            exam=exam,
            question_type=qtype,
            text=request.POST['text'],
            marks=marks,
            order=order,
            explanation=request.POST.get('explanation', ''),
            rubric=request.POST.get('rubric', ''),
        )
        _save_question_components(question, request)
        messages.success(request, 'تمت إضافة السؤال بنجاح')
        return redirect('exam_edit', pk=exam_pk)

    return render(request, 'exams/question_form.html', {'exam': exam, 'question_types': Question.TYPE_CHOICES})


@require_role('admin')
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk, exam__created_by=request.user)
    exam = question.exam
    if request.method == 'POST':
        question.question_type = request.POST['question_type']
        question.text = request.POST['text']
        question.marks = int(request.POST.get('marks', question.marks))
        question.explanation = request.POST.get('explanation', '')
        question.rubric = request.POST.get('rubric', '')
        question.save()
        
        _save_question_components(question, request)
        messages.success(request, 'تم تحديث السؤال بنجاح')
        return redirect('exam_edit', pk=exam.pk)

    return render(request, 'exams/question_form.html', {
        'exam': exam, 
        'question': question,
        'question_types': Question.TYPE_CHOICES
    })


@require_role('admin')
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    exam_pk = question.exam_id
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'تم حذف السؤال')
    return redirect('exam_edit', pk=exam_pk)


# ─── STUDENT: TAKE EXAM ──────────────────────────────────────────────────────

@login_required
def exam_start(request, pk):
    exam = get_object_or_404(Exam, pk=pk)

    try:
        profile = request.user.profile
        if profile.is_admin():
            messages.warning(request, 'المشرفون لا يمكنهم أداء الاختبارات')
            return redirect('dashboard')
    except Profile.DoesNotExist:
        pass

    if not exam.is_available():
        messages.error(request, 'هذا الاختبار غير متاح حالياً')
        return redirect('dashboard')

    if exam.assigned_students.exists() and request.user not in exam.assigned_students.all():
        messages.error(request, 'غير مصرح لك بدخول هذا الاختبار. الاختبار مخصص لطلاب محددين.')
        return redirect('dashboard')

    # Check attempt limits and overrides
    override = exam.student_overrides.filter(student=request.user).first()
    max_allowed = exam.max_attempts + (override.extra_attempts if override else 0)
    attempts_count = ExamAttempt.objects.filter(exam=exam, student=request.user, is_submitted=True).count()
    
    if attempts_count >= max_allowed:
        messages.info(request, f'لقد استنفدت جميع المحاولات المتاحة لهذا الاختبار ({max_allowed})')
        # Redirect to the latest result
        latest = ExamAttempt.objects.filter(exam=exam, student=request.user, is_submitted=True).first()
        if latest:
            return redirect('exam_result', pk=latest.pk)
        return redirect('dashboard')

    if request.method == 'POST':
        # Create a new attempt
        attempt = ExamAttempt.objects.create(
            exam=exam,
            student=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )

        # Generate random question bank subset
        qs = list(exam.questions.all())
        if exam.random_question_count and exam.random_question_count < len(qs):
            qs = random.sample(qs, exam.random_question_count)
        
        # Pre-create blank AttemptAnswers for the selected questions
        for q in qs:
            AttemptAnswer.objects.create(attempt=attempt, question=q)

        return redirect('exam_take', pk=attempt.pk)

    context = {
        'exam': exam,
        'attempts_used': attempts_count,
        'attempts_remaining': max_allowed - attempts_count,
    }
    return render(request, 'exams/exam_start.html', context)


@login_required
def exam_take(request, pk):
    attempt = get_object_or_404(ExamAttempt, pk=pk, student=request.user)

    if attempt.is_submitted:
        return redirect('exam_result', pk=attempt.pk)

    exam = attempt.exam
    
    # Check assigned questions from Bank
    assigned_q_ids = attempt.answers.values_list('question_id', flat=True)
    if assigned_q_ids:
        questions = list(Question.objects.filter(id__in=assigned_q_ids).prefetch_related('options', 'blanks', 'pairs', 'order_items'))
    else:
        questions = list(exam.questions.prefetch_related('options', 'blanks', 'pairs', 'order_items'))

    if exam.shuffle_questions:
        random.shuffle(questions)

    # Shuffle options for MCQ
    for q in questions:
        if q.question_type in ['mcq_single', 'mcq_multi']:
            q._shuffled_options = list(q.options.all())
            random.shuffle(q._shuffled_options)
        if q.question_type == 'matching':
            q._shuffled_rights = list(q.pairs.all())
            random.shuffle(q._shuffled_rights)
        if q.question_type == 'ordering':
            q._shuffled_items = list(q.order_items.all())
            random.shuffle(q._shuffled_items)

    # Get existing answers
    existing_answers = {a.question_id: a for a in attempt.answers.all()}

    # Time remaining with overrides
    override = exam.student_overrides.filter(student=request.user).first()
    extra_time = override.extra_time_minutes if override else 0
    total_time_seconds = (exam.duration + extra_time) * 60

    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    time_remaining = max(0, int(total_time_seconds - elapsed))

    if time_remaining == 0 and not attempt.is_submitted:
        _submit_attempt(attempt, request.POST)
        return redirect('exam_result', pk=attempt.pk)

    context = {
        'attempt': attempt,
        'exam': exam,
        'questions': questions,
        'existing_answers': existing_answers,
        'time_remaining': time_remaining,
        'total_questions': len(questions),
    }
    return render(request, 'exams/exam_take.html', context)


@login_required
@require_POST
def exam_submit(request, pk):
    attempt = get_object_or_404(ExamAttempt, pk=pk, student=request.user)
    if attempt.is_submitted:
        return redirect('exam_result', pk=attempt.pk)
    _submit_attempt(attempt, request.POST)
    return redirect('exam_result', pk=attempt.pk)


def _submit_attempt(attempt, post_data):
    """Process and save all answers, then auto-grade."""
    exam = attempt.exam
    questions = exam.questions.prefetch_related('options', 'blanks', 'pairs', 'order_items')

    for question in questions:
        answer, _ = AttemptAnswer.objects.get_or_create(attempt=attempt, question=question)
        qtype = question.question_type

        if qtype == 'mcq_single':
            selected = post_data.get(f'q_{question.id}', '')
            answer.selected_options = selected
            answer.answer_text = ''

        elif qtype == 'mcq_multi':
            if hasattr(post_data, 'getlist'):
                selected = post_data.getlist(f'q_{question.id}')
            else:
                val = post_data.get(f'q_{question.id}', [])
                selected = val if isinstance(val, list) else ([val] if val else [])
            answer.selected_options = ','.join(selected)
            answer.answer_text = ''

        elif qtype == 'true_false':
            answer.answer_text = post_data.get(f'q_{question.id}', '')

        elif qtype == 'fill_blank':
            answer.answer_text = post_data.get(f'q_{question.id}', '').strip()

        elif qtype in ['short_answer', 'essay']:
            answer.answer_text = post_data.get(f'q_{question.id}', '').strip()
            answer.is_graded = False

        elif qtype == 'matching':
            pairs = {}
            for pair in question.pairs.all():
                chosen = post_data.get(f'q_{question.id}_left_{pair.id}', '')
                if chosen:
                    pairs[str(pair.id)] = chosen
            answer.matching_answer = json.dumps(pairs)

        elif qtype == 'ordering':
            order_str = post_data.get(f'q_{question.id}_order', '')
            answer.ordering_answer = order_str

        elif qtype == 'code':
            answer.answer_text = post_data.get(f'q_{question.id}', '').strip()
            answer.is_graded = False

        answer.save()

    # Save time spent
    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    attempt.time_spent_seconds = int(elapsed)
    attempt.is_submitted = True
    attempt.submitted_at = timezone.now()
    attempt.save()

    # Auto-grade
    auto_grade_attempt(attempt)


@login_required
@require_POST
def save_answer_ajax(request, attempt_pk):
    """AJAX endpoint to save answer progress"""
    attempt = get_object_or_404(ExamAttempt, pk=attempt_pk, student=request.user)
    if attempt.is_submitted:
        return JsonResponse({'status': 'submitted'})

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        question = get_object_or_404(Question, pk=question_id, exam=attempt.exam)
        answer, _ = AttemptAnswer.objects.get_or_create(attempt=attempt, question=question)

        qtype = question.question_type
        if qtype in ['mcq_single']:
            answer.selected_options = str(data.get('value', ''))
        elif qtype == 'mcq_multi':
            val = data.get('value', [])
            answer.selected_options = ','.join(str(v) for v in val)
        elif qtype in ['true_false', 'fill_blank', 'short_answer', 'essay']:
            answer.answer_text = str(data.get('value', ''))
        elif qtype == 'matching':
            answer.matching_answer = json.dumps(data.get('value', {}))
        elif qtype == 'ordering':
            val = data.get('value', [])
            answer.ordering_answer = ','.join(str(v) for v in val)

        answer.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_POST
def log_violation_ajax(request, attempt_pk):
    """AJAX endpoint to log violations"""
    attempt = get_object_or_404(ExamAttempt, pk=attempt_pk, student=request.user)
    if attempt.is_submitted:
        return JsonResponse({'status': 'submitted'})

    try:
        data = json.loads(request.body)
        ViolationLog.objects.create(
            attempt=attempt,
            violation_type=data.get('type', 'tab_switch'),
            details=data.get('details', '')[:255],
        )
        attempt.violations_count += 1
        attempt.save(update_fields=['violations_count'])
        return JsonResponse({'status': 'ok', 'total': attempt.violations_count})
    except Exception as e:
        return JsonResponse({'status': 'error'})


# ─── RESULTS ──────────────────────────────────────────────────────────────────

@login_required
def exam_result(request, pk):
    attempt = get_object_or_404(ExamAttempt, pk=pk)
    # Access control
    try:
        profile = request.user.profile
        if profile.is_student() and attempt.student != request.user:
            return HttpResponseForbidden()
    except Profile.DoesNotExist:
        pass

    answers = attempt.answers.select_related('question').prefetch_related(
        'question__options', 'question__blanks', 'question__pairs', 'question__order_items'
    )

    context = {
        'attempt': attempt,
        'exam': attempt.exam,
        'answers': answers,
        'percentage': attempt.get_percentage(),
        'passed': attempt.get_percentage() >= attempt.exam.pass_mark / attempt.exam.total_marks * 100 if attempt.exam.total_marks else False,
    }
    return render(request, 'exams/exam_result.html', context)


@login_required
def results_list(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return HttpResponseForbidden()

    exam_id = request.GET.get('exam')
    status_filter = request.GET.get('status', 'all')

    if profile.is_admin() or profile.is_assistant():
        if profile.is_admin() or request.user.is_superuser:
            attempts = ExamAttempt.objects.filter(
                exam__created_by=request.user, is_submitted=True
            ).select_related('student', 'exam').order_by('-submitted_at')
            exams = Exam.objects.filter(created_by=request.user)
        else:
            # Assistant sees all attempts for grading
            attempts = ExamAttempt.objects.filter(is_submitted=True).select_related('student', 'exam').order_by('-submitted_at')
            exams = Exam.objects.all()
    else:
        attempts = ExamAttempt.objects.filter(
            student=request.user, is_submitted=True
        ).select_related('exam').order_by('-submitted_at')
        exams = Exam.objects.filter(attempts__student=request.user).distinct()

    if exam_id:
        attempts = attempts.filter(exam_id=exam_id)
    if status_filter == 'pending':
        attempts = attempts.filter(is_fully_graded=False)
    elif status_filter == 'graded':
        attempts = attempts.filter(is_fully_graded=True)

    context = {
        'attempts': attempts,
        'exams': exams,
        'selected_exam': exam_id,
        'status_filter': status_filter,
        'profile': profile,
    }
    return render(request, 'exams/results_list.html', context)


@require_role(['admin', 'assistant'])
def grade_attempt(request, pk):
    profile = request.user.profile
    if profile.is_admin() or request.user.is_superuser:
        attempt = get_object_or_404(ExamAttempt, pk=pk, exam__created_by=request.user)
    else:
        # Assistant can grade any attempt
        attempt = get_object_or_404(ExamAttempt, pk=pk)
    answers = attempt.answers.select_related('question').prefetch_related(
        'question__options', 'question__blanks', 'question__pairs', 'question__order_items'
    ).order_by('question__order')

    if request.method == 'POST':
        for answer in answers:
            key_marks = f'marks_{answer.id}'
            key_comment = f'comment_{answer.id}'
            if key_marks in request.POST:
                try:
                    earned = float(request.POST[key_marks])
                    earned = max(0.0, min(earned, float(answer.question.marks)))
                    answer.earned_marks = earned
                    answer.grader_comment = request.POST.get(key_comment, '').strip()
                    answer.is_graded = True
                    answer.graded_at = timezone.now()
                    answer.graded_by = request.user
                    answer.save()
                except (ValueError, TypeError):
                    pass

        attempt.grader_notes = request.POST.get('grader_notes', '').strip()

        # Recalculate score
        total = sum(a.earned_marks for a in attempt.answers.filter(is_graded=True) if a.earned_marks is not None)
        attempt.final_score = total
        attempt.grade = attempt.calculate_grade()
        attempt.is_fully_graded = not attempt.answers.filter(is_graded=False).exists()
        attempt.save()

        messages.success(request, f'تم حفظ التصحيح. الدرجة النهائية: {total}/{attempt.exam.total_marks}')
        # Notify student that grading is done
        if attempt.is_fully_graded:
            create_notification(
                user=attempt.student,
                notification_type='grading_done',
                title=f'تم تصحيح: {attempt.exam.title}',
                message=f'درجتك النهائية: {total}/{attempt.exam.total_marks}',
                link=f'/attempts/{attempt.pk}/result/',
            )
        return redirect('results_list')

    context = {
        'attempt': attempt,
        'exam': attempt.exam,
        'answers': answers,
    }
    return render(request, 'exams/grade_attempt.html', context)


# ─── MONITORING ───────────────────────────────────────────────────────────────

@require_role(['admin', 'assistant'])
def monitoring(request):
    profile = request.user.profile
    if profile.is_admin() or request.user.is_superuser:
        active_attempts = ExamAttempt.objects.filter(
            exam__created_by=request.user,
            is_submitted=False,
        ).select_related('student', 'exam').order_by('-started_at')
    else:
        # Assistant sees all ongoing attempts
        active_attempts = ExamAttempt.objects.filter(
            is_submitted=False,
        ).select_related('student', 'exam').order_by('-started_at')

    # Annotate with time remaining
    for a in active_attempts:
        elapsed = (timezone.now() - a.started_at).total_seconds()
        a.time_remaining = max(0, int(a.exam.duration * 60 - elapsed))
        a.progress = min(100, int((a.answers.count() / max(1, a.exam.questions.count())) * 100))

    context = {
        'active_attempts': active_attempts,
        'exams': Exam.objects.filter(created_by=request.user, status='active') if profile.is_admin() else Exam.objects.filter(status='active'),
    }
    return render(request, 'exams/monitoring.html', context)


@require_role(['admin', 'assistant'])
def force_submit(request, attempt_pk):
    """Admin can force-submit an ongoing exam"""
    if request.method == 'POST':
        profile = request.user.profile
        if profile.is_admin() or request.user.is_superuser:
            attempt = get_object_or_404(ExamAttempt, pk=attempt_pk, exam__created_by=request.user)
        else:
            attempt = get_object_or_404(ExamAttempt, pk=attempt_pk)
        if not attempt.is_submitted:
            _submit_attempt(attempt, {})
            messages.warning(request, f'تم إنهاء جلسة {attempt.student.get_full_name()} قسراً')
    return redirect('monitoring')


# ─── API: Monitoring refresh ──────────────────────────────────────────────────

@require_role(['admin', 'assistant'])
def monitoring_data_api(request):
    """Returns JSON data for live monitoring refresh"""
    profile = request.user.profile
    if profile.is_admin() or request.user.is_superuser:
        active = ExamAttempt.objects.filter(
            exam__created_by=request.user, is_submitted=False
        ).select_related('student', 'exam')
    else:
        active = ExamAttempt.objects.filter(is_submitted=False).select_related('student', 'exam')

    data = []
    for a in active:
        elapsed = (timezone.now() - a.started_at).total_seconds()
        time_rem = max(0, int(a.exam.duration * 60 - elapsed))
        data.append({
            'id': a.id,
            'student': a.student.get_full_name(),
            'exam': a.exam.title,
            'time_remaining': time_rem,
            'violations': a.violations_count,
            'progress': min(100, int((a.answers.count() / max(1, a.exam.questions.count())) * 100)),
        })
    return JsonResponse({'attempts': data})


# ─── STUDENTS LIST ────────────────────────────────────────────────────────────

@require_role(['admin', 'assistant'])
def students_list(request):
    students = User.objects.filter(profile__role='student').select_related('profile').order_by('last_name')
    context = {
        'students': students,
        'total': students.count(),
    }
    return render(request, 'exams/students_list.html', context)


# ─── EXAM STATISTICS ─────────────────────────────────────────────────────────

@require_role(['admin', 'assistant'])
def exam_statistics(request, pk):
    exam = get_object_or_404(Exam, pk=pk, created_by=request.user)
    attempts = exam.attempts.filter(is_submitted=True).select_related('student')
    total_attempts = attempts.count()

    if total_attempts == 0:
        context = {
            'exam': exam,
            'no_data': True,
        }
        return render(request, 'exams/exam_statistics.html', context)

    scores = [a.get_total_score() for a in attempts]
    percentages = [a.get_percentage() for a in attempts]

    avg_score = round(sum(scores) / len(scores), 1)
    max_score = max(scores)
    min_score = min(scores)
    pass_threshold = (exam.pass_mark / exam.total_marks * 100) if exam.total_marks else 50
    passed_count = sum(1 for p in percentages if p >= pass_threshold)
    failed_count = total_attempts - passed_count

    # Grade distribution
    grade_dist = {}
    for a in attempts:
        g = a.grade or a.calculate_grade()
        grade_dist[g] = grade_dist.get(g, 0) + 1

    # Score distribution for chart (buckets of 10%)
    score_buckets = [0] * 10
    for p in percentages:
        bucket = min(int(p // 10), 9)
        score_buckets[bucket] += 1

    # Question difficulty analysis
    questions = exam.questions.all()
    question_stats = []
    for q in questions:
        q_answers = AttemptAnswer.objects.filter(
            question=q, attempt__is_submitted=True, is_graded=True
        )
        total_q = q_answers.count()
        if total_q > 0:
            correct_q = q_answers.filter(earned_marks=q.marks).count()
            difficulty = round((1 - correct_q / total_q) * 100, 1)
        else:
            correct_q = 0
            difficulty = 0
        question_stats.append({
            'question': q,
            'total': total_q,
            'correct': correct_q,
            'difficulty': difficulty,
        })

    context = {
        'exam': exam,
        'total_attempts': total_attempts,
        'avg_score': avg_score,
        'max_score': max_score,
        'min_score': min_score,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'pass_rate': round(passed_count / total_attempts * 100, 1),
        'grade_dist': json.dumps(grade_dist),
        'grade_labels': json.dumps(list(grade_dist.keys())),
        'grade_values': json.dumps(list(grade_dist.values())),
        'score_buckets': json.dumps(score_buckets),
        'question_stats': question_stats,
        'no_data': False,
    }
    return render(request, 'exams/exam_statistics.html', context)


# ─── EXAM DUPLICATE ──────────────────────────────────────────────────────────

@require_role('admin')
def exam_duplicate(request, pk):
    original = get_object_or_404(Exam, pk=pk, created_by=request.user)
    if request.method == 'POST':
        new_exam = Exam.objects.create(
            title=f"{original.title} (نسخة)",
            subject=original.subject,
            description=original.description,
            duration=original.duration,
            total_marks=original.total_marks,
            pass_mark=original.pass_mark,
            max_attempts=original.max_attempts,
            shuffle_questions=original.shuffle_questions,
            allow_review=original.allow_review,
            status='draft',
            created_by=request.user,
        )
        # Duplicate questions
        for q in original.questions.all():
            new_q = Question.objects.create(
                exam=new_exam,
                question_type=q.question_type,
                text=q.text,
                marks=q.marks,
                order=q.order,
                explanation=q.explanation,
                tf_answer=q.tf_answer,
                rubric=q.rubric,
            )
            for opt in q.options.all():
                QuestionOption.objects.create(
                    question=new_q, text=opt.text,
                    is_correct=opt.is_correct, order=opt.order,
                )
            for blank in q.blanks.all():
                QuestionBlank.objects.create(
                    question=new_q, accepted_answer=blank.accepted_answer,
                    case_sensitive=blank.case_sensitive,
                )
            for pair in q.pairs.all():
                MatchingPair.objects.create(
                    question=new_q, left_text=pair.left_text,
                    right_text=pair.right_text, order=pair.order,
                )
            for item in q.order_items.all():
                OrderingItem.objects.create(
                    question=new_q, text=item.text,
                    correct_position=item.correct_position,
                )

        messages.success(request, f'تم نسخ الاختبار بنجاح إلى "{new_exam.title}"')
        return redirect('exam_edit', pk=new_exam.pk)
    return redirect('exam_list')


# ─── EXPORT RESULTS TO CSV ─────────────────────────────────────────────────────

@require_role(['admin', 'assistant'])
def export_results(request):
    exam_id = request.GET.get('exam')
    profile = request.user.profile
    if profile.is_admin() or request.user.is_superuser:
        attempts = ExamAttempt.objects.filter(
            exam__created_by=request.user, is_submitted=True
        ).select_related('student', 'exam').order_by('exam__title', '-submitted_at')
    else:
        attempts = ExamAttempt.objects.filter(
            is_submitted=True
        ).select_related('student', 'exam').order_by('exam__title', '-submitted_at')

    if exam_id:
        attempts = attempts.filter(exam_id=exam_id)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="exam_results.csv"'
    response.write('\ufeff')  # BOM for Excel Arabic support

    writer = csv.writer(response)
    writer.writerow(['الاختبار', 'اسم الطالب', 'اسم المستخدم', 'الدرجة', 'الدرجة الكلية', 'النسبة', 'التقدير', 'المخالفات', 'الحالة', 'تاريخ التسليم'])

    for a in attempts:
        writer.writerow([
            a.exam.title,
            a.student.get_full_name(),
            a.student.username,
            a.final_score or 0,
            a.exam.total_marks,
            f"{a.get_percentage()}%",
            a.grade or '-',
            a.violations_count,
            'مصحح' if a.is_fully_graded else 'بانتظار التصحيح',
            a.submitted_at.strftime('%Y-%m-%d %H:%M') if a.submitted_at else '',
        ])

    return response


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

@login_required
def notifications_api(request):
    notifications = Notification.objects.filter(user=request.user)[:20]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'link': n.link,
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            }
            for n in notifications
        ]
    }
    return JsonResponse(data)


@login_required
@require_POST
def mark_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok'})

@login_required
@require_POST
def contact_api_submit(request):
    try:
        import json
        data = json.loads(request.body)
        subject = data.get('subject')
        message = data.get('message')
        
        if not subject or not message:
            return JsonResponse({'status': 'error', 'msg': 'يرجى إكمال جميع الحقول'})
            
        from .models import ContactMessage
        ContactMessage.objects.create(
            user=request.user,
            subject=subject,
            message=message
        )
        return JsonResponse({'status': 'success', 'msg': 'تم استلام رسالتك، سيصلك الرد قريباً عبر الإشعارات.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})


def create_notification(user, notification_type, title, message='', link=''):
    """Helper to create a notification for a user."""
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )
@login_required
def generate_certificate(request, attempt_pk):
    """
    Renders a premium, printable certificate for students who passed.
    """
    attempt = get_object_or_404(ExamAttempt, pk=attempt_pk, student=request.user, is_submitted=True)
    
    # Check if passed and fully graded
    percentage = (attempt.final_score / attempt.exam.total_marks) * 100 if attempt.exam.total_marks > 0 else 0
    passed = percentage >= attempt.exam.pass_mark
    
    if not passed or not attempt.is_fully_graded:
        return HttpResponseForbidden("الشهادة متاحة فقط للاختبارات المجتازة والمصححة بالكامل.")
        
    context = {
        'attempt': attempt,
        'percentage': percentage,
        'passed': passed,
        'now': timezone.now(),
    }
    return render(request, 'exams/certificate.html', context)


@login_required
@require_POST
def send_chat_message(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id)
    profile = getattr(request.user, 'profile', None)
    is_owner = attempt.user == request.user
    is_staff = (profile and profile.role in ['admin', 'assistant']) or request.user.is_superuser
    
    if not (is_owner or is_staff):
        return HttpResponseForbidden("غير مسموح لك بإرسال رسائل هنا.")
        
    try:
        data = json.loads(request.body)
        msg_text = data.get('message', '').strip()
    except:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    if msg_text:
        msg = ChatMessage.objects.create(
            attempt=attempt,
            sender=request.user,
            message=msg_text
        )
        return JsonResponse({
            'status': 'ok',
            'id': msg.id,
            'sender': 'أنت' if msg.sender == request.user else msg.sender.username,
            'timestamp': msg.timestamp.strftime('%H:%M')
        })
    return JsonResponse({'status': 'error', 'message': 'رسالة فارغة'}, status=400)


@login_required
def get_chat_messages(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id)
    profile = getattr(request.user, 'profile', None)
    is_owner = attempt.user == request.user
    is_staff = (profile and profile.role in ['admin', 'assistant']) or request.user.is_superuser
    
    if not (is_owner or is_staff):
        return HttpResponseForbidden()
        
    messages = ChatMessage.objects.filter(attempt=attempt).order_by('timestamp')
    return JsonResponse({
        'messages': [
            {
                'id': m.id,
                'sender': 'أنت' if m.sender == request.user else m.sender.username,
                'is_me': m.sender == request.user,
                'message': m.message,
                'timestamp': m.timestamp.strftime('%H:%M')
            }
            for m in messages
        ]
    })

def about_system(request):
    """Renders the About page with FAQ and contact info."""
    return render(request, 'exams/about.html')
