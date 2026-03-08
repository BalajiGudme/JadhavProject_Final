

#above code is per fect for 3/10/2025===================================================================================================================================================================================
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinLengthValidator, EmailValidator, RegexValidator
from django.utils import timezone
from django.conf import settings
import random
import string

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    ]
    
    username = models.CharField(
        max_length=50,
        unique=True,
        validators=[MinLengthValidator(3, "Username must be at least 3 characters long.")]
    )
    
    full_name = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(3, "Full name must be at least 3 characters long.")]
    )

    email = models.EmailField(
        unique=True,
        validators=[EmailValidator(message="Enter a valid email address.")]
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?\d{10,15}$',
                message="Enter a valid phone number (10–15 digits, may start with +)."
            )
        ]
    )
    
    college_company = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        validators=[MinLengthValidator(2, "College/Company name must be at least 2 characters long.")]
    )

    address = models.TextField(blank=True, null=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )

    is_active = models.BooleanField(default=True)  
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    is_approved = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "full_name"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.full_name} ({self.email}) - {self.role}"
    
    def save(self, *args, **kwargs):
        if not self.full_name and (self.first_name or self.last_name):
            self.full_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)


class Architecture(models.Model):
    # Status choices
    STATUS_PENDING = 0
    STATUS_ACCEPTED = 1
    STATUS_REJECTED = 2
    STATUS_COMPLETED = 3
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_COMPLETED, 'Completed'),
    ]
    
    name = models.CharField(max_length=200, help_text="Name of the college, company, or institution")
    institution_type = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Type of institution (e.g., College, Company, School, etc.)"
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        help_text="Parent institution if this is a subunit"
    )
    department_name = models.CharField(max_length=200, blank=True, null=True, help_text="Department name (if applicable)")
    class_name = models.CharField(max_length=100, blank=True, null=True, help_text="Class name (if applicable)")
    division = models.CharField(max_length=100, blank=True, null=True, help_text="Division name (if applicable)")
    student_count = models.PositiveIntegerField(default=0, help_text="Number of students in this unit")
    staff_count = models.PositiveIntegerField(default=0, help_text="Number of staff members in this unit")
    
    # New status field
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Status of the record: 0=Pending, 1=Accepted, 2=Rejected, 3=Completed"
    )
    
    is_active = models.BooleanField(default=True)
    custm_sent_to_admin = models.BooleanField(
        default=False,
        help_text="Whether this record has been sent to admin"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Using settings reference
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='created_architectures'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name', 'department_name', 'class_name', 'division']
        verbose_name_plural = "Architectures"
    
    def __str__(self):
        parts = []
        if self.institution_type:
            parts.append(f"{self.institution_type}")
        if self.name:
            parts.append(f"{self.name}")
        if self.department_name:
            parts.append(f"{self.department_name}")
        if self.class_name:
            parts.append(f"{self.class_name}")
        if self.division:
            parts.append(f"{self.division}")
        
        return " - ".join(parts)
    
    def mark_as_sent_to_admin(self):
        """Method to mark this record as sent to admin"""
        self.custm_sent_to_admin = True
        self.save()
    
    def mark_as_not_sent_to_admin(self):
        """Method to mark this record as not sent to admin"""
        self.custm_sent_to_admin = False
        self.save()
    
    def is_sent_to_admin(self):
        """Method to check if record was sent to admin"""
        return self.custm_sent_to_admin
    
    # New methods for status management
    def mark_as_pending(self):
        """Method to mark this record as pending"""
        self.status = self.STATUS_PENDING
        self.save()
    
    def mark_as_accepted(self):
        """Method to mark this record as accepted"""
        self.status = self.STATUS_ACCEPTED
        self.save()
    
    def mark_as_rejected(self):
        """Method to mark this record as rejected"""
        self.status = self.STATUS_REJECTED
        self.save()
    
    def mark_as_completed(self):
        """Method to mark this record as completed"""
        self.status = self.STATUS_COMPLETED
        self.save()
    
    def is_pending(self):
        """Check if record is pending"""
        return self.status == self.STATUS_PENDING
    
    def is_accepted(self):
        """Check if record is accepted"""
        return self.status == self.STATUS_ACCEPTED
    
    def is_rejected(self):
        """Check if record is rejected"""
        return self.status == self.STATUS_REJECTED
    
    def is_completed(self):
        """Check if record is completed"""
        return self.status == self.STATUS_COMPLETED
    
    def get_status_display(self):
        """Get human-readable status"""
        return dict(self.STATUS_CHOICES).get(self.status, 'Unknown')
class Form(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Using settings reference
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='created_forms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    allow_multiple_submissions = models.BooleanField(default=False)
    architecture = models.ForeignKey(
        Architecture,
        on_delete=models.CASCADE,
        related_name='forms',
        null=True,
        blank=True,
        help_text="Associated architecture for this form"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title}"



class FormField(models.Model):
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('dropdown', 'Dropdown'),
        ('checkbox', 'Checkbox'),
        ('image', 'Image'),
        ('alphanumeric', 'Alphanumeric'),
        ('email', 'Email ID'),
        ('phonenumber', 'Phone Number'),
    ]
    
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    options = models.JSONField(blank=True, null=True)
    placeholder = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.label} ({self.field_type})"



