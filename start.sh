#!/bin/bash
# =============================================================
#  نظام الاختبارات الجامعي — سكريبت الإعداد والتشغيل
# =============================================================

set -e
cd "$(dirname "$0")"

echo ""
echo "🎓 نظام الاختبارات الجامعي"
echo "=================================="

# Install dependencies
echo "📦 جارٍ تثبيت المكتبات..."
pip install -r requirements.txt -q

# Database migrations
echo "🗄️  جارٍ إنشاء قاعدة البيانات..."
python manage.py makemigrations accounts exams --no-input
python manage.py migrate --no-input

# Seed sample data
echo "🌱 جارٍ إضافة البيانات التجريبية..."
python manage.py seed_data

# Collect static files
echo "📁 جارٍ تجميع الملفات الثابتة..."
python manage.py collectstatic --no-input -v 0

echo ""
echo "✅ اكتمل الإعداد!"
echo "=================================="
echo "  🌐 افتح: http://127.0.0.1:8000"
echo "  👨‍🏫 مشرف: admin / admin123"
echo "  👨‍🎓 طالب: ahmed / 1234"
echo "=================================="
echo ""

# Start server
python manage.py runserver 0.0.0.0:8000
