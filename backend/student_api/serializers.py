


#1---------------------=========================================================================================================


from rest_framework import serializers
from .models import Form, FormField, FormSubmission, FieldResponse, Architecture, FormToken
from django.utils import timezone

class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = '__all__'

class FormSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Form
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at', 'updated_at', 'is_published')

class FieldResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldResponse
        fields = '__all__'

class FormSubmissionSerializer(serializers.ModelSerializer):
    responses = FieldResponseSerializer(many=True, read_only=True)
    token_value = serializers.CharField(source='token.token', read_only=True)
    
    class Meta:
        model = FormSubmission
        fields = '__all__'

# For form submission creation
class FormSubmissionCreateSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)
    responses = serializers.ListField(
        child=serializers.DictField()
    )
    
    class Meta:
        model = FormSubmission
        fields = ['form', 'token', 'responses', 'student']
        read_only_fields = ('student',)
    
    def validate(self, data):
        token_value = data.get('token')
        form = data.get('form')
        
        if not token_value:
            raise serializers.ValidationError("Token is required")
        
        try:
            token = FormToken.objects.get(token=token_value, form=form)
            if token.is_used:
                raise serializers.ValidationError("This token has already been used")
        except FormToken.DoesNotExist:
            raise serializers.ValidationError("Invalid token for this form")
        
        data['token_instance'] = token
        return data
    
    def create(self, validated_data):
        responses_data = validated_data.pop('responses')
        token_instance = validated_data.pop('token_instance')
        token_value = validated_data.pop('token', None)
        
        # Create submission with token
        submission = FormSubmission.objects.create(
            **validated_data,
            token=token_instance
        )
        
        # Create field responses
        for response_data in responses_data:
            field_id = response_data.get('field_id')
            value = response_data.get('value')
            
            try:
                field = FormField.objects.get(id=field_id, form=submission.form)
                FieldResponse.objects.create(
                    submission=submission,
                    field=field,
                    **self._get_value_field(field.field_type, value)
                )
            except FormField.DoesNotExist:
                # Skip invalid fields
                continue
        
        return submission
    
    def _get_value_field(self, field_type, value):
        """Map value to the correct field based on field type"""
        field_mapping = {
            'text': {'value_text': value},
            'number': {'value_number': float(value) if value else None},
            'date': {'value_date': value},
            'checkbox': {'value_boolean': bool(value)},
            'image': {'value_image': value},
            'alphanumeric': {'value_alphanumeric': value},
            'dropdown': {'value_text': value},
        }
        return field_mapping.get(field_type, {'value_text': value})

# Form Token Serializers
class FormTokenSerializer(serializers.ModelSerializer):
    form_title = serializers.CharField(source='form.title', read_only=True)
    architecture_name = serializers.CharField(source='architecture.name', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = FormToken
        fields = [
            'id', 'token', 'form', 'form_title', 'architecture', 'architecture_name',
            'is_used', 'used_at', 'created_at', 'is_valid'
        ]
        read_only_fields = ('token', 'created_at', 'is_valid')

class FormTokenCreateSerializer(serializers.Serializer):
    form_id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1, max_value=100)
    architecture_id = serializers.IntegerField()
    
    def validate(self, data):
        form_id = data.get('form_id')
        architecture_id = data.get('architecture_id')
        
        # Check if form exists
        try:
            form = Form.objects.get(id=form_id)
            data['form'] = form
        except Form.DoesNotExist:
            raise serializers.ValidationError("Form does not exist")
        
        # Check if architecture exists
        try:
            architecture = Architecture.objects.get(id=architecture_id)
            data['architecture'] = architecture
        except Architecture.DoesNotExist:
            raise serializers.ValidationError("Architecture does not exist")
        
        return data
    
    def create(self, validated_data):
        form = validated_data['form']
        architecture = validated_data['architecture']
        count = validated_data['count']
        
        # Create tokens
        tokens = []
        for _ in range(count):
            token = FormToken.objects.create(
                form=form,
                architecture=architecture
            )
            tokens.append(token)
        
        return tokens

class TokenValidationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=4)
    # form_id = serializers.IntegerField()
    
    def validate(self, data):
        token_value = data.get('token')
        # form_id = data.get('form_id')
        
        try:
            # token = FormToken.objects.get(token=token_value, form_id=form_id)
            token = FormToken.objects.get(token=token_value)
            if token.is_used:
                raise serializers.ValidationError("Token has already been used")
            data['token_instance'] = token
        except FormToken.DoesNotExist:
            raise serializers.ValidationError("Invalid token")
        
        return data

# Architecture Serializers
class ArchitectureSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_hierarchy = serializers.CharField(read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    total_staff = serializers.IntegerField(read_only=True)
    forms_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Architecture
        fields = [
            'id', 'name', 'institution_type', 'parent', 'parent_name','custm_sent_to_admin',
            'department_name', 'class_name', 'division',
            'student_count', 'staff_count', 'is_active',
            'created_by', 'created_at', 'updated_at','status',
            'children', 'full_hierarchy', 'total_students', 'total_staff', 'forms_count'
        ]
        read_only_fields = ('created_by', 'created_at', 'updated_at')
    
    def get_children(self, obj):
        """Recursively get children with their hierarchies"""
        children = obj.children.all()
        serializer = ArchitectureSerializer(children, many=True, context=self.context)
        return serializer.data
    
    def get_forms_count(self, obj):
        """Get count of forms associated with this architecture"""
        return obj.forms.count()

class ArchitectureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Architecture
        fields = [
            'name', 'institution_type', 'parent',
            'department_name', 'class_name', 'division',
            'student_count', 'staff_count', 'is_active'
        ]
    
    def validate(self, data):
        """Custom validation for architecture hierarchy"""
        parent = data.get('parent')
        
        # Prevent circular references
        if parent and parent.id:
            current = parent
            while current:
                if current == self.instance:
                    raise serializers.ValidationError("Cannot create circular reference in hierarchy")
                current = current.parent
        
        return data

class ArchitectureTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Architecture
        fields = ['id', 'name', 'institution_type', 'department_name', 
                 'class_name', 'division', 'student_count', 'staff_count', 'children']
    
    def get_children(self, obj):
        """Recursively get children for tree structure"""
        children = obj.children.all()
        serializer = ArchitectureTreeSerializer(children, many=True, context=self.context)
        return serializer.data

class ArchitectureStatisticsSerializer(serializers.ModelSerializer):
    total_students = serializers.IntegerField(read_only=True)
    total_staff = serializers.IntegerField(read_only=True)
    children_count = serializers.IntegerField(read_only=True)
    forms_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Architecture
        fields = [
            'id', 'name', 'student_count', 'staff_count',
            'total_students', 'total_staff', 'children_count', 'forms_count'
        ]

# For QR Code Generation
class QRCodeGenerationSerializer(serializers.Serializer):
    form_id = serializers.IntegerField()
    architecture_id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1, max_value=100)
    
    def validate(self, data):
        form_id = data.get('form_id')
        architecture_id = data.get('architecture_id')
        
        # Validate form exists
        try:
            Form.objects.get(id=form_id)
        except Form.DoesNotExist:
            raise serializers.ValidationError("Form does not exist")
        
        # Validate architecture exists
        try:
            Architecture.objects.get(id=architecture_id)
        except Architecture.DoesNotExist:
            raise serializers.ValidationError("Architecture does not exist")
        
        return data


class FormSubmissionCreateSerializer(serializers.Serializer):
    token = serializers.CharField()
    responses = serializers.ListField(child=serializers.DictField())
    
    def create(self, validated_data):
        token = validated_data['token']
        responses = validated_data['responses']
        
        # Get the token object
        form_token = FormToken.objects.get(token=token, is_used=False)
        
        # Create submission
        submission = FormSubmission.objects.create(
            form=form_token.form,
            token=form_token,
            submitted_by=self.context['request'].user if self.context['request'].user.is_authenticated else None
        )
        
        # Create responses
        for response_data in responses:
            field_id = response_data.get('field_id')
            value = response_data.get('value')
            
            if field_id and value is not None:
                try:
                    field = FormField.objects.get(id=field_id)
                    FieldResponse.objects.create(
                        submission=submission,
                        field=field,
                        value=value
                    )
                except FormField.DoesNotExist:
                    continue
        
        # Mark token as used
        form_token.is_used = True
        form_token.save()
        
        return submission

# Then use it in your view:
# class SubmitFormByTokenView(APIView):
#     permission_classes = [AllowAny]
    
#     def post(self, request, *args, **kwargs):
#         serializer = FormSubmissionCreateSerializer(
#             data=request.data,
#             context={'request': request}
#         )
        