class FormToken(models.Model):
    token = models.CharField(max_length=6, unique=True)
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='tokens')
    architecture = models.ForeignKey(Architecture, on_delete=models.CASCADE)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        super().save(*args, **kwargs)
    
    def generate_token(self):
        """Generate a unique 4-digit token"""
        while True:
            token = ''.join(random.choices(string.digits, k=4))
            if not FormToken.objects.filter(token=token).exists():
                return token
    
    def __str__(self):
        return f"{self.token} - {self.form.title}"

class FormSubmission(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='submissions')
    token = models.OneToOneField(
        FormToken, 
        on_delete=models.CASCADE, 
        related_name='submission',
        null=True,
        blank=True
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Using settings reference
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='form_submissions'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Submission for {self.form.title}"
from datetime import datetime

# class FieldResponse(models.Model):
#     submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='responses')
#     field = models.ForeignKey(FormField, on_delete=models.CASCADE)
#     value_text = models.TextField(blank=True, null=True)
#     value_number = models.FloatField(blank=True, null=True)
#     value_date = models.DateField(blank=True, null=True)
#     value_boolean = models.BooleanField(blank=True, null=True)
#     value_image = models.ImageField(upload_to='form_responses/', blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ['field__order', 'created_at']

#     def __str__(self):
#         return f"Response for {self.field.label}"

#      # ✅ ADD THIS
    

#     def get_value(self):
#         """
#         Return the stored value based on field type
#         """
#         if self.value_image:
#             return self.value_image
#         if self.value_text not in [None, ""]:
#             return self.value_text
#         if self.value_number is not None:
#             return self.value_number
#         if self.value_boolean is not None:
#             return self.value_boolean
#         if self.value_date:
#             return self.value_date
#         return None

#     def has_value(self):
#         """
#         Check if this response already has any value
#         """
#         return any([
#             self.value_text not in [None, ""],
#             self.value_number is not None,
#             self.value_boolean is not None,
#             self.value_date is not None,
#             bool(self.value_image)
#         ])
    
#     # ✅ ADD THIS METHOD TO HANDLE SETTING VALUES
#     def set_value(self, value):
#         """
#         Set the appropriate value field based on field type
#         """
#         field_type = self.field.field_type
        
#         # Clear all fields first
#         self.value_text = None
#         self.value_number = None
#         self.value_date = None
#         self.value_boolean = None
#         self.value_image = None
        
#         if value is None or value == '':
#             # Keep all fields as None
#             return
        
#         if field_type == 'text':
#             self.value_text = str(value)
        
#         elif field_type == 'number':
#             try:
#                 self.value_number = float(value)
#             except (ValueError, TypeError):
#                 self.value_number = None
        
#         elif field_type == 'date':
#             try:
#                 if isinstance(value, str):
#                     # Try to parse date string
#                     self.value_date = datetime.strptime(value, '%Y-%m-%d').date()
#                 elif hasattr(value, 'date'):
#                     # It's already a date/datetime object
#                     self.value_date = value.date() if hasattr(value, 'date') else value
#             except (ValueError, TypeError):
#                 self.value_date = None
        
#         elif field_type == 'boolean':
#             if isinstance(value, bool):
#                 self.value_boolean = value
#             elif isinstance(value, str):
#                 self.value_boolean = value.lower() in ['true', '1', 'yes', 'on']
#             elif isinstance(value, (int, float)):
#                 self.value_boolean = bool(value)
#             else:
#                 self.value_boolean = None
        
#         elif field_type == 'image':
#             # Handle file upload
#             if hasattr(value, 'file'):  # It's an InMemoryUploadedFile or TemporaryUploadedFile
#                 # Generate a unique filename
#                 filename = f"{self.submission.id}_{self.field.id}_{value.name}"
#                 self.value_image.save(filename, value, save=False)
#             elif isinstance(value, str) and value.startswith('data:image'):
#                 # Handle base64 image data
#                 import base64
#                 from django.core.files.base import ContentFile
#                 from django.utils.crypto import get_random_string
                
#                 try:
#                     format, imgstr = value.split(';base64,')
#                     ext = format.split('/')[-1]
                    
#                     # Generate random filename
#                     filename = f"{self.submission.id}_{self.field.id}_{get_random_string(8)}.{ext}"
#                     data = ContentFile(base64.b64decode(imgstr), name=filename)
#                     self.value_image.save(filename, data, save=False)
#                 except Exception as e:
#                     logger.error(f"Error decoding base64 image: {e}")
#             elif value:  # Any other non-empty value for image field
#                 self.value_text = str(value)  # Fallback to text if image handling fails
        
#         # For any other field type, default to text
#         else:
#             self.value_text = str(value)
        
#         self.save()
    
#     # ✅ ADD THIS METHOD TO CLEAR VALUES
#     def clear_value(self):
#         """Clear all value fields"""
#         self.value_text = None
#         self.value_number = None
#         self.value_date = None
#         self.value_boolean = None
#         self.value_image = None
#         self.save()
    
#     # ✅ ADD THIS METHOD FOR BULK FIELD TYPE CHECKS
#     def get_field_type_specific_value(self):
#         """Get the field type specific value (not the generic get_value)"""
#         if self.field.field_type == 'image':
#             return self.value_image
#         elif self.field.field_type == 'number':
#             return self.value_number
#         elif self.field.field_type == 'date':
#             return self.value_date
#         elif self.field.field_type == 'boolean':
#             return self.value_boolean
#         else:  # text or default
#             return self.value_text


class FieldResponse(models.Model):
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='responses')
    field = models.ForeignKey(FormField, on_delete=models.CASCADE)
    value_text = models.TextField(blank=True, null=True)
    value_number = models.FloatField(blank=True, null=True)
    value_date = models.DateField(blank=True, null=True)
    value_boolean = models.BooleanField(blank=True, null=True)
    value_image = models.ImageField(upload_to='form_responses/', blank=True, null=True)
    
    # ✅ ADD THESE NEW FIELDS
    value_alphanumeric = models.CharField(max_length=255, blank=True, null=True)
    value_email = models.EmailField(max_length=254, blank=True, null=True)
    value_phonenumber = models.CharField(max_length=20, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['field__order', 'created_at']

    def __str__(self):
        return f"Response for {self.field.label}"

    def get_value(self):
        """
        Return the stored value based on field type
        """
        if self.value_image:
            return self.value_image
        if self.value_alphanumeric not in [None, ""]:
            return self.value_alphanumeric
        if self.value_email not in [None, ""]:
            return self.value_email
        if self.value_phonenumber not in [None, ""]:
            return self.value_phonenumber
        if self.value_text not in [None, ""]:
            return self.value_text
        if self.value_number is not None:
            return self.value_number
        if self.value_boolean is not None:
            return self.value_boolean
        if self.value_date:
            return self.value_date
        return None

    def has_value(self):
        """
        Check if this response already has any value
        """
        return any([
            self.value_text not in [None, ""],
            self.value_number is not None,
            self.value_boolean is not None,
            self.value_date is not None,
            bool(self.value_image),
            self.value_alphanumeric not in [None, ""],
            self.value_email not in [None, ""],
            self.value_phonenumber not in [None, ""]
        ])
    
    def set_value(self, value):
        """
        Set the appropriate value field based on field type
        """
        field_type = self.field.field_type
        
        # Clear all fields first
        self.value_text = None
        self.value_number = None
        self.value_date = None
        self.value_boolean = None
        self.value_image = None
        self.value_alphanumeric = None
        self.value_email = None
        self.value_phonenumber = None
        
        if value is None or value == '':
            # Keep all fields as None
            return
        
        if field_type == 'text':
            self.value_text = str(value)
        
        elif field_type == 'alphanumeric':
            import re
    # This now KEEPS spaces (a-zA-Z0-9 and space)
            alphanumeric_value = re.sub(r'[^a-zA-Z0-9\s]', '', str(value))
    # Optional: Trim multiple spaces to single space
            alphanumeric_value = re.sub(r'\s+', ' ', alphanumeric_value).strip()
            self.value_alphanumeric = alphanumeric_value
        
        elif field_type == 'email':
            # Store email (validation should happen at serializer level)
            self.value_email = str(value).lower().strip()
        
        elif field_type == 'phonenumber':
            # Store phone number (strip spaces and special chars but keep +)
            import re
            # Keep only digits and optional leading +
            phone_value = re.sub(r'[^\d+]', '', str(value))
            # Ensure + is only at the beginning if present
            if phone_value.startswith('+'):
                phone_value = '+' + re.sub(r'\+', '', phone_value[1:])
            else:
                phone_value = re.sub(r'\+', '', phone_value)
            self.value_phonenumber = phone_value
        
        elif field_type == 'number':
            try:
                self.value_number = float(value)
            except (ValueError, TypeError):
                self.value_number = None
        
        elif field_type == 'date':
            try:
                if isinstance(value, str):
                    # Try to parse date string
                    from datetime import datetime
                    self.value_date = datetime.strptime(value, '%Y-%m-%d').date()
                elif hasattr(value, 'date'):
                    # It's already a date/datetime object
                    self.value_date = value.date() if hasattr(value, 'date') else value
            except (ValueError, TypeError):
                self.value_date = None
        
        elif field_type == 'checkbox':
            if isinstance(value, bool):
                self.value_boolean = value
            elif isinstance(value, str):
                self.value_boolean = value.lower() in ['true', '1', 'yes', 'on', 'checked']
            elif isinstance(value, (int, float)):
                self.value_boolean = bool(value)
            else:
                self.value_boolean = None
        
        elif field_type == 'dropdown':
            self.value_text = str(value)
        
        elif field_type == 'image':
            # Handle file upload
            if hasattr(value, 'file'):  # It's an InMemoryUploadedFile or TemporaryUploadedFile
                # Generate a unique filename
                import os
                filename = f"{self.submission.id}_{self.field.id}_{os.path.basename(value.name)}"
                self.value_image.save(filename, value, save=False)
            elif isinstance(value, str) and value.startswith('data:image'):
                # Handle base64 image data
                import base64
                from django.core.files.base import ContentFile
                from django.utils.crypto import get_random_string
                
                try:
                    format, imgstr = value.split(';base64,')
                    ext = format.split('/')[-1]
                    
                    # Generate random filename
                    filename = f"{self.submission.id}_{self.field.id}_{get_random_string(8)}.{ext}"
                    data = ContentFile(base64.b64decode(imgstr), name=filename)
                    self.value_image.save(filename, data, save=False)
                except Exception as e:
                    print(f"Error decoding base64 image: {e}")
            elif value:  # Any other non-empty value for image field
                self.value_text = str(value)  # Fallback to text if image handling fails
        
        # For any other field type, default to text
        else:
            self.value_text = str(value)
        
        self.save()
    
    def clear_value(self):
        """Clear all value fields"""
        self.value_text = None
        self.value_number = None
        self.value_date = None
        self.value_boolean = None
        self.value_image = None
        self.value_alphanumeric = None
        self.value_email = None
        self.value_phonenumber = None
        self.save()
    
    def get_field_type_specific_value(self):
        """
        Get the field type specific value (not the generic get_value)
        Returns the value stored in the field corresponding to the field type
        """
        field_type = self.field.field_type
        
        if field_type == 'image':
            return self.value_image
        elif field_type == 'number':
            return self.value_number
        elif field_type == 'date':
            return self.value_date
        elif field_type == 'checkbox':
            return self.value_boolean
        elif field_type == 'alphanumeric':
            return self.value_alphanumeric
        elif field_type == 'email':
            return self.value_email
        elif field_type == 'phonenumber':
            return self.value_phonenumber
        elif field_type == 'text':
            return self.value_text
        elif field_type == 'dropdown':
            return self.value_text
        else:
            # For any other type, try to return appropriate value
            return self.get_value()
    
    def validate_field_value(self):
        """
        Validate that the value matches the field type requirements
        This can be called before saving
        Returns (is_valid, error_message)
        """
        field_type = self.field.field_type
        value = self.get_field_type_specific_value()
        
        if value is None or value == '':
            return True, None  # Empty is valid (required check should be done separately)
        
        import re
        
        if field_type == 'email':
            # Email validation
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, str(value)):
                return False, "Invalid email format"
        
        elif field_type == 'phonenumber':
            # Phone number validation (basic)
            digits_only = re.sub(r'\D', '', str(value))
            if len(digits_only) < 10 or len(digits_only) > 15:
                return False, "Phone number must have 10-15 digits"
        
        elif field_type == 'alphanumeric':
            # Alphanumeric validation
            if not re.match(r'^[A-Za-z0-9\s]+$', str(value)):
                return False, "Only letters, numbers, and spaces are allowed"
        
        elif field_type == 'number':
            # Number validation
            try:
                float(value)
            except (ValueError, TypeError):
                return False, "Invalid number format"
        
        elif field_type == 'date':
            # Date validation
            if not isinstance(value, (str, datetime.date)):
                return False, "Invalid date format"
        
        elif field_type == 'checkbox':
            # Boolean validation
            if not isinstance(value, bool):
                return False, "Invalid boolean value"
        
        return True, None
    
    def get_value_display(self):
        """
        Get a human-readable display value
        """
        value = self.get_field_type_specific_value()
        
        if value is None:
            return "Not provided"
        
        field_type = self.field.field_type
        
        if field_type == 'checkbox':
            return "Yes" if value else "No"
        elif field_type == 'date':
            if hasattr(value, 'strftime'):
                return value.strftime('%B %d, %Y')
        elif field_type == 'image':
            if value:
                return f"Image uploaded: {value.name}"
            return "No image"
        
        return str(value)


