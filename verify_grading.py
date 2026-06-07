import os
import django
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_exam.settings')
django.setup()

from django.contrib.auth.models import User
from exams.models import Exam, Question, ExamAttempt, AttemptAnswer
from exams.views import _submit_attempt
from exams.grading import auto_grade_attempt

def verify_grading_subset():
    print("--- Verifying Grading Subset Logic ---")
    
    # 1. Setup Student and Exam
    student = User.objects.filter(username='student_test_user').first()
    if not student:
        student = User.objects.create_user(username='student_test_user', password='password123')
    
    exam = Exam.objects.create(
        title="Test Random Grading Logic",
        duration=60,
        random_question_count=2,
        status='active'
    )
    
    # 2. Add 5 Questions (3 Auto-grade, 2 Manual-grade)
    q1 = Question.objects.create(exam=exam, text="Q1 - MCQ", question_type='mcq_single', marks=10)
    q2 = Question.objects.create(exam=exam, text="Q2 - TF", question_type='true_false', marks=10, tf_answer=True)
    q3 = Question.objects.create(exam=exam, text="Q3 - Fill", question_type='fill_blank', marks=10)
    q4 = Question.objects.create(exam=exam, text="Q4 - Essay (Manual)", question_type='essay', marks=10)
    q5 = Question.objects.create(exam=exam, text="Q5 - Short (Manual)", question_type='short_answer', marks=10)
    
    # 3. Create Attempt and assign only the 2 Auto-gradeable questions
    attempt = ExamAttempt.objects.create(exam=exam, student=student)
    AttemptAnswer.objects.create(attempt=attempt, question=q1, selected_options="0") # Assume id 0 for mock
    AttemptAnswer.objects.create(attempt=attempt, question=q2, answer_text="true")
    
    print(f"Attempt created with {attempt.answers.count()} assigned questions.")
    
    # 4. Simulate Submission
    # We pass empty post_data but the questions are in assigned_q_ids
    _submit_attempt(attempt, {})
    
    # 5. Check Results
    attempt.refresh_from_db()
    print(f"Final Score: {attempt.final_score}")
    print(f"Is Fully Graded: {attempt.is_fully_graded}")
    
    # The count of AttemptAnswers should still be 2, not 5.
    final_ans_count = attempt.answers.count()
    print(f"Final Answer Count: {final_ans_count}")
    
    if final_ans_count == 2 and attempt.is_fully_graded == True:
        print("SUCCESS: Grading correctly ignored unassigned questions!")
    else:
        print(f"FAILURE: Expected 2 answers and is_fully_graded=True. Got {final_ans_count} and {attempt.is_fully_graded}")

    # Cleanup
    exam.delete()

if __name__ == "__main__":
    verify_grading_subset()