#         if serializer.is_valid():
#             submission = serializer.save()
#             return Response({
#                 'success': True,
#                 'submission_id': submission.id
#             }, status=status.HTTP_201_CREATED)
#         else:
#             return Response(
#                 {'error': 'Invalid data', 'details': serializer.errors},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#------------------------------------22-09-2025---------------------------
# from rest_framework import serializers
# from .models import FieldResponse, FormField, FormSubmission, FormToken
# from django.core.files.base import ContentFile
# import base64

# class ArchitectureFieldResponseSerializer(serializers.ModelSerializer):
#     field_label = serializers.CharField(source='field.label', read_only=True)
#     field_type = serializers.CharField(source='field.field_type', read_only=True)
#     field_order = serializers.IntegerField(source='field.order', read_only=True)
#     field_required = serializers.BooleanField(source='field.is_required', read_only=True)
#     value = serializers.SerializerMethodField()
#     submission_id = serializers.IntegerField(source='submission.id', read_only=True)
#     architecture_id = serializers.IntegerField(source='submission.token.architecture.id', read_only=True)
#     architecture_name = serializers.CharField(source='submission.token.architecture.name', read_only=True)
#     token = serializers.CharField(source='submission.token.token', read_only=True)

#     class Meta:
#         model = FieldResponse
#         fields = [
#             'id', 'submission_id', 'architecture_id', 'architecture_name', 'token',
#             'field', 'field_label', 'field_type', 'field_order', 'field_required', 
#             'value', 'created_at'
#         ]

#     def get_value(self, obj):
#         """Safely get the value, handling binary data properly"""
#         try:
#             value = obj.get_value()
            
#             # Handle image fields specially
#             if obj.field.field_type == 'image' and value:
#                 # For images, return the URL instead of binary data
#                 request = self.context.get('request')
#                 if request and hasattr(value, 'url'):
#                     return request.build_absolute_uri(value.url)
#                 return str(value.url) if hasattr(value, 'url') else None
            
#             # Handle other binary or complex data types
#             if isinstance(value, (bytes, bytearray, ContentFile)):
#                 # Convert binary data to base64 string for safe serialization
#                 try:
#                     if hasattr(value, 'read'):
#                         # It's a file-like object
#                         value.seek(0)
#                         binary_data = value.read()
#                         return base64.b64encode(binary_data).decode('utf-8')
#                     else:
#                         # It's bytes/bytearray
#                         return base64.b64encode(value).decode('utf-8')
#                 except:
#                     return None
            
#             # Handle date objects
#             if hasattr(value, 'strftime'):
#                 return value.isoformat()
            
#             return value
            
#         except (UnicodeDecodeError, ValueError, AttributeError) as e:
#             # Log the error but don't crash
#             print(f"Error getting value for field {obj.field.label}: {e}")
#             return None

#main---------------------------------------------------------------------------


# import base64
# from rest_framework import serializers
# from django.core.files.base import ContentFile
# from .models import FieldResponse

# class ArchitectureFieldResponseSerializer(serializers.ModelSerializer):
#     field_label = serializers.CharField(source='field.label', read_only=True)
#     field_type = serializers.CharField(source='field.field_type', read_only=True)
#     field_order = serializers.IntegerField(source='field.order', read_only=True)
#     field_required = serializers.BooleanField(source='field.is_required', read_only=True)
#     value = serializers.SerializerMethodField()
#     submission_id = serializers.IntegerField(source='submission.id', read_only=True)
#     architecture_id = serializers.IntegerField(source='submission.token.architecture.id', read_only=True)
#     architecture_name = serializers.CharField(source='submission.token.architecture.name', read_only=True)
#     token = serializers.CharField(source='submission.token.token', read_only=True)

#     class Meta:
#         model = FieldResponse
#         fields = [
#             'id', 'submission_id', 'architecture_id', 'architecture_name', 'token',
#             'field', 'field_label', 'field_type', 'field_order', 'field_required', 
#             'value', 'created_at'
#         ]

#     def get_value(self, obj):
#         """Safely get the value, handling binary data properly"""
#         try:
#             value = obj.get_value()
            
#             # Handle None values
#             if value is None:
#                 return None
            
#             # Handle image fields specially
#             if obj.field.field_type == 'image' and value:
#                 # For images, return the URL instead of binary data
#                 request = self.context.get('request')
#                 if request and hasattr(value, 'url'):
#                     return request.build_absolute_uri(value.url)
#                 return str(value.url) if hasattr(value, 'url') else None
            
#             # Handle other binary or complex data types
#             if isinstance(value, (bytes, bytearray, ContentFile)):
#                 # Convert binary data to base64 string for safe serialization
#                 try:
#                     if hasattr(value, 'read'):
#                         # It's a file-like object
#                         value.seek(0)
#                         binary_data = value.read()
#                         return base64.b64encode(binary_data).decode('utf-8')
#                     else:
#                         # It's bytes/bytearray
#                         return base64.b64encode(value).decode('utf-8')
#                 except:
#                     return None
            
#             # Handle date objects
#             if hasattr(value, 'strftime'):
#                 return value.isoformat()
            
#             # Handle boolean values
#             if isinstance(value, bool):
#                 return value
            
#             # Handle numeric values
#             if isinstance(value, (int, float)):
#                 return value
            
#             # Convert everything else to string
#             return str(value)
            
#         except (UnicodeDecodeError, ValueError, AttributeError) as e:
#             # Log the error but don't crash
#             print(f"Error getting value for field {obj.field.label if obj.field else 'unknown'}: {e}")
#             return None

#     def to_representation(self, instance):
#         """
#         Override to handle cases where related objects might be None or instance is a dict
#         """
#         # Handle dictionary instances (for empty responses)
#         if isinstance(instance, dict):
#             return instance
            
#         # Handle cases where related objects might be None
#         data = super().to_representation(instance)
        
#         # Safely handle None values for related fields
#         if not data.get('submission_id'):
#             data['submission_id'] = None
            
#         if not data.get('architecture_id'):
#             data['architecture_id'] = None
            
#         if not data.get('architecture_name'):
#             data['architecture_name'] = None
            
#         if not data.get('token'):
#             data['token'] = None
            
#         # Ensure field information is present even if field relation fails
#         if not data.get('field_label') and hasattr(instance, 'field') and instance.field:
#             data['field_label'] = instance.field.label
            
#         if not data.get('field_type') and hasattr(instance, 'field') and instance.field:
#             data['field_type'] = instance.field.field_type
            
#         if not data.get('field_order') and hasattr(instance, 'field') and instance.field:
#             data['field_order'] = instance.field.order
            
#         if not data.get('field_required') and hasattr(instance, 'field') and instance.field:
#             data['field_required'] = instance.field.is_required
            
#         return data

#---------------------------------------------=================================== 3/10/2025
#sssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssooppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppp

import logging
import base64
from rest_framework import serializers
from django.core.files.base import ContentFile
from .models import FieldResponse

logger = logging.getLogger(__name__)

# class ArchitectureFieldResponseSerializer(serializers.ModelSerializer):
#     field_label = serializers.CharField(source='field.label', read_only=True)
#     field_type = serializers.CharField(source='field.field_type', read_only=True)
#     field_order = serializers.IntegerField(source='field.order', read_only=True)
#     field_required = serializers.BooleanField(source='field.is_required', read_only=True)
#     value = serializers.SerializerMethodField()
#     submission_id = serializers.IntegerField(source='submission.id', read_only=True)
#     architecture_id = serializers.IntegerField(source='submission.token.architecture.id', read_only=True)
#     architecture_name = serializers.CharField(source='submission.token.architecture.name', read_only=True)
#     token = serializers.CharField(source='submission.token.token', read_only=True)

#     class Meta:
#         model = FieldResponse
#         fields = [
#             'id', 'submission_id', 'architecture_id', 'architecture_name', 'token',
#             'field', 'field_label', 'field_type', 'field_order', 'field_required', 
#             'value', 'created_at',
#         ]

#     def get_value(self, obj):
#         """Safely get the value, handling binary data properly"""
#         try:
#             # First, try to get the raw value from the appropriate field
#             field_type = obj.field.field_type if obj.field else 'text'
            
#             # Get value from the correct field based on field type
#             if field_type == 'number':
#                 raw_value = obj.value_number
#             elif field_type == 'date':
#                 raw_value = obj.value_date
#             elif field_type == 'checkbox':
#                 raw_value = obj.value_boolean
#             elif field_type == 'image':
#                 raw_value = obj.value_image
#             elif field_type == 'alphanumeric':
#                 raw_value = obj.value_alphanumeric
#             else:  # text, dropdown, etc.
#                 raw_value = obj.value_text
            