from django.db import models
from django.contrib.auth.models import User

class Statistic(models.Model):
    number = models.CharField(max_length=50)
    label = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.number} {self.label}"


class PortfolioItem(models.Model):
    id = models.AutoField(primary_key=True)
    category = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    client = models.CharField(max_length=200)
    year = models.CharField(max_length=10)
    image = models.ImageField(upload_to='portfolio/')

    def __str__(self):
        return f"{self.title} - {self.client}"


class Service(models.Model):
    icon = models.CharField(max_length=10)
    title = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.title


class Testimonial(models.Model):
    text = models.TextField()
    author = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    avatar = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"Testimonial by {self.author}"


class Client(models.Model):
    name = models.CharField(max_length=200, unique=True)
    
    def __str__(self):
        return self.name


class Slide1(models.Model):
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image1 = models.ImageField(upload_to='slides/slide1/')
    image2 = models.ImageField(upload_to='slides/slide1/')
    image3 = models.ImageField(upload_to='slides/slide1/')
    
    def __str__(self):
        return f"Slide1 #{self.id} by {self.user.username}"


class Slide2(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image1 = models.ImageField(upload_to='slides/slide2/')
    image2 = models.ImageField(upload_to='slides/slide2/')
    image3 = models.ImageField(upload_to='slides/slide2/')
    
    def __str__(self):
        return f"Slide2 #{self.id} by {self.user.username}"




