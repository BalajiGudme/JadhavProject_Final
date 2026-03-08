# # utils/otp_utils.py
# from django.core.cache import cache
# import random
# import string
# from django.core.mail import send_mail
# from django.conf import settings
# from django.contrib.auth import get_user_model

# # Get the custom user model
# User = get_user_model()

# def generate_otp():
#     """Generate 6-digit OTP"""
#     return ''.join(random.choices(string.digits, k=6))

# def store_otp(email, otp):
#     """Store OTP in cache with 1 minute expiry"""
#     cache_key = f"password_reset_otp_{email}"
#     cache.set(cache_key, otp, timeout=60)  # 1 minute
#     return True

# def get_otp(email):
#     """Retrieve OTP from cache"""
#     cache_key = f"password_reset_otp_{email}"
#     return cache.get(cache_key)

# def delete_otp(email):
#     """Delete OTP from cache"""
#     cache_key = f"password_reset_otp_{email}"
#     cache.delete(cache_key)

# def verify_otp(email, otp):
#     """Verify if OTP is valid"""
#     stored_otp = get_otp(email)
#     return stored_otp == otp

# def send_otp_email(user, otp):
#     """Send OTP email to user"""
#     subject = "Password Reset OTP"
#     message = f"""
#     Hello {user.username},
    
#     Your password reset OTP is: {otp}
    
#     This OTP is valid for 1 minute.
    
#     If you didn't request this, please ignore this email.
    
#     Best regards,
#     Your App Team
#     """
    
#     send_mail(
#         subject,
#         message,
#         settings.DEFAULT_FROM_EMAIL,
#         [user.email],
#         fail_silently=False,
#     )

# def resend_otp(email):
#     """Resend OTP - generates new OTP and sends email"""
#     try:
#         user = User.objects.get(email=email)
        
#         # Generate new OTP
#         otp = generate_otp()
        
#         # Store new OTP (overwrites previous one)
#         store_otp(email, otp)
        
#         # Send email with new OTP
#         send_otp_email(user, otp)
        
#         return True, "OTP resent successfully."
        
#     except User.DoesNotExist:
#         # This should not happen since we validate email first
#         return False, "No account found with this email address."

# def can_resend_otp(email):
#     """Check if OTP can be resent (prevent spam)"""
#     cache_key = f"otp_resend_count_{email}"
#     resend_count = cache.get(cache_key, 0)
    
#     # Allow maximum 3 resends in 10 minutes
#     if resend_count >= 3:
#         return False, "Too many resend attempts. Please try again later."
    
#     return True, "Can resend OTP"




# # utils.py (enhance your existing utils for registration)

# def store_registration_otp(email, otp):
#     """Store registration OTP with metadata"""
#     cache_key = f"reg_otp_{email}"
#     cache.set(cache_key, {
#         'otp': otp,
#         'attempts': 0,
#         'created_at': timezone.now().isoformat()
#     }, timeout=60)  # 1 minute
#     return True

# def get_registration_otp_data(email):
#     """Get registration OTP data"""
#     cache_key = f"reg_otp_{email}"
#     return cache.get(cache_key)

# def verify_registration_otp(email, otp):
#     """Verify registration OTP with attempt tracking"""
#     cache_key = f"reg_otp_{email}"
#     otp_data = cache.get(cache_key)
    
#     if not otp_data:
#         return False, "OTP expired"
    
#     if otp_data['attempts'] >= 3:
#         cache.delete(cache_key)
#         return False, "Maximum attempts exceeded"
    
#     if otp_data['otp'] != otp:
#         otp_data['attempts'] += 1
#         cache.set(cache_key, otp_data, timeout=60)
#         return False, "Invalid OTP"
    
#     # OTP is valid, delete it
#     cache.delete(cache_key)
#     return True, "OTP verified"


# # utils.py (add this function)

# def send_registration_otp_email(user, otp):
#     """Send registration OTP email to user (user can be a temp object with email and username)"""
#     subject = "Your Registration OTP"
#     message = f"""
#     Hello {user.username},
    
#     Thank you for registering!
    
#     Your registration OTP is: {otp}
    
#     This OTP is valid for 1 minute.
    
#     If you didn't request this, please ignore this email.
    