#             # Handle None values
#             if raw_value is None:
#                 return None
            
#             # Handle image fields specially - return URL instead of file data
#             if field_type == 'image' and raw_value:
#                 if hasattr(raw_value, 'url'):
#                     # It's an ImageField - return URL
#                     request = self.context.get('request')
#                     if request:
#                         return request.build_absolute_uri(raw_value.url)
#                     return raw_value.url
#                 elif hasattr(raw_value, 'name'):
#                     # It has a filename but no URL method
#                     return str(raw_value.name)
#                 else:
#                     # Return string representation
#                     return str(raw_value)
            
#             # Handle binary data safely - don't try to decode it
#             if isinstance(raw_value, (bytes, bytearray)):
#                 try:
#                     # For binary data that's not images, encode as base64
#                     if raw_value:
#                         return base64.b64encode(raw_value).decode('ascii')
#                     return None
#                 except Exception as e:
#                     logger.warning(f"Error encoding binary data for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                     return "[Binary data]"
            
#             # Handle file-like objects
#             if hasattr(raw_value, 'read') and hasattr(raw_value, 'seek'):
#                 try:
#                     raw_value.seek(0)
#                     binary_data = raw_value.read()
#                     if binary_data:
#                         return base64.b64encode(binary_data).decode('ascii')
#                     return None
#                 except Exception as e:
#                     logger.warning(f"Error reading file object for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                     return "[File data]"
            
#             # Handle date objects
#             if hasattr(raw_value, 'strftime'):
#                 return raw_value.isoformat()
            
#             # Handle boolean values
#             if isinstance(raw_value, bool):
#                 return raw_value
            
#             # Handle numeric values
#             if isinstance(raw_value, (int, float)):
#                 return raw_value
            
#             # Convert everything else to string safely
#             try:
#                 if isinstance(raw_value, str):
#                     return raw_value
#                 else:
#                     return str(raw_value)
#             except (UnicodeDecodeError, UnicodeEncodeError) as e:
#                 logger.warning(f"Error converting value to string for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                 if isinstance(raw_value, (bytes, bytearray)):
#                     try:
#                         return base64.b64encode(raw_value).decode('ascii')
#                     except:
#                         return "[Binary data]"
#                 return "[Unserializable data]"
            
#         except Exception as e:
#             logger.error(f"Error getting value for field response {obj.id}: {e}")
#             return None

#     def to_representation(self, instance):
#         """
#         Override to handle cases where related objects might be None or instance is a dict
#         """
#         # Handle dictionary instances (for empty responses)
#         if isinstance(instance, dict):
#             return instance
            
#         try:
#             data = super().to_representation(instance)
            
#             # Safely handle None values for related fields
#             safe_fields = ['submission_id', 'architecture_id', 'architecture_name', 'token']
#             for field in safe_fields:
#                 if not data.get(field):
#                     data[field] = None
            
#             return data
            
#         except Exception as e:
#             logger.error(f"Error in to_representation for instance {instance.id if hasattr(instance, 'id') else 'unknown'}: {e}")
#             return {
#                 'id': getattr(instance, 'id', None),
#                 'field_id': getattr(instance.field, 'id', None) if hasattr(instance, 'field') and instance.field else None,
#                 'field_label': getattr(instance.field, 'label', 'Unknown') if hasattr(instance, 'field') and instance.field else 'Unknown',
#                 'field_type': getattr(instance.field, 'field_type', 'text') if hasattr(instance, 'field') and instance.field else 'text',
#                 'value': None,
#                 'error': 'Error serializing data'
#             }




# class ArchitectureFieldResponseSerializer(serializers.ModelSerializer):
#     field_label = serializers.CharField(source='field.label', read_only=True)
#     field_type = serializers.CharField(source='field.field_type', read_only=True)
#     field_order = serializers.IntegerField(source='field.order', read_only=True)
#     field_required = serializers.BooleanField(source='field.is_required', read_only=True)
#     value = serializers.SerializerMethodField()
#     submission_id = serializers.IntegerField(source='submission.id', read_only=True)
#     architecture_id = serializers.IntegerField(source='submission.token.architecture.id', read_only=True)
#     architecture_name = serializers.CharField(source='submission.token.architecture.name', read_only=True)
#     token = serializers.CharField(source='submission.token.token', read_only=True)

#     class Meta:
#         model = FieldResponse
#         fields = [
#             'id', 'submission_id', 'architecture_id', 'architecture_name', 'token',
#             'field', 'field_label', 'field_type', 'field_order', 'field_required', 
#             'value', 'created_at',
#         ]

#     def get_value(self, obj):
#         """Safely get the value, handling binary data properly"""
#         try:
#             # First, try to get the raw value from the appropriate field
#             field_type = obj.field.field_type if obj.field else 'text'
            
#             # Get value from the correct field based on field type
#             if field_type == 'number':
#                 raw_value = obj.value_number
#             elif field_type == 'date':
#                 raw_value = obj.value_date
#             elif field_type == 'checkbox':
#                 raw_value = obj.value_boolean
#             elif field_type == 'image':
#                 raw_value = obj.value_image
#             elif field_type == 'alphanumeric':
#                 raw_value = obj.value_alphanumeric
#             elif field_type == 'email':
#                 raw_value = obj.value_email
#             elif field_type == 'phonenumber':
#                 raw_value = obj.value_phonenumber
#             else:  # text, dropdown, etc.
#                 raw_value = obj.value_text
            
#             # Handle None values
#             if raw_value is None:
#                 return None
            
#             # Handle image fields specially - return URL instead of file data
#             if field_type == 'image' and raw_value:
#                 if hasattr(raw_value, 'url'):
#                     # It's an ImageField - return URL
#                     request = self.context.get('request')
#                     if request:
#                         return request.build_absolute_uri(raw_value.url)
#                     return raw_value.url
#                 elif hasattr(raw_value, 'name'):
#                     # It has a filename but no URL method
#                     return str(raw_value.name)
#                 else:
#                     # Return string representation
#                     return str(raw_value)
            
#             # Handle binary data safely - don't try to decode it
#             if isinstance(raw_value, (bytes, bytearray)):
#                 try:
#                     # For binary data that's not images, encode as base64
#                     if raw_value:
#                         return base64.b64encode(raw_value).decode('ascii')
#                     return None
#                 except Exception as e:
#                     logger.warning(f"Error encoding binary data for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                     return "[Binary data]"
            
#             # Handle file-like objects
#             if hasattr(raw_value, 'read') and hasattr(raw_value, 'seek'):
#                 try:
#                     raw_value.seek(0)
#                     binary_data = raw_value.read()
#                     if binary_data:
#                         return base64.b64encode(binary_data).decode('ascii')
#                     return None
#                 except Exception as e:
#                     logger.warning(f"Error reading file object for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                     return "[File data]"
            
#             # Handle date objects
#             if hasattr(raw_value, 'strftime'):
#                 return raw_value.isoformat()
            
#             # Handle boolean values
#             if isinstance(raw_value, bool):
#                 return raw_value
            
#             # Handle numeric values
#             if isinstance(raw_value, (int, float)):
#                 return raw_value
            
#             # Handle email values - they are strings but we want to ensure proper formatting
#             if field_type == 'email' and isinstance(raw_value, str):
#                 return raw_value
            
#             # Handle phone number values - they are strings
#             if field_type == 'phonenumber' and isinstance(raw_value, str):
#                 return raw_value
            
#             # Handle alphanumeric values - they are strings
#             if field_type == 'alphanumeric' and isinstance(raw_value, str):
#                 return raw_value
            
#             # Convert everything else to string safely
#             try:
#                 if isinstance(raw_value, str):
#                     return raw_value
#                 else:
#                     return str(raw_value)
#             except (UnicodeDecodeError, UnicodeEncodeError) as e:
#                 logger.warning(f"Error converting value to string for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                 if isinstance(raw_value, (bytes, bytearray)):
#                     try:
#                         return base64.b64encode(raw_value).decode('ascii')
#                     except:
#                         return "[Binary data]"
#                 return "[Unserializable data]"
            
#         except Exception as e:
#             logger.error(f"Error getting value for field response {obj.id}: {e}")
#             return None

#     def to_representation(self, instance):
#         """
#         Override to handle cases where related objects might be None or instance is a dict
#         """
#         # Handle dictionary instances (for empty responses)
#         if isinstance(instance, dict):
#             return instance
            
#         try:
#             data = super().to_representation(instance)
            
