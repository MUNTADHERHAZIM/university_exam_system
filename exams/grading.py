"""
Auto-grading engine for the University Exam System.
Handles all auto-gradeable question types.
"""
import json
from django.utils import timezone
from .models import AttemptAnswer, ExamAttempt, Question, QuestionOption


def auto_grade_answer(answer: AttemptAnswer) -> float:
    """
    Auto-grade a single answer. Returns earned marks.
    Returns None for manual-graded question types.
    """
    question = answer.question
    qtype = question.question_type

    if qtype == 'mcq_single':
        return _grade_mcq_single(answer, question)
    elif qtype == 'mcq_multi':
        return _grade_mcq_multi(answer, question)
    elif qtype == 'true_false':
        return _grade_true_false(answer, question)
    elif qtype == 'fill_blank':
        return _grade_fill_blank(answer, question)
    elif qtype == 'matching':
        return _grade_matching(answer, question)
    elif qtype == 'ordering':
        return _grade_ordering(answer, question)
    else:
        # short_answer, essay => manual
        return None


def _grade_mcq_single(answer: AttemptAnswer, question: Question) -> float:
    if not answer.selected_options:
        return 0.0
    try:
        selected_id = int(answer.selected_options.strip())
        correct = question.options.filter(is_correct=True, id=selected_id).exists()
        return float(question.marks) if correct else 0.0
    except (ValueError, TypeError):
        return 0.0


def _grade_mcq_multi(answer: AttemptAnswer, question: Question) -> float:
    correct_ids = set(question.options.filter(is_correct=True).values_list('id', flat=True))
    if not answer.selected_options:
        selected_ids = set()
    else:
        try:
            selected_ids = set(int(x) for x in answer.selected_options.split(',') if x.strip())
        except ValueError:
            return 0.0

    if not correct_ids:
        return 0.0

    # Full marks only if exactly right
    if selected_ids == correct_ids:
        return float(question.marks)

    # Partial grading: give credit per correct selected, penalize wrong selections
    correct_selected = len(selected_ids & correct_ids)
    wrong_selected = len(selected_ids - correct_ids)
    if wrong_selected > 0:
        return 0.0
    # Partial marks
    partial = (correct_selected / len(correct_ids)) * question.marks
    return round(partial, 2)


def _grade_true_false(answer: AttemptAnswer, question: Question) -> float:
    if not answer.answer_text:
        return 0.0
    student_answer = answer.answer_text.strip().lower()
    correct_answer = str(question.tf_answer).lower()  # 'true' or 'false'
    # Accept arabic too
    if student_answer in ['true', 'صحيح', 'صح', '1']:
        student_bool = True
    elif student_answer in ['false', 'خطأ', 'خطا', '0']:
        student_bool = False
    else:
        return 0.0
    return float(question.marks) if (student_bool == question.tf_answer) else 0.0


def _grade_fill_blank(answer: AttemptAnswer, question: Question) -> float:
    student_text = answer.answer_text.strip()
    if not student_text:
        return 0.0
    blanks = question.blanks.all()
    if not blanks.exists():
        return 0.0
    for blank in blanks:
        expected = blank.accepted_answer.strip()
        if blank.case_sensitive:
            if student_text == expected:
                return float(question.marks)
        else:
            if student_text.lower() == expected.lower():
                return float(question.marks)
    return 0.0


def _grade_matching(answer: AttemptAnswer, question: Question) -> float:
    if not answer.matching_answer:
        return 0.0
    try:
        student_pairs = json.loads(answer.matching_answer)
    except (json.JSONDecodeError, TypeError):
        return 0.0

    pairs = question.pairs.all()
    if not pairs.exists():
        return 0.0

    correct_count = 0
    for pair in pairs:
        left_key = str(pair.id)
        student_right = student_pairs.get(left_key)
        if student_right and str(student_right) == str(pair.id):
            correct_count += 1

    # Actually matching pairs: left_id -> right_id where right_id maps to same pair
    # Re-implement: student_pairs = {left_pair_id: right_pair_id (which pair's right they chose)}
    correct_count = 0
    for pair in pairs:
        left_key = str(pair.id)
        chosen_right_id = student_pairs.get(left_key)
        if chosen_right_id is not None:
            # The correct answer: same pair id
            if str(chosen_right_id) == str(pair.id):
                correct_count += 1

    total = pairs.count()
    if total == 0:
        return 0.0
    return round((correct_count / total) * question.marks, 2)


def _grade_ordering(answer: AttemptAnswer, question: Question) -> float:
    if not answer.ordering_answer:
        return 0.0
    try:
        student_order = [int(x) for x in answer.ordering_answer.split(',') if x.strip()]
    except ValueError:
        return 0.0

    correct_order = list(question.order_items.order_by('correct_position').values_list('id', flat=True))
    if student_order == correct_order:
        return float(question.marks)

    # Partial: count items in correct relative position
    correct_count = sum(1 for i, item_id in enumerate(student_order) if i < len(correct_order) and item_id == correct_order[i])
    total = len(correct_order)
    if total == 0:
        return 0.0
    return round((correct_count / total) * question.marks, 2)


def auto_grade_attempt(attempt: ExamAttempt):
    """Auto-grade all auto-gradeable answers in an attempt."""
    for answer in attempt.answers.all():
        if answer.is_graded:
            continue
        earned = auto_grade_answer(answer)
        if earned is not None:
            answer.earned_marks = earned
            answer.is_graded = True
            answer.graded_at = timezone.now()
            answer.save(update_fields=['earned_marks', 'is_graded', 'graded_at'])

    # Update attempt score
    total = sum(a.earned_marks for a in attempt.answers.filter(is_graded=True) if a.earned_marks is not None)
    attempt.final_score = total
    attempt.grade = attempt.calculate_grade()

    # Check if fully graded
    ungraded = attempt.answers.filter(is_graded=False).count()
    attempt.is_fully_graded = (ungraded == 0)
    attempt.save(update_fields=['final_score', 'grade', 'is_fully_graded'])

    return attempt