#     Best regards,
#     Your App Team
#     """
    
#     send_mail(
#         subject,
#         message,
#         settings.DEFAULT_FROM_EMAIL,
#         [user.email],
#         fail_silently=False,
#     )



# utils/otp_utils.py
from django.core.cache import cache
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone  # Add this import
import logging

logger = logging.getLogger(__name__)

# Get the custom user model
User = get_user_model()

def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def store_otp(email, otp):
    """Store OTP in cache with 1 minute expiry"""
    cache_key = f"password_reset_otp_{email}"
    cache.set(cache_key, otp, timeout=60)  # 1 minute
    return True

def get_otp(email):
    """Retrieve OTP from cache"""
    cache_key = f"password_reset_otp_{email}"
    return cache.get(cache_key)

def delete_otp(email):
    """Delete OTP from cache"""
    cache_key = f"password_reset_otp_{email}"
    cache.delete(cache_key)

def verify_otp(email, otp):
    """Verify if OTP is valid"""
    stored_otp = get_otp(email)
    return stored_otp == otp

def send_otp_email(user, otp):
    """Send OTP email to user"""
    subject = "Password Reset OTP"
    message = f"""
    Hello {user.username},
    
    Your password reset OTP is: {otp}
    
    This OTP is valid for 1 minute.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    Your App Team
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def resend_otp(email):
    """Resend OTP - generates new OTP and sends email"""
    try:
        user = User.objects.get(email=email)
        
        # Generate new OTP
        otp = generate_otp()
        
        # Store new OTP (overwrites previous one)
        store_otp(email, otp)
        
        # Send email with new OTP
        send_otp_email(user, otp)
        
        return True, "OTP resent successfully."
        
    except User.DoesNotExist:
        # This should not happen since we validate email first
        return False, "No account found with this email address."

def can_resend_otp(email):
    """Check if OTP can be resent (prevent spam)"""
    cache_key = f"otp_resend_count_{email}"
    resend_count = cache.get(cache_key, 0)
    
    # Allow maximum 3 resends in 10 minutes
    if resend_count >= 3:
        return False, "Too many resend attempts. Please try again later."
    
    return True, "Can resend OTP"

# Registration OTP functions
def store_registration_otp(email, otp):
    """Store registration OTP with metadata"""
    cache_key = f"reg_otp_{email}"
    cache.set(cache_key, {
        'otp': otp,
        'attempts': 0,
        'created_at': timezone.now().isoformat()
    }, timeout=60)  # 1 minute
    return True

def get_registration_otp_data(email):
    """Get registration OTP data"""
    cache_key = f"reg_otp_{email}"
    return cache.get(cache_key)

def verify_registration_otp(email, otp):
    """Verify registration OTP with attempt tracking"""
    cache_key = f"reg_otp_{email}"
    otp_data = cache.get(cache_key)
    
    if not otp_data:
        return False, "OTP expired"
    
    if otp_data['attempts'] >= 3:
        cache.delete(cache_key)
        return False, "Maximum attempts exceeded"
    
    if otp_data['otp'] != otp:
        otp_data['attempts'] += 1
        cache.set(cache_key, otp_data, timeout=60)
        return False, "Invalid OTP"
    
    # OTP is valid, delete it
    cache.delete(cache_key)
    return True, "OTP verified"

# Fix this function - it should accept email and username separately, not a user object
def send_registration_otp_email(email, username, otp):
    """Send registration OTP email"""
    try:
        subject = "Your Registration OTP"
        message = f"""
        Hello {username},
        
        Thank you for registering!
        
        Your registration OTP is: {otp}
        
        This OTP is valid for 1 minute.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        Your App Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        logger.info(f"Registration OTP email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send registration OTP email to {email}: {str(e)}")
        raise

# Add this function to store registration data
def store_registration_data(email, data, timeout=600):
    """Store registration data in cache"""
    cache_key = f"registration_data_{email}"
    cache.set(cache_key, data, timeout=timeout)
    return True

def get_registration_data(email):
    """Get registration data from cache"""
    cache_key = f"registration_data_{email}"
    return cache.get(cache_key)

def delete_registration_data(email):
    """Delete registration data from cache"""
    cache_key = f"registration_data_{email}"
    cache.delete(cache_key)