#             # Safely handle None values for related fields
#             safe_fields = ['submission_id', 'architecture_id', 'architecture_name', 'token']
#             for field in safe_fields:
#                 if not data.get(field):
#                     data[field] = None
            
#             return data
            
#         except Exception as e:
#             logger.error(f"Error in to_representation for instance {instance.id if hasattr(instance, 'id') else 'unknown'}: {e}")
#             return {
#                 'id': getattr(instance, 'id', None),
#                 'field_id': getattr(instance.field, 'id', None) if hasattr(instance, 'field') and instance.field else None,
#                 'field_label': getattr(instance.field, 'label', 'Unknown') if hasattr(instance, 'field') and instance.field else 'Unknown',
#                 'field_type': getattr(instance.field, 'field_type', 'text') if hasattr(instance, 'field') and instance.field else 'text',
#                 'value': None,
#                 'error': 'Error serializing data'
#             }






import base64
import logging
from rest_framework import serializers
from student_api.models import FieldResponse  # Update with your actual import

logger = logging.getLogger(__name__)

# class ArchitectureFieldResponseSerializer(serializers.ModelSerializer):
#     field_label = serializers.CharField(source='field.label', read_only=True)
#     field_type = serializers.CharField(source='field.field_type', read_only=True)
#     field_order = serializers.IntegerField(source='field.order', read_only=True)
#     field_required = serializers.BooleanField(source='field.is_required', read_only=True)
#     value = serializers.SerializerMethodField()
#     submission_id = serializers.IntegerField(source='submission.id', read_only=True)
#     architecture_id = serializers.IntegerField(source='submission.token.architecture.id', read_only=True)
#     architecture_name = serializers.CharField(source='submission.token.architecture.name', read_only=True)
#     token = serializers.CharField(source='submission.token.token', read_only=True)

#     class Meta:
#         model = FieldResponse
#         fields = [
#             'id', 'submission_id', 'architecture_id', 'architecture_name', 'token',
#             'field', 'field_label', 'field_type', 'field_order', 'field_required', 
#             'value', 'created_at',
#         ]

#     def get_value(self, obj):
#         """Safely get the value, handling binary data properly"""
#         try:
#             # Handle None or invalid objects
#             if obj is None or not hasattr(obj, 'field'):
#                 return None
            
#             # Get field type safely
#             field_type = obj.field.field_type if obj.field else 'text'
            
#             # Get value from the correct field based on field type
#             raw_value = None
#             if field_type == 'number':
#                 raw_value = obj.value_number
#             elif field_type == 'date':
#                 raw_value = obj.value_date
#             elif field_type == 'checkbox':
#                 raw_value = obj.value_boolean
#             elif field_type == 'image':
#                 raw_value = obj.value_image
#             elif field_type == 'alphanumeric':
#                 raw_value = obj.value_alphanumeric
#             elif field_type == 'email':
#                 raw_value = obj.value_text  # Email stored as text
#             elif field_type == 'phonenumber':
#                 raw_value = obj.value_text  # Phone stored as text
#             else:  # text, dropdown, etc.
#                 raw_value = obj.value_text
            
#             # Handle None values
#             if raw_value is None:
#                 return None
            
#             # Handle image fields specially - return URL instead of file data
#             if field_type == 'image' and raw_value:
#                 if hasattr(raw_value, 'url'):
#                     # It's an ImageField - return URL
#                     request = self.context.get('request')
#                     if request:
#                         return request.build_absolute_uri(raw_value.url)
#                     return raw_value.url
#                 elif hasattr(raw_value, 'name'):
#                     # It has a filename but no URL method
#                     return str(raw_value.name)
#                 else:
#                     # Return string representation
#                     return str(raw_value)
            
#             # Handle binary data safely - don't try to decode it
#             if isinstance(raw_value, (bytes, bytearray)):
#                 try:
#                     # For binary data that's not images, encode as base64
#                     if raw_value:
#                         return base64.b64encode(raw_value).decode('ascii')
#                     return None
#                 except Exception as e:
#                     logger.warning(f"Error encoding binary data for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                     return "[Binary data]"
            
#             # Handle file-like objects
#             if hasattr(raw_value, 'read') and hasattr(raw_value, 'seek'):
#                 try:
#                     raw_value.seek(0)
#                     binary_data = raw_value.read()
#                     if binary_data:
#                         return base64.b64encode(binary_data).decode('ascii')
#                     return None
#                 except Exception as e:
#                     logger.warning(f"Error reading file object for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                     return "[File data]"
            
#             # Handle date objects
#             if hasattr(raw_value, 'strftime'):
#                 return raw_value.isoformat()
            
#             # Handle boolean values
#             if isinstance(raw_value, bool):
#                 return raw_value
            
#             # Handle numeric values
#             if isinstance(raw_value, (int, float)):
#                 return raw_value
            
#             # Handle email values - they are strings but we want to ensure proper formatting
#             if field_type == 'email' and isinstance(raw_value, str):
#                 return raw_value
            
#             # Handle phone number values - they are strings
#             if field_type == 'phonenumber' and isinstance(raw_value, str):
#                 return raw_value
            
#             # Handle alphanumeric values - they are strings
#             if field_type == 'alphanumeric' and isinstance(raw_value, str):
#                 return raw_value
            
#             # Convert everything else to string safely
#             try:
#                 if isinstance(raw_value, str):
#                     return raw_value
#                 else:
#                     return str(raw_value)
#             except (UnicodeDecodeError, UnicodeEncodeError) as e:
#                 logger.warning(f"Error converting value to string for field {obj.field.label if obj.field else 'unknown'}: {e}")
#                 if isinstance(raw_value, (bytes, bytearray)):
#                     try:
#                         return base64.b64encode(raw_value).decode('ascii')
#                     except:
#                         return "[Binary data]"
#                 return "[Unserializable data]"
            
#         except Exception as e:
#             logger.error(f"Error getting value for field response {getattr(obj, 'id', 'unknown')}: {e}")
#             return None

#     def to_representation(self, instance):
#         """
#         Override to handle cases where related objects might be None or instance is a dict
#         This ensures null values are properly displayed for missing data
#         """
#         # Handle dictionary instances (for empty/null responses from view)
#         if isinstance(instance, dict):
#             return {
#                 'id': instance.get('id'),
#                 'submission_id': instance.get('submission_id'),
#                 'architecture_id': instance.get('architecture_id'),
#                 'architecture_name': instance.get('architecture_name'),
#                 'token': instance.get('token'),
#                 'field': instance.get('field'),
#                 'field_label': instance.get('field_label'),
#                 'field_type': instance.get('field_type'),
#                 'field_order': instance.get('field_order'),
#                 'field_required': instance.get('field_required'),
#                 'value': instance.get('value'),
#                 'created_at': instance.get('created_at')
#             }
        
#         # Handle None instances
#         if instance is None:
#             return {
#                 'id': None,
#                 'submission_id': None,
#                 'architecture_id': None,
#                 'architecture_name': None,
#                 'token': None,
#                 'field': None,
#                 'field_label': None,
#                 'field_type': None,
#                 'field_order': None,
#                 'field_required': None,
#                 'value': None,
#                 'created_at': None
#             }
            
#         try:
#             data = super().to_representation(instance)
            
#             # Safely handle None values for related fields
#             # This ensures we don't get errors when related objects are missing
#             safe_fields = ['submission_id', 'architecture_id', 'architecture_name', 'token']
#             for field in safe_fields:
#                 if data.get(field) is None:
#                     data[field] = None
            
#             # Ensure field values are properly set even if None
#             if data.get('field') is None and instance.field:
#                 data['field'] = instance.field.id
            
#             return data
            
#         except Exception as e:
#             logger.error(f"Error in to_representation for instance {getattr(instance, 'id', 'unknown')}: {e}")
#             # Return a minimal representation with available data
#             return {
#                 'id': getattr(instance, 'id', None),
#                 'submission_id': getattr(instance.submission, 'id', None) if hasattr(instance, 'submission') and instance.submission else None,
#                 'architecture_id': getattr(instance.submission.token.architecture, 'id', None) if hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token') and instance.submission.token and hasattr(instance.submission.token, 'architecture') else None,
#                 'architecture_name': str(instance.submission.token.architecture) if hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token') and instance.submission.token and hasattr(instance.submission.token, 'architecture') else None,
#                 'token': getattr(instance.submission.token, 'token', None) if hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token') else None,
#                 'field': getattr(instance.field, 'id', None) if hasattr(instance, 'field') and instance.field else None,
#                 'field_label': getattr(instance.field, 'label', 'Unknown') if hasattr(instance, 'field') and instance.field else 'Unknown',
#                 'field_type': getattr(instance.field, 'field_type', 'text') if hasattr(instance, 'field') and instance.field else 'text',
#                 'field_order': getattr(instance.field, 'order', 0) if hasattr(instance, 'field') and instance.field else 0,
#                 'field_required': getattr(instance.field, 'is_required', False) if hasattr(instance, 'field') and instance.field else False,
#                 'value': None,
#                 'created_at': getattr(instance, 'created_at', None),
#                 'error': 'Error serializing data'
#             }





