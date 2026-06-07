import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_exam.settings')
django.setup()

from exams.models import AttemptAnswer
from exams.security_utils import decrypt_data
from django.conf import settings

print(f"SECRET_KEY starts with: {settings.SECRET_KEY[:5]}...")

ans = AttemptAnswer.objects.exclude(answer_text='').first()
if ans:
    print(f"ID: {ans.id}")
    print(f"Raw text: {ans.answer_text[:20]}...")
    dec = ans.decrypted_text
    print(f"Decrypted property: {dec[:20]}...")
    dec_func = decrypt_data(ans.answer_text)
    print(f"Decrypt function: {dec_func[:20]}...")
    
    if dec == ans.answer_text:
        print("FAILED to decrypt.")
        try:
            import base64
            import hashlib
            from cryptography.fernet import Fernet
            key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key)
            cipher = Fernet(fernet_key)
            test_dec = cipher.decrypt(ans.answer_text.encode()).decode()
            print(f"Manual decrypt: {test_dec}")
        except Exception as e:
            print(f"Manual decrypt error: {e}")
else:
    print("No answers found in DB.")
