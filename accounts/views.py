from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Profile
import random


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        profile.phone = request.POST.get('phone', profile.phone)
        profile.department = request.POST.get('department', profile.department)
        profile.save()
        messages.success(request, 'تم تحديث الملف الشخصي بنجاح')
        return redirect('profile')
    return render(request, 'accounts/profile.html', {'profile': profile})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # Verify Captcha
        captcha_answer = request.session.get('captcha_answer')
        user_captcha = request.POST.get('captcha', '').strip()
        
        try:
            if not captcha_answer or int(user_captcha) != captcha_answer:
                messages.error(request, 'إجابة التحقق (CAPTCHA) غير صحيحة، يرجى المحاولة مرة أخرى.')
                return redirect('register')
        except ValueError:
            messages.error(request, 'يرجى إدخال رقم صحيح في حقل التحقق.')
            return redirect('register')

        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        if password != password_confirm:
            messages.error(request, 'كلمات المرور غير متطابقة.')
            return redirect('register')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, 'اسم المستخدم هذا مسجل مسبقاً.')
            return redirect('register')

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        # Profile is created by signals usually, but we ensure role is student
        profile, created = Profile.objects.get_or_create(user=user)
        profile.role = 'student'
        profile.save()

        # Clear captcha
        if 'captcha_answer' in request.session:
            del request.session['captcha_answer']

        messages.success(request, 'تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول.')
        return redirect('login')

    # Generate new Captcha for GET request
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    op = random.choice(['+', '-', '*'])
    
    if op == '+':
        ans = num1 + num2
        op_str = '+'
    elif op == '-':
        # ensure positive result
        if num1 < num2:
            num1, num2 = num2, num1
        ans = num1 - num2
        op_str = '-'
    else:
        # keep numbers small for multiplication
        num1 = random.randint(1, 5)
        num2 = random.randint(1, 5)
        ans = num1 * num2
        op_str = '×'

    request.session['captcha_answer'] = ans
    captcha_text = f"{num1} {op_str} {num2}"

    return render(request, 'accounts/register.html', {'captcha_text': captcha_text})