class ArchitectureFieldResponseSerializer(serializers.ModelSerializer):
    field_label = serializers.CharField(source='field.label', read_only=True)
    field_type = serializers.CharField(source='field.field_type', read_only=True)
    field_order = serializers.IntegerField(source='field.order', read_only=True)
    field_required = serializers.BooleanField(source='field.is_required', read_only=True)
    value = serializers.SerializerMethodField()
    submission_id = serializers.IntegerField(source='submission.id', read_only=True)
    architecture_id = serializers.IntegerField(source='submission.token.architecture.id', read_only=True)
    architecture_name = serializers.CharField(source='submission.token.architecture.name', read_only=True)
    token = serializers.CharField(source='submission.token.token', read_only=True)

    class Meta:
        model = FieldResponse
        fields = [
            'id', 'submission_id', 'architecture_id', 'architecture_name', 'token',
            'field', 'field_label', 'field_type', 'field_order', 'field_required', 
            'value', 'created_at',
        ]

    def get_value(self, obj):
        """
        Safely get the value based on field type
        Handles all field types including email, phonenumber, and image
        """
        try:
            # Handle None or invalid objects
            if obj is None or not hasattr(obj, 'field') or obj.field is None:
                return None
            
            field_type = obj.field.field_type
            
            # Get the appropriate value based on field type
            raw_value = self._get_raw_value(obj, field_type)
            
            # Handle None values
            if raw_value is None:
                return None
            
            # Process value based on field type
            return self._process_value_by_type(raw_value, field_type, obj)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in get_value for field response {getattr(obj, 'id', 'unknown')}: {e}")
            return None

    def _get_raw_value(self, obj, field_type):
        """Extract raw value from the appropriate field based on field type"""
        
        # Map field types to their corresponding value fields
        field_mapping = {
            'number': 'value_number',
            'date': 'value_date',
            'checkbox': 'value_boolean',
            'image': 'value_image',
            'alphanumeric': 'value_alphanumeric',
            'email': 'value_email',
            'phonenumber': 'value_phonenumber',
            'text': 'value_text',
            'dropdown': 'value_text',
            'radio': 'value_text',
            'textarea': 'value_text',
        }
        
        # Get the field name to use
        value_field = field_mapping.get(field_type, 'value_text')
        
        # Check if the attribute exists
        if hasattr(obj, value_field):
            return getattr(obj, value_field)
        
        # Fallback to value_text for backward compatibility
        if hasattr(obj, 'value_text'):
            return obj.value_text
        
        return None

    def _process_value_by_type(self, raw_value, field_type, obj):
        """Process the raw value based on field type"""
        
        # Handle image fields
        if field_type == 'image':
            return self._process_image_value(raw_value)
        
        # Handle binary data
        if isinstance(raw_value, (bytes, bytearray)):
            return self._process_binary_value(raw_value, obj)
        
        # Handle file-like objects
        if hasattr(raw_value, 'read') and hasattr(raw_value, 'seek'):
            return self._process_file_object(raw_value, obj)
        
        # Handle date objects
        if hasattr(raw_value, 'strftime'):
            return raw_value.isoformat()
        
        # Handle boolean values
        if isinstance(raw_value, bool):
            return raw_value
        
        # Handle numeric values
        if isinstance(raw_value, (int, float)):
            return raw_value
        
        # Handle email values
        if field_type == 'email':
            return self._process_email_value(raw_value)
        
        # Handle phone number values
        if field_type == 'phonenumber':
            return self._process_phonenumber_value(raw_value)
        
        # Handle string values
        if isinstance(raw_value, str):
            return raw_value
        
        # Convert everything else to string safely
        return self._safe_string_conversion(raw_value, obj)

    def _process_image_value(self, raw_value):
        """Process image field value and return URL"""
        if not raw_value:
            return None
            
        # If it's an ImageField with URL
        if hasattr(raw_value, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(raw_value.url)
            return raw_value.url
        
        # If it has a name attribute (file path)
        if hasattr(raw_value, 'name'):
            # Try to construct URL
            if hasattr(raw_value, 'storage'):
                try:
                    url = raw_value.storage.url(raw_value.name)
                    request = self.context.get('request')
                    if request:
                        return request.build_absolute_uri(url)
                    return url
                except:
                    pass
            return f"/media/{raw_value.name}"
        
        # If it's a string path
        if isinstance(raw_value, str):
            if raw_value.startswith(('http://', 'https://')):
                return raw_value
            if raw_value.startswith('/media/'):
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(raw_value)
                return raw_value
            return f"/media/{raw_value}"
        
        # Return string representation as fallback
        return str(raw_value)

    def _process_binary_value(self, raw_value, obj):
        """Process binary data and return base64 encoded string"""
        try:
            if raw_value:
                import base64
                return base64.b64encode(raw_value).decode('ascii')
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error encoding binary data for field {obj.field.label if obj.field else 'unknown'}: {e}")
            return "[Binary data]"

    def _process_file_object(self, raw_value, obj):
        """Process file-like object and return base64 encoded data"""
        try:
            raw_value.seek(0)
            binary_data = raw_value.read()
            if binary_data:
                import base64
                return base64.b64encode(binary_data).decode('ascii')
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error reading file object for field {obj.field.label if obj.field else 'unknown'}: {e}")
            return "[File data]"

    def _process_email_value(self, raw_value):
        """Process email value - ensure proper formatting"""
        if raw_value is None:
            return None
            
        if isinstance(raw_value, str):
            # Clean and normalize email
            email = raw_value.strip().lower()
            # Basic validation - you might want to add more sophisticated validation
            if '@' in email and '.' in email:
                return email
            return email  # Return as-is even if format seems invalid
        return str(raw_value)

    def _process_phonenumber_value(self, raw_value):
        """Process phone number value - ensure proper formatting"""
        if raw_value is None:
            return None
            
        if isinstance(raw_value, str):
            # Clean phone number (remove extra spaces)
            phone = raw_value.strip()
            # You might want to add phone number formatting here
            # For now, return as-is
            return phone
        if isinstance(raw_value, (int, float)):
            # Convert numeric phone to string
            return str(raw_value)
        return str(raw_value)

    def _safe_string_conversion(self, raw_value, obj):
        """Safely convert value to string"""
        try:
            if isinstance(raw_value, str):
                return raw_value
            return str(raw_value)
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error converting value to string for field {obj.field.label if obj.field else 'unknown'}: {e}")
            
            if isinstance(raw_value, (bytes, bytearray)):
                try:
                    import base64
                    return base64.b64encode(raw_value).decode('ascii')
                except:
                    return "[Binary data]"
            return "[Unserializable data]"

    def to_representation(self, instance):
        """
        Override to handle cases where related objects might be None or instance is a dict
        This ensures null values are properly displayed for missing data
        """
        # Handle dictionary instances (for empty/null responses from view)
        if isinstance(instance, dict):
            return {
                'id': instance.get('id'),
                'submission_id': instance.get('submission_id'),
                'architecture_id': instance.get('architecture_id'),
                'architecture_name': instance.get('architecture_name'),
                'token': instance.get('token'),
                'field': instance.get('field'),
                'field_label': instance.get('field_label'),
                'field_type': instance.get('field_type'),
                'field_order': instance.get('field_order'),
                'field_required': instance.get('field_required'),
                'value': instance.get('value'),
                'created_at': instance.get('created_at')
            }
        
        # Handle None instances
        if instance is None:
            return {
                'id': None,
                'submission_id': None,
                'architecture_id': None,
                'architecture_name': None,
                'token': None,
                'field': None,
                'field_label': None,
                'field_type': None,
                'field_order': None,
                'field_required': None,
                'value': None,
                'created_at': None
            }
            
        try:
            data = super().to_representation(instance)
            
            # Safely handle None values for related fields
            safe_fields = ['submission_id', 'architecture_id', 'architecture_name', 'token']
            for field in safe_fields:
                if data.get(field) is None:
                    # Try to get values from related objects if they exist
                    if field == 'submission_id' and hasattr(instance, 'submission') and instance.submission:
                        data[field] = instance.submission.id
                    elif field == 'architecture_id' and hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token') and instance.submission.token and hasattr(instance.submission.token, 'architecture'):
                        data[field] = instance.submission.token.architecture.id
                    elif field == 'architecture_name' and hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token') and instance.submission.token and hasattr(instance.submission.token, 'architecture'):
                        data[field] = str(instance.submission.token.architecture)
                    elif field == 'token' and hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token'):
                        data[field] = instance.submission.token.token
                    else:
                        data[field] = None
            
            # Ensure field values are properly set
            if data.get('field') is None and instance.field:
                data['field'] = instance.field.id
                
            if data.get('field_label') is None and instance.field:
                data['field_label'] = instance.field.label
                
            if data.get('field_type') is None and instance.field:
                data['field_type'] = instance.field.field_type
                
            if data.get('field_order') is None and instance.field:
                data['field_order'] = instance.field.order
                
            if data.get('field_required') is None and instance.field:
                data['field_required'] = instance.field.is_required
            
            return data
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in to_representation for instance {getattr(instance, 'id', 'unknown')}: {e}")
            
            # Return a minimal representation with available data
            return {
                'id': getattr(instance, 'id', None),
                'submission_id': getattr(instance.submission, 'id', None) if hasattr(instance, 'submission') and instance.submission else None,
                'architecture_id': getattr(instance.submission.token.architecture, 'id', None) if hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token') and instance.submission.token and hasattr(instance.submission.token, 'architecture') else None,
                'architecture_name': str(instance.submission.token.architecture) if hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token') and instance.submission.token and hasattr(instance.submission.token, 'architecture') else None,
                'token': getattr(instance.submission.token, 'token', None) if hasattr(instance, 'submission') and instance.submission and hasattr(instance.submission, 'token') else None,
                'field': getattr(instance.field, 'id', None) if hasattr(instance, 'field') and instance.field else None,
                'field_label': getattr(instance.field, 'label', 'Unknown') if hasattr(instance, 'field') and instance.field else 'Unknown',
                'field_type': getattr(instance.field, 'field_type', 'text') if hasattr(instance, 'field') and instance.field else 'text',
                'field_order': getattr(instance.field, 'order', 0) if hasattr(instance, 'field') and instance.field else 0,
                'field_required': getattr(instance.field, 'is_required', False) if hasattr(instance, 'field') and instance.field else False,
                'value': None,
                'created_at': getattr(instance, 'created_at', None),
                'error': 'Error serializing data'
            }
#________________ above code 3/10/2025++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((()))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))



# Add these imports at the top
# from django.contrib.auth import get_user_model
# from rest_framework import serializers
# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework import serializers
# from django.contrib.auth import get_user_model
# from django.core.validators import MinLengthValidator, EmailValidator, RegexValidator


# User = get_user_model()

# # User Serializer
# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ['id', 'username', 'email', 'first_name', 'last_name', 
#                  'is_approved', 'is_active', 'date_joined', 'last_login']
#         read_only_fields = ['id', 'date_joined', 'last_login']

# # Registration Serializer


# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, min_length=8)
#     password_confirm = serializers.CharField(write_only=True, min_length=8)

#     class Meta:
#         model = User
#         fields = [
#             'full_name',      # 1. Full name first
#             'username',       # 2. Username second  
#             'email',          # 3. Email third
#             'phone_number',   # 4. Phone number
#             'college_company', # 5. College/Company
#             'address',        # 6. Address
#             'password',       # 7. Password
#             'password_confirm', # 8. Password confirm
#             # Role is excluded - will be set to 'customer' by default
#         ]
#         extra_kwargs = {
#             'username': {
#                 'validators': [MinLengthValidator(3, "Username must be at least 3 characters long.")]
#             },
#             'full_name': {
#                 'validators': [MinLengthValidator(3, "Full name must be at least 3 characters long.")]
#             },
#             'email': {
#                 'validators': [EmailValidator(message="Enter a valid email address.")]
#             },
#             'phone_number': {
#                 'required': False,
#                 'allow_blank': True,
#                 'validators': [
#                     RegexValidator(
#                         regex=r'^\+?\d{10,15}$',
#                         message="Enter a valid phone number (10–15 digits, may start with +)."
#                     )
#                 ]
#             },
#             'college_company': {
#                 'required': False,
#                 'allow_blank': True,
#                 'validators': [MinLengthValidator(2, "College/Company name must be at least 2 characters long.")]
#             },
#             'address': {
#                 'required': False,
#                 'allow_blank': True
#             }
#         }

#     def validate(self, attrs):
#         # Check if passwords match
#         if attrs['password'] != attrs['password_confirm']:
#             raise serializers.ValidationError("Passwords do not match")
        
#         # Validate phone number format if provided
#         phone_number = attrs.get('phone_number')
#         if phone_number and phone_number.strip():  # Check if not empty
#             import re
#             if not re.match(r'^\+?\d{10,15}$', phone_number):
#                 raise serializers.ValidationError({
#                     'phone_number': "Enter a valid phone number (10–15 digits, may start with +)."
#                 })
        
#         return attrs

#     def create(self, validated_data):
#         validated_data.pop('password_confirm')
        
#         # Set default role to 'customer'
#         validated_data['role'] = 'customer'
        
#         user = User.objects.create_user(**validated_data)
#         return user

# # Custom Token Serializer
# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         data = super().validate(attrs)
        
#         # Add custom claims
#         data.update({
#             'username': self.user.username,
#             'email': self.user.email,
#             'is_approved': self.user.is_approved,
#             'is_staff': self.user.is_staff,
#             'is_superuser': self.user.is_superuser
#         })
#         return data

# # Admin Token Serializer
# class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         data = super().validate(attrs)
        
#         # Check if user is admin
#         if not (self.user.is_staff or self.user.is_superuser):
#             raise serializers.ValidationError("Admin access required")
            
#         data.update({
#             'username': self.user.username,
#             'email': self.user.email,
#             'is_staff': self.user.is_staff,
#             'is_superuser': self.user.is_superuser
#         })
#         return data

#-------------------6/10/2025

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator, EmailValidator, RegexValidator

User = get_user_model()

# User Serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'is_approved', 'is_active', 'date_joined', 'last_login', 'role']  # Added 'role'
        read_only_fields = ['id', 'date_joined', 'last_login', 'role']

# Registration Serializer
# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, min_length=8)
#     password_confirm = serializers.CharField(write_only=True, min_length=8)

#     class Meta:
#         model = User
#         fields = [
#             'full_name',      # 1. Full name first
#             'username',       # 2. Username second  
#             'email',          # 3. Email third
#             'phone_number',   # 4. Phone number
#             'college_company', # 5. College/Company
#             'address',        # 6. Address
#             'password',       # 7. Password
#             'password_confirm', # 8. Password confirm
#             # Role is excluded - will be set to 'customer' by default
#         ]
#         extra_kwargs = {
#             'username': {
#                 'validators': [MinLengthValidator(3, "Username must be at least 3 characters long.")]
#             },
#             'full_name': {
#                 'validators': [MinLengthValidator(3, "Full name must be at least 3 characters long.")]
#             },
#             'email': {
#                 'validators': [EmailValidator(message="Enter a valid email address.")]
#             },
#             'phone_number': {
#                 'required': False,
#                 'allow_blank': True,
#                 'validators': [
#                     RegexValidator(
#                         regex=r'^\+?\d{10,15}$',
#                         message="Enter a valid phone number (10–15 digits, may start with +)."
#                     )
#                 ]
#             },
#             'college_company': {
#                 'required': False,
#                 'allow_blank': True,
#                 'validators': [MinLengthValidator(2, "College/Company name must be at least 2 characters long.")]
#             },
#             'address': {
#                 'required': False,
#                 'allow_blank': True
#             }
#         }

#     def validate(self, attrs):
#         # Check if passwords match
#         if attrs['password'] != attrs['password_confirm']:
#             raise serializers.ValidationError("Passwords do not match")
        
#         # Validate phone number format if provided
#         phone_number = attrs.get('phone_number')
#         if phone_number and phone_number.strip():  # Check if not empty
#             import re
#             if not re.match(r'^\+?\d{10,15}$', phone_number):
#                 raise serializers.ValidationError({
#                     'phone_number': "Enter a valid phone number (10–15 digits, may start with +)."
#                 })
        
#         return attrs

#     def create(self, validated_data):
#         validated_data.pop('password_confirm')
        
#         # Set default role to 'customer'
#         validated_data['role'] = 'customer'
        
#         user = User.objects.create_user(**validated_data)
#         return user

#14/10/2025

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'full_name',      # 1. Full name first
            'username',       # 2. Username second  
            'email',          # 3. Email third
            'phone_number',   # 4. Phone number
            'college_company', # 5. College/Company
            'address',        # 6. Address
            'password',       # 7. Password
            'password_confirm', # 8. Password confirm
        ]
        extra_kwargs = {
            'username': {
                'validators': [MinLengthValidator(3, "Username must be at least 3 characters long.")]
            },
            'full_name': {
                'validators': [MinLengthValidator(3, "Full name must be at least 3 characters long.")]
            },
            'email': {
                'validators': [EmailValidator(message="Enter a valid email address.")]
            },
            'phone_number': {
                'required': False,
                'allow_blank': True,
                'validators': [
                    RegexValidator(
                        regex=r'^\+?\d{10,15}$',
                        message="Enter a valid phone number (10–15 digits, may start with +)."
                    )
                ]
            },
            'college_company': {
                'required': False,
                'allow_blank': True,
                'validators': [MinLengthValidator(2, "College/Company name must be at least 2 characters long.")]
            },
            'address': {
                'required': False,
                'allow_blank': True
            }
        }

    def validate(self, attrs):
        # Check if passwords match
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Validate phone number format if provided
        phone_number = attrs.get('phone_number')
        if phone_number and phone_number.strip():
            import re
            if not re.match(r'^\+?\d{10,15}$', phone_number):
                raise serializers.ValidationError({
                    'phone_number': "Enter a valid phone number (10–15 digits, may start with +)."
                })
        
        # Check if email already exists
        email = attrs.get('email')
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': 'A user with this email already exists.'
            })
        
        # Check if username already exists
        username = attrs.get('username')
        if username and User.objects.filter(username=username).exists():
            raise serializers.ValidationError({
                'username': 'A user with this username already exists.'
            })
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        
        # Set default role to 'customer'
        validated_data['role'] = 'customer'
        
        # Use try-except as additional safety net
        try:
            user = User.objects.create_user(**validated_data)
            return user
        except IntegrityError as e:
            if 'email' in str(e):
                raise serializers.ValidationError({'email': 'This email is already registered.'})
            elif 'username' in str(e):
                raise serializers.ValidationError({'username': 'This username is already taken.'})
            raise serializers.ValidationError('User registration failed due to database error.')

# Custom Token Serializer 8/10/2025
# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         data = super().validate(attrs)
        
#         # Add custom claims including role
#         data.update({
#             'username': self.user.username,
#             'email': self.user.email,
#             'role': self.user.role,  # Added role
#             'is_approved': self.user.is_approved,
#             'is_staff': self.user.is_staff,
#             'is_superuser': self.user.is_superuser,
#             'user': {  # Add complete user object
#                 'id': self.user.id,
#                 'username': self.user.username,
#                 'email': self.user.email,
#                 'role': self.user.role,
#                 'first_name': self.user.first_name,
#                 'last_name': self.user.last_name,
#                 'is_approved': self.user.is_approved,
#                 'is_active': self.user.is_active
#             }
#         })
#         return data/8/102025--------------------------
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs[self.username_field]
        password = attrs['password']
        
        # Single database query with only needed fields
        try:
            user_query = User.objects
            if '@' in username:
                user = user_query.only(
                    'id', 'username', 'password', 'is_active', 
                    'is_approved', 'email', 'role'
                ).get(email=username)
            else:
                user = user_query.only(
                    'id', 'username', 'password', 'is_active', 
                    'is_approved', 'email', 'role'
                ).get(username=username)
            
            # Quick status checks first
            if not user.is_active:
                raise serializers.ValidationError(
                    "Your account is deactivated.",
                    code='account_inactive'
                )
            
            if not user.is_approved:
                raise serializers.ValidationError(
                    "Your account is pending approval.",
                    code='account_not_approved'
                )
            
            # Password check (this is the slowest operation)
            if not user.check_password(password):
                raise serializers.ValidationError(
                    "You have entered wrong password.",
                    code='wrong_password'
                )
            
            # Set user for token generation
            self.user = user
            
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No account found with this email/username.",
                code='user_not_found'
            )
        
        # Generate tokens directly without calling super()
        refresh = self.get_token(self.user)
        data = {}
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        
        # Add custom claims
        data.update({
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'is_approved': self.user.is_approved,
            'is_staff': self.user.is_staff,
            'is_superuser': self.user.is_superuser,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'email': self.user.email,
                'role': self.user.role,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'is_approved': self.user.is_approved,
                'is_active': self.user.is_active
            }
        })
        return data
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims to token payload
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        token['is_approved'] = user.is_approved
        return token
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@14/10/2025
# Admin Token Serializer
# class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         data = super().validate(attrs)
        
#         # Check if user is admin
#         if not (self.user.is_staff or self.user.is_superuser):
#             raise serializers.ValidationError("Admin access required")
            
#         data.update({
#             'username': self.user.username,
#             'email': self.user.email,
#             'role': self.user.role,  # Added role
#             'is_staff': self.user.is_staff,
#             'is_superuser': self.user.is_superuser,
#             'user': {  # Add complete user object
#                 'id': self.user.id,
#                 'username': self.user.username,
#                 'email': self.user.email,
#                 'role': self.user.role,
#                 'first_name': self.user.first_name,
#                 'last_name': self.user.last_name,
#                 'is_approved': self.user.is_approved,
#                 'is_active': self.user.is_active
#             }
#         })
#         return data
#14.888888888888888800000000000000000
# serializers.py - Fix the AdminTokenObtainPairSerializer
class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs[self.username_field]
        password = attrs['password']
        
        try:
            # Single database query for admin users
            user_query = User.objects
            if '@' in username:
                user = user_query.only(
                    'id', 'username', 'password', 'is_active', 
                    'is_approved', 'email', 'role', 'is_staff', 'is_superuser'
                ).get(email=username)
            else:
                user = user_query.only(
                    'id', 'username', 'password', 'is_active', 
                    'is_approved', 'email', 'role', 'is_staff', 'is_superuser'
                ).get(username=username)
            
            # ✅ Check if user is admin/staff
            if not (user.is_staff or user.is_superuser):
                raise serializers.ValidationError(
                    "Admin access required. Only staff/superusers can login here.",
                    code='admin_access_required'
                )
            
            # Check if user is active
            if not user.is_active:
                raise serializers.ValidationError(
                    "Your account is deactivated.",
                    code='account_inactive'
                )
            
            # Password check
            if not user.check_password(password):
                raise serializers.ValidationError(
                    "You have entered wrong password.",
                    code='wrong_password'
                )
            
            self.user = user
            
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No admin account found with this email/username.",
                code='admin_not_found'
            )
        
        # Generate tokens
        refresh = self.get_token(self.user)
        data = {}
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        
        # Add custom claims
        data.update({
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'is_approved': self.user.is_approved,
            'is_staff': self.user.is_staff,
            'is_superuser': self.user.is_superuser,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'email': self.user.email,
                'role': self.user.role,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'is_approved': self.user.is_approved,
                'is_active': self.user.is_active,
                'is_staff': self.user.is_staff,
                'is_superuser': self.user.is_superuser
            }
        })
        return data
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add admin claims to token payload
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        token['is_approved'] = user.is_approved
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        return token

#---------------------------------8/10/2025
        # serializers.py
# serializers.py
# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .utils.otp_utils import generate_otp, store_otp, send_otp_email, verify_otp, delete_otp, resend_otp, can_resend_otp

# Get the custom user model
User = get_user_model()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Check if email exists in database
        try:
            user = User.objects.get(email=value)
            if not user.is_active:
                raise serializers.ValidationError("User account is deactivated.")
            if hasattr(user, 'is_approved') and not user.is_approved:
                raise serializers.ValidationError("User account is not approved.")
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")
        return value
    
    def save(self):
        email = self.validated_data['email']
        
        # Get user (we know it exists because validation passed)
        user = User.objects.get(email=email)
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP in cache
        store_otp(email, otp)
        
        # Initialize resend count
        cache_key = f"otp_resend_count_{email}"
        cache.set(cache_key, 0, timeout=600)  # 10 minutes
        
        # Send email with OTP
        send_otp_email(user, otp)
        
        return {
            'email': email,
            'otp_sent': True
        }

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Check if email exists in database
        try:
            user = User.objects.get(email=value)
            if not user.is_active:
                raise serializers.ValidationError("User account is deactivated.")
            if hasattr(user, 'is_approved') and not user.is_approved:
                raise serializers.ValidationError("User account is not approved.")
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")
        return value
    
    def validate(self, attrs):
        email = attrs['email']
        
        # Check if user can resend OTP (prevent spam)
        can_resend, message = can_resend_otp(email)
        if not can_resend:
            raise serializers.ValidationError(message)
        
        return attrs
    
    def save(self):
        email = self.validated_data['email']
        
        # Get user (we know it exists because validation passed)
        user = User.objects.get(email=email)
        
        # Increment resend count
        cache_key = f"otp_resend_count_{email}"
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, timeout=600)  # Reset 10min timer
        
        # Resend OTP
        success, message = resend_otp(email)
        
        return {
            'email': email,
            'success': success,
            'message': message
        }

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        email = attrs['email']
        otp = attrs['otp']
        
        # First check if user exists
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise serializers.ValidationError("User account is deactivated.")
            if hasattr(user, 'is_approved') and not user.is_approved:
                raise serializers.ValidationError("User account is not approved.")
            
            attrs['user'] = user
            
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")
        
        # Then check if OTP exists and is valid
        if not verify_otp(email, otp):
            raise serializers.ValidationError("Invalid or expired OTP.")
        
        return attrs
    
    def save(self):
        # OTP is verified, we can proceed to password reset
        email = self.validated_data['email']
        # Don't delete OTP yet, we need it for password reset confirmation
        return self.validated_data['user']

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs['email']
        otp = attrs['otp']
        new_password = attrs['new_password']
        confirm_password = attrs['confirm_password']
        
        # Check if passwords match
        if new_password != confirm_password:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })
        
        # First check if user exists
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise serializers.ValidationError("User account is deactivated.")
            if hasattr(user, 'is_approved') and not user.is_approved:
                raise serializers.ValidationError("User account is not approved.")
            
            attrs['user'] = user
            
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")
        
        # Then verify OTP
        if not verify_otp(email, otp):
            raise serializers.ValidationError("Invalid or expired OTP.")
        
        return attrs
    
    def save(self):
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        email = self.validated_data['email']
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Delete OTP after successful password reset
        delete_otp(email)
        
        # Also delete resend count
        cache_key = f"otp_resend_count_{email}"
        cache.delete(cache_key)
        
        return user

    #23--10-2025________________________++++++++++++++++++++++++++++++++============================================================================

from rest_framework import serializers
from .models import Architecture

class ArchitectureSendToAdminSerializer(serializers.ModelSerializer):
    """Serializer specifically for updating custm_sent_to_admin field only"""
    class Meta:
        model = Architecture
        fields = ['custm_sent_to_admin']
        
    def update(self, instance, validated_data):
        """Update only the custm_sent_to_admin field"""
        instance.custm_sent_to_admin = True  # Always set to True
        instance.save()
        return instance


#---=======================23/3.30=========================

class CustomSentRecordForIDSerializer(serializers.ModelSerializer):
    created_by_username = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Architecture
        fields = [
            'id',
            'name',
            'institution_type',
            'department_name', 
            'student_count',
            'staff_count',
            'class_name',
            'division',
            'custm_sent_to_admin',
            'created_by_username',  # Use the method field instead
            'created_at',
            'status',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_created_by_username(self, obj):
        # Safely handle cases where created_by might be None
        return obj.created_by.username if obj.created_by else None
# serializers.py
# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 
            'username', 
            'email', 
            'full_name', 
            'phone_number', 
            'college_company', 
            'address', 
            'role', 
            'is_approved',
            'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']
# serializers.py
from rest_framework import serializers
from .models import Architecture

class ArchitectureSerializer1(serializers.ModelSerializer):
    """Simple serializer that returns only architecture model fields"""
    class Meta:
        model = Architecture
        fields = [
            'id',
            'name',
            'institution_type',
            'parent',
            'department_name',
            'class_name',
            'division',
            'student_count',
            'staff_count',
            'is_active',
            'custm_sent_to_admin',
            'created_by',
            'created_at',
            'updated_at',
            'status',
        ]
        read_only_fields = ['created_at', 'updated_at']
from rest_framework import serializers
from .models import Architecture

class StatusArchitectureSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Architecture
        fields = [
            'id', 'name', 'institution_type', 'parent', 'department_name', 
            'class_name', 'division', 'student_count', 'staff_count', 
            'status', 'status_display', 'is_active', 'custm_sent_to_admin',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['status_display', 'created_at', 'updated_at']




























from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Statistic, PortfolioItem, Service, Testimonial, 
    Client, Slide1, Slide2
)

User = get_user_model()

# User Serializer (for Slide serializers only)
class UserSerializer(serializers.ModelSerializer):
    """Serializer for reading user data in slides"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = fields

# Statistic Serializer
class StatisticSerializer(serializers.ModelSerializer):
    """Serializer for Statistic model"""
    class Meta:
        model = Statistic
        fields = ['id', 'number', 'label']
        read_only_fields = ['id']

# PortfolioItem Serializer
class PortfolioItemSerializer(serializers.ModelSerializer):
    """Serializer for PortfolioItem model"""
    class Meta:
        model = PortfolioItem
        fields = ['id', 'category', 'title', 'client', 'year', 'image']
        read_only_fields = ['id']

# Service Serializer
class ServiceSerializer(serializers.ModelSerializer):
    """Serializer for Service model"""
    class Meta:
        model = Service
        fields = ['id', 'icon', 'title', 'description']
        read_only_fields = ['id']

# Testimonial Serializer
class TestimonialSerializer(serializers.ModelSerializer):
    """Serializer for Testimonial model"""
    class Meta:
        model = Testimonial
        fields = ['id', 'text', 'author', 'position', 'avatar']
        read_only_fields = ['id']

# Client Serializer
class ClientSerializer(serializers.ModelSerializer):
    """Serializer for Client model"""
    class Meta:
        model = Client
        fields = ['id', 'name']
        read_only_fields = ['id']

# Slide1 Serializers
class Slide1Serializer(serializers.ModelSerializer):
    """Serializer for creating/updating Slide1"""
    class Meta:
        model = Slide1
        fields = ['id', 'image1', 'image2', 'image3']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return Slide1.objects.create(**validated_data)

class Slide1DetailSerializer(serializers.ModelSerializer):
    """Serializer for reading Slide1 with user details"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Slide1
        fields = ['id', 'user', 'image1', 'image2', 'image3']
        read_only_fields = fields

# Slide2 Serializers
class Slide2Serializer(serializers.ModelSerializer):
    """Serializer for creating/updating Slide2"""
    class Meta:
        model = Slide2
        fields = ['id', 'image1', 'image2', 'image3']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return Slide2.objects.create(**validated_data)

class Slide2DetailSerializer(serializers.ModelSerializer):
    """Serializer for reading Slide2 with user details"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Slide2
        fields = ['id', 'user', 'image1', 'image2', 'image3']
        read_only_fields = fields




from rest_framework import serializers
from .models import Architecture

class ArchitectureSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Architecture
        fields = [
            'id', 'name', 'institution_type', 'parent', 'parent_name',
            'department_name', 'class_name', 'division', 'student_count',
            'staff_count', 'status', 'status_display', 'is_active',
            'custm_sent_to_admin', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']





# registration_serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()

class RegistrationInitSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    college_company = serializers.CharField(max_length=255)
    address = serializers.CharField()
    role = serializers.CharField(max_length=50, default='customer')
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "User with this email already exists"})
        
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already taken"})
        
        return data

class RegistrationOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    
    def validate(self, data):
        email = data.get('email')
        
        # Get registration data from cache
        cache_key = f"registration_data_{email}"
        registration_data = cache.get(cache_key)
        
        if not registration_data:
            raise serializers.ValidationError("Registration session expired. Please start over.")
        
        data['registration_data'] = registration_data
        return data

class RegistrationOTPResendSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        
        # Check if there's active registration data
        cache_key = f"registration_data_{value}"
        if not cache.get(cache_key):
            raise serializers.ValidationError("No active registration found. Please start over.")
        
        return value
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        
        # Check if there's active registration data
        cache_key = f"registration_data_{value}"
        if not cache.get(cache_key):
            raise serializers.ValidationError("No active registration found. Please start over.")
        
        return value




from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    is_approved = serializers.BooleanField()
    date_joined = serializers.DateTimeField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'full_name',
            'phone_number',
            'college_company',
            'address',
            'role',
            'is_approved',
            'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_full_name(self, obj):
        # If you have separate first_name and last_name fields
        if hasattr(obj, 'first_name') and hasattr(obj, 'last_name'):
            if obj.first_name and obj.last_name:
                return f"{obj.first_name} {obj.last_name}"
            elif obj.first_name:
                return obj.first_name
            elif obj.last_name:
                return obj.last_name
        
        # If you have a direct full_name field
        if hasattr(obj, 'full_name') and obj.full_name:
            return obj.full_name
            
        # Fallback to username
        return obj.username