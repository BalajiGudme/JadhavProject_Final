

# Add these imports at the top
from rest_framework import generics, permissions,viewsets ,status
from rest_framework.decorators import api_view, permission_classes,action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    UserSerializer, RegisterSerializer, 
    CustomTokenObtainPairSerializer, AdminTokenObtainPairSerializer ,
)



from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth.models import User
import base64
from django.core.files.base import ContentFile
from rest_framework.views import APIView
import qrcode
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from django.http import HttpResponse

from .models import Form, FormField, FormSubmission, FieldResponse, Architecture, FormToken
from .serializers import (
    FormSerializer, FormFieldSerializer, FormSubmissionSerializer, 
    FormSubmissionCreateSerializer, ArchitectureSerializer,
    ArchitectureCreateSerializer, ArchitectureTreeSerializer,
    FormTokenSerializer, FormTokenCreateSerializer, TokenValidationSerializer,
    QRCodeGenerationSerializer, ArchitectureStatisticsSerializer
)
User = get_user_model()

# Registration View
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

# List Users (Admin only)
class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        # Exclude admin/superuser/staff
        return User.objects.filter(is_superuser=False, is_staff=False)

# Pending users (only non-admins)
@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def pending_users(request):
    users = User.objects.filter(
        is_approved=False, is_superuser=False, is_staff=False
    )
    return Response({
        "count": users.count(),
        "users": UserSerializer(users, many=True).data
    })

# Approve user (only if not admin)
@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def approve_user(request, user_id):
    try:
        user = User.objects.get(
            id=user_id, is_superuser=False, is_staff=False
        )
        user.is_approved = True
        user.save()
        return Response({"message": "User approved successfully"})
    except User.DoesNotExist:
        return Response({"error": "User not found or cannot approve admin"}, status=404)

# Reject user (only if not admin)
@api_view(["DELETE"])
@permission_classes([permissions.IsAdminUser])
def reject_user(request, user_id):
    try:
        user = User.objects.get(
            id=user_id, is_superuser=False, is_staff=False
        )
        user.delete()
        return Response({"message": "User rejected and deleted"})
    except User.DoesNotExist:
        return Response({"error": "User not found or cannot reject admin"}, status=404)

# JWT Token Views
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class AdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer




# class FormViewSet(viewsets.ModelViewSet):
#     serializer_class = FormSerializer
#     permission_classes = [permissions.AllowAny]
#     queryset = Form.objects.all()
    
#     def perform_create(self, serializer):
#         serializer.save()
    
#     @action(detail=True, methods=['post'])
#     def publish(self, request, pk=None):
#         form = self.get_object()
#         form.is_published = True
#         form.save()
#         return Response({'status': 'form published'})
    
#     @action(detail=True, methods=['post'])
#     def unpublish(self, request, pk=None):
#         form = self.get_object()
#         form.is_published = False
#         form.save()
#         return Response({'status': 'form unpublished'})
    
#     @action(detail=False, methods=['get'])
#     def by_architecture(self, request):
#         """Get forms for a specific architecture"""
#         architecture_id = request.query_params.get('architecture_id')
#         if not architecture_id:
#             return Response(
#                 {'error': 'architecture_id parameter is required'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             architecture = Architecture.objects.get(id=architecture_id)
#             forms = Form.objects.filter(architecture=architecture, is_active=True)
#             serializer = FormSerializer(forms, many=True)
#             return Response(serializer.data)
#         except Architecture.DoesNotExist:
#             return Response(
#                 {'error': 'Architecture not found'},
#                 status=status.HTTP_404_NOT_FOUND
#             )

class FormViewSet(viewsets.ModelViewSet):
    serializer_class = FormSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Form.objects.all()
    
    def get_queryset(self):
        """Return only the forms belonging to the current user"""
        return Form.objects.filter(created_by=self.request.user)
    
    def perform_create(self, serializer):
        """Automatically assign the current user to the form"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        form = self.get_object()
        form.is_published = True
        form.save()
        return Response({'status': 'form published'})
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        form = self.get_object()
        form.is_published = False
        form.save()
        return Response({'status': 'form unpublished'})
    
    @action(detail=False, methods=['get'])
    def by_architecture(self, request):
        """Get forms for a specific architecture - only user's forms"""
        architecture_id = request.query_params.get('architecture_id')
        if not architecture_id:
            return Response(
                {'error': 'architecture_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            architecture = Architecture.objects.get(id=architecture_id)
            # Use get_queryset() to ensure user filtering is applied
            forms = self.get_queryset().filter(
                architecture=architecture, 
                is_active=True
            )
            
            # Check if forms exist
            if not forms.exists():
                return Response(
                    {'message': 'You have not created any forms for this architecture yet'},
                    status=status.HTTP_200_OK
                )
            
            serializer = FormSerializer(forms, many=True)
            return Response(serializer.data)
            
        except Architecture.DoesNotExist:
            return Response(
                {'error': 'Architecture not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class FormFieldViewSet(viewsets.ModelViewSet):
    serializer_class = FormFieldSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = FormField.objects.all()
    
    def perform_create(self, serializer):
        form_id = self.request.data.get('form')
        form = get_object_or_404(Form, id=form_id)
        serializer.save(form=form)
from rest_framework.decorators import action
from rest_framework import permissions

class FormTokenViewSet(viewsets.ModelViewSet):
    serializer_class = FormTokenSerializer
    permission_classes = [permissions.AllowAny]
    queryset = FormToken.objects.all()
    
    # @action(detail=False, methods=['post'])
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])# ----------------------------------------------========================================================20-10-2025
    def generate_multiple(self, request):
        """Generate multiple tokens at once"""
        serializer = FormTokenCreateSerializer(data=request.data)
        if serializer.is_valid():
            tokens = serializer.save()
            token_serializer = FormTokenSerializer(tokens, many=True)
            return Response(token_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=False, methods=['post'])
    def validate_token(self, request):
        """Validate a token before form submission"""
        serializer = TokenValidationSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token_instance']
            
            # Get form fields along with the form
            form = token.form
            fields = form.fields.all().values(
                'id', 'label', 'field_type', 'is_required', 'options', 'placeholder', 'order', 'is_active', 'is_unique'
            )
            
            # Convert options from JSON string to dict if it's a string
            for field in fields:
                if isinstance(field['options'], str):
                    try:
                        field['options'] = json.loads(field['options'])
                    except json.JSONDecodeError:
                        field['options'] = {}
            
            # Prepare response data with only available fields
            response_data = {
                'valid': True,
                'token': token.token,
                'is_used': token.is_used,
                'form': {
                    'id': form.id,
                    'title': form.title,
                    'fields': list(fields)
                }
            }
            
            # Only include architecture if it exists in the model
            if hasattr(token, 'architecture') and token.architecture:
                response_data['architecture_name'] = token.architecture.name
            
            return Response(response_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def submit_form(self, request):
        """Handle form submission with token"""
        try:
            data = request.data
            token_value = data.get('token')
            
            if not token_value:
                return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate token
            try:
                token = FormToken.objects.get(token=token_value)
            except FormToken.DoesNotExist:
                return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
            
            if token.is_used:
                return Response({'error': 'Token has already been used'}, status=status.HTTP_400_BAD_REQUEST)
            
            responses = data.get('responses', [])
            
            if not responses:
                return Response({'error': 'No form responses provided'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create form response
            form_response = FormResponse.objects.create(
                form=token.form,
                token=token
            )
            
            # Process each field response
            for response_data in responses:
                field_id = response_data.get('field_id')
                value = response_data.get('value')
                
                if not field_id:
                    continue
                
                try:
                    field = token.form.fields.get(id=field_id)
                except:
                    continue
                
                # Handle image fields
                if field.field_type == 'image' and value and isinstance(value, str) and value.startswith('data:image'):
                    # Process base64 image
                    format, imgstr = value.split(';base64,')
                    ext = format.split('/')[-1]
                    
                    # Create file name
                    file_name = f"{token.token}_{field_id}.{ext}"
                    
                    # Save image file
                    image_data = ContentFile(base64.b64decode(imgstr), name=file_name)
                    
                    FieldResponse.objects.create(
                        form_response=form_response,
                        field=field,
                        value=file_name,  # Store file name
                        file=image_data   # Store actual file
                    )
                else:
                    # For non-image fields
                    FieldResponse.objects.create(
                        form_response=form_response,
                        field=field,
                        value=value
                    )
            
            # Mark token as used
            token.is_used = True
            token.save()
            
            return Response({
                'success': True,
                'message': 'Form submitted successfully'
            })
            
        except Exception as e:
            return Response({'error': f'Failed to submit form: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(detail=False, methods=['get'])
    def by_architecture(self, request):
        """Get tokens for a specific architecture"""
        architecture_id = request.query_params.get('architecture_id')
        if not architecture_id:
            return Response(
                {'error': 'architecture_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            architecture = Architecture.objects.get(id=architecture_id)
            tokens = FormToken.objects.filter(architecture=architecture)
            serializer = FormTokenSerializer(tokens, many=True)
            return Response(serializer.data)
        except Architecture.DoesNotExist:
            return Response(
                {'error': 'Architecture not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class QRCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Generate QR codes as PDF"""
        serializer = QRCodeGenerationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        form_id = serializer.validated_data['form_id']
        count = serializer.validated_data['count']
        architecture_id = serializer.validated_data['architecture_id']
        
        try:
            form = Form.objects.get(id=form_id)
            architecture = Architecture.objects.get(id=architecture_id)
        except (Form.DoesNotExist, Architecture.DoesNotExist):
            return Response(
                {'error': 'Form or Architecture not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create tokens
        tokens = []
        for _ in range(count):
            token = FormToken.objects.create(form=form, architecture=architecture)
            tokens.append(token)
        
        # Generate PDF with QR codes
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="qr_codes_{form.title}.pdf"'
        
        # Create PDF
        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter
        
        # Set up layout - 3 columns, 8 rows
        cols = 3
        rows = 8
        col_width = width / cols
        row_height = height / rows
        
        for i, token in enumerate(tokens):
            if i > 0 and i % (cols * rows) == 0:
                p.showPage()  # New page
            
            col = i % cols
            row = (i // cols) % rows
            
            x = col * col_width + col_width / 2
            y = height - (row * row_height) - row_height / 2
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(token.token)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Draw QR code on PDF
            p.drawImage(io.BytesIO(img_buffer.getvalue()), 
                       x - 0.8 * inch, 
                       y - 0.8 * inch, 
                       width=1.6 * inch, 
                       height=1.6 * inch)
            
            # Draw token text
            p.setFont("Helvetica", 12)
            p.drawCentredString(x, y - 1 * inch, f"Token: {token.token}")
            p.drawCentredString(x, y - 1.2 * inch, f"Form: {form.title}")
        
        p.save()
        return response

class PublicFormViewSet(viewsets.ModelViewSet):
    serializer_class = FormSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Form.objects.filter(is_active=True, is_published=True)
    
    http_method_names = ['get', 'post', 'head', 'options']
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        form = self.get_object()
        
        if not form.is_active or not form.is_published:
            return Response(
                {'error': 'This form is not currently accepting submissions'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if token is required and validate it
        token_value = request.data.get('token')
        if token_value:
            try:
                token = FormToken.objects.get(token=token_value, form=form)
                if token.is_used:
                    return Response(
                        {'error': 'This token has already been used'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except FormToken.DoesNotExist:
                return Response(
                    {'error': 'Invalid token for this form'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif form.is_unique:
            return Response(
                {'error': 'Token is required for this form'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if 'responses' in request.data:
                responses_data = request.data.get('responses', [])
            else:
                responses_data = []
                for key, value in request.data.items():
                    if key == 'token':
                        continue
                    try:
                        field_id = int(key)
                        responses_data.append({'field_id': field_id, 'value': value})
                    except (ValueError, TypeError):
                        continue
            
            if not responses_data:
                return Response(
                    {'error': 'No valid responses provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Create submission with token if provided
                submission_data = {'form': form}
                if token_value:
                    token = FormToken.objects.get(token=token_value, form=form)
                    submission_data['token'] = token
                
                submission = FormSubmission.objects.create(**submission_data)
                
                for response_data in responses_data:
                    field_id = response_data.get('field_id')
                    value = response_data.get('value')
                    
                    if field_id is None or value is None:
                        continue
                    
                    try:
                        field = FormField.objects.get(id=field_id, form=form, is_active=True)
                    except FormField.DoesNotExist:
                        continue
                    
                    if field.field_type == 'text':
                        FieldResponse.objects.create(
                            submission=submission,
                            field=field,
                            value_text=str(value)
                        )
                    elif field.field_type == 'number':
                        try:
                            numeric_value = float(value)
                            FieldResponse.objects.create(
                                submission=submission,
                                field=field,
                                value_number=numeric_value
                            )
                        except (ValueError, TypeError):
                            continue
                    elif field.field_type == 'date':
                        FieldResponse.objects.create(
                            submission=submission,
                            field=field,
                            value_date=value
                        )
                    elif field.field_type == 'checkbox':
                        if isinstance(value, str):
                            bool_value = value.lower() in ['true', '1', 'yes', 'on']
                        else:
                            bool_value = bool(value)
                        
                        FieldResponse.objects.create(
                            submission=submission,
                            field=field,
                            value_boolean=bool_value
                        )
                    elif field.field_type == 'alphanumeric':
                        FieldResponse.objects.create(
                            submission=submission,
                            field=field,
                            value_alphanumeric=str(value)
                        )
                    elif field.field_type == 'image' and isinstance(value, str) and value.startswith('data:image'):
                        try:
                            format, imgstr = value.split(';base64,')
                            ext = format.split('/')[-1]
                            image_data = ContentFile(base64.b64decode(imgstr), name=f'image_{field_id}.{ext}')
                            
                            FieldResponse.objects.create(
                                submission=submission,
                                field=field,
                                value_image=image_data
                            )
                        except Exception as img_error:
                            print(f"Image processing error: {img_error}")
                            continue
                    elif field.field_type == 'dropdown':
                        FieldResponse.objects.create(
                            submission=submission,
                            field=field,
                            value_text=str(value)
                        )
                
                return Response(
                    {
                        'status': 'submission successful',
                        'submission_id': submission.id,
                        'message': 'Form submitted successfully!'
                    },
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            print(f"Submission error: {str(e)}")
            return Response(
                {'error': f'Submission failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

class FormSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FormSubmissionSerializer
    permission_classes = [permissions.AllowAny]
    queryset = FormSubmission.objects.all()
    
    @action(detail=False, methods=['get'])
    def by_token(self, request):
        """Get submission by token"""
        token = request.query_params.get('token')
        if not token:
            return Response(
                {'error': 'token parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            submission = FormSubmission.objects.get(token__token=token)
            serializer = FormSubmissionSerializer(submission)
            return Response(serializer.data)
        except FormSubmission.DoesNotExist:
            return Response(
                {'error': 'Submission not found for this token'},
                status=status.HTTP_404_NOT_FOUND
            )
#
class FormSubmitView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, pk):
        try:
            form = Form.objects.get(id=pk, is_active=True, is_published=True)
        except Form.DoesNotExist:
            return Response(
                {'error': 'Form not found or not accepting submissions'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Copy submit logic from PublicFormViewSet.submit method
        viewset = PublicFormViewSet()
        viewset.action = 'submit'
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': pk}
        return viewset.submit(request, pk)

# Architecture Views
# class ArchitectureViewSet(viewsets.ModelViewSet):
#     serializer_class = ArchitectureSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     queryset = Architecture.objects.all()
    
#     def get_serializer_class(self):
#         if self.action in ['create', 'update', 'partial_update']:
#             return ArchitectureCreateSerializer
#         return ArchitectureSerializer
    
#     def perform_create(self, serializer):
#         # Handle both authenticated and anonymous users
#         if self.request.user.is_authenticated:
#             serializer.save(created_by=self.request.user)
#         else:
#             # Save without the created_by field for anonymous users
#             serializer.save()
    
#     def perform_update(self, serializer):
#         # Similar handling for updates if needed
#         if self.request.user.is_authenticated:
#             serializer.save(updated_by=self.request.user)
#         else:
#             serializer.save()
    
#     @action(detail=False, methods=['get'])
#     def tree(self, request):
#         """Get the full architecture tree"""
#         root_nodes = Architecture.objects.filter(parent__isnull=True)
#         serializer = ArchitectureTreeSerializer(root_nodes, many=True)
#         return Response(serializer.data)
    
#     @action(detail=True, methods=['get'])
#     def children(self, request, pk=None):
#         """Get children of a specific architecture node"""
#         architecture = self.get_object()
#         children = architecture.children.all()
#         serializer = ArchitectureSerializer(children, many=True)
#         return Response(serializer.data)
    
#     @action(detail=True, methods=['get'])
#     def hierarchy(self, request, pk=None):
#         """Get the full hierarchy path for a node"""
#         architecture = self.get_object()
#         return Response({'hierarchy': architecture.get_full_hierarchy()})
    
#     @action(detail=True, methods=['get'])
#     def statistics(self, request, pk=None):
#         """Get statistics for a node and its children"""
#         architecture = self.get_object()
#         serializer = ArchitectureStatisticsSerializer(architecture)
#         return Response(serializer.data)
    
#     @action(detail=True, methods=['get'])
#     def forms(self, request, pk=None):
#         """Get forms associated with this architecture"""
#         architecture = self.get_object()
#         forms = Form.objects.filter(architecture=architecture, is_active=True)
#         serializer = FormSerializer(forms, many=True)
#         return Response(serializer.data)
    
#     @action(detail=True, methods=['get'])
#     def tokens(self, request, pk=None):
#         """Get tokens associated with this architecture"""
#         architecture = self.get_object()
#         tokens = FormToken.objects.filter(architecture=architecture)
#         serializer = FormTokenSerializer(tokens, many=True)
#         return Response(serializer.data)
#20-10-2025--======================================================--------------
class ArchitectureViewSet(viewsets.ModelViewSet):
    serializer_class = ArchitectureSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # def get_queryset(self):
    #     """
    #     This view should return a list of all architectures
    #     created by the currently authenticated user.
    #     """
    #     return Architecture.objects.filter(created_by=self.request.user)

    def get_queryset(self):
        return Architecture.objects.filter(created_by=self.request.user)
        
      
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ArchitectureCreateSerializer
        return ArchitectureSerializer
    
    def perform_create(self, serializer):
        # Always save with the authenticated user
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        # Always save with the authenticated user for updates
        serializer.save(updated_by=self.request.user)
    def get_object(self):
        """
        Override get_object to first try direct lookup, then fall back to queryset
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Try to get the object using the queryset first (respects filtering)
        try:
            obj = queryset.get(pk=self.kwargs['pk'])
            return obj
        except Architecture.DoesNotExist:
            # If not found in filtered queryset, try direct lookup for debugging
            try:
                obj = Architecture.objects.get(pk=self.kwargs['pk'])
                # If we found it but it's not in queryset, user doesn't own it
                print(f"Architecture {self.kwargs['pk']} exists but is owned by {obj.created_by_id}, not by {self.request.user.id}")
                raise
            except Architecture.DoesNotExist:
                raise
        
        self.check_object_permissions(self.request, obj)
        return obj
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get the full architecture tree for the current user"""
        root_nodes = Architecture.objects.filter(
            parent__isnull=True, 
            created_by=self.request.user
        )
        serializer = ArchitectureTreeSerializer(root_nodes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """Get children of a specific architecture node (only user's data)"""
        architecture = self.get_object()  # This will automatically check ownership via get_queryset
        children = architecture.children.filter(created_by=self.request.user)
        serializer = ArchitectureSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def hierarchy(self, request, pk=None):
        """Get the full hierarchy path for a node (only user's data)"""
        architecture = self.get_object()  # This will automatically check ownership via get_queryset
        return Response({'hierarchy': architecture.get_full_hierarchy()})
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a node and its children (only user's data)"""
        architecture = self.get_object()  # This will automatically check ownership via get_queryset
        serializer = ArchitectureStatisticsSerializer(architecture)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def forms(self, request, pk=None):
        """Get forms associated with this architecture (only user's data)"""
        architecture = self.get_object()  # This will automatically check ownership via get_queryset
        forms = Form.objects.filter(
            architecture=architecture, 
            is_active=True,
            created_by=self.request.user  # Add this filter if forms also have user ownership
        )
        serializer = FormSerializer(forms, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tokens(self, request, pk=None):
        """Get tokens associated with this architecture (only user's data)"""
        architecture = self.get_object()  # This will automatically check ownership via get_queryset
        tokens = FormToken.objects.filter(
            architecture=architecture,
            created_by=self.request.user  # Add this filter if tokens also have user ownership
        )
        serializer = FormTokenSerializer(tokens, many=True)
        return Response(serializer.data)
# class ArchitectureTreeView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
    
#     def get(self, request):
#         """Get the complete architecture tree structure"""
#         root_nodes = Architecture.objects.filter(parent__isnull=True)
#         serializer = ArchitectureTreeSerializer(root_nodes, many=True)
#         return Response(serializer.data)
class ArchitectureTreeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get the complete architecture tree structure for the current user"""
        root_nodes = Architecture.objects.filter(
            parent__isnull=True, 
            created_by=request.user
        )
        serializer = ArchitectureTreeSerializer(root_nodes, many=True)
        return Response(serializer.data)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import FormSubmission, FormToken, FormField, FieldResponse



class SubmitFormByTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        try:
            token = request.data.get('token')
            responses = request.data.get('responses', [])
            
            # print("=== FORM SUBMISSION DEBUG ===")
            # print("Token:", token)
            # print("Number of responses:", len(responses))
            # print("All responses:", responses)
            
            # Validate token
            if not token:
                return Response(
                    {"error": "Token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                form_token = FormToken.objects.get(token=token, is_used=False)
                print(f"Found valid token for form: {form_token.form.title}")
            except FormToken.DoesNotExist:
                print("❌ Invalid or already used token")
                return Response(
                    {"error": "Invalid or already used token"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get all fields for this form
            form_fields = FormField.objects.filter(form=form_token.form)
            print(f"Expected fields for this form: {[(f.id, f.label, f.field_type, f.is_required, f.is_unique) for f in form_fields]}")
            
            # Create a dictionary of submitted responses by field_id for easy lookup
            submitted_responses = {}
            for response in responses:
                field_id = response.get('field_id')
                value = response.get('value')
                if field_id is not None:
                    try:
                        submitted_responses[int(field_id)] = value
                    except (ValueError, TypeError):
                        pass  # Skip invalid field_id
            
            # VALIDATE REQUIRED FIELDS
            missing_required_fields = []
            empty_required_fields = []
            
            for field in form_fields:
                if field.is_required:
                    # Check if field exists in submission
                    if field.id not in submitted_responses:
                        missing_required_fields.append({
                            'field_id': field.id,
                            'field_name': field.label,
                            'message': f'Field "{field.label}" is required but was not submitted'
                        })
                    else:
                        # Check if value is empty based on field type
                        value = submitted_responses[field.id]
                        
                        # Handle different types of empty values
                        is_empty = False
                        
                        if value is None:
                            is_empty = True
                        elif isinstance(value, str) and value.strip() == '':
                            is_empty = True
                        elif isinstance(value, list) and len(value) == 0:  # For checkboxes or multi-select
                            is_empty = True
                        elif isinstance(value, dict) and not value:  # For empty JSON
                            is_empty = True
                        
                        if is_empty:
                            empty_required_fields.append({
                                'field_id': field.id,
                                'field_name': field.label,
                                'message': f'Field "{field.label}" is required and cannot be empty'
                            })
            
            # If there are missing or empty required fields, return error
            if missing_required_fields or empty_required_fields:
                return Response({
                    "error": "Validation failed",
                    "missing_fields": missing_required_fields,
                    "empty_fields": empty_required_fields
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # VALIDATE UNIQUE FIELDS
            unique_field_errors = []
            
            for field in form_fields:
                if field.is_unique and field.id in submitted_responses:
                    value = submitted_responses[field.id]
                    
                    # Skip validation for empty values on unique fields
                    if value in [None, '', []]:
                        continue
                    
                    # Check if this value already exists for this field in any submission
                    existing_responses = FieldResponse.objects.filter(
                        field=field,
                        submission__form=form_token.form
                    )
                    
                    # Check based on field type
                    exists = False
                    
                    if field.field_type == 'text':
                        exists = existing_responses.filter(value_text=value).exists()
                    elif field.field_type == 'email':
                        exists = existing_responses.filter(value_email=value).exists()
                    elif field.field_type == 'phonenumber':
                        # Normalize phone number before checking (remove special characters)
                        normalized_value = self.normalize_phone_number(value)
                        # Check both original and normalized versions in value_phonenumber
                        exists = existing_responses.filter(value_phonenumber=value).exists() or \
                                 existing_responses.filter(value_phonenumber=normalized_value).exists()
                    elif field.field_type == 'number':
                        try:
                            numeric_value = float(value)
                            exists = existing_responses.filter(value_number=numeric_value).exists()
                        except (ValueError, TypeError):
                            exists = False  # Invalid number format, will be caught by validation
                    elif field.field_type == 'date':
                        exists = existing_responses.filter(value_date=value).exists()
                    elif field.field_type == 'checkbox':
                        # Checkbox values are usually boolean, uniqueness might not apply
                        pass
                    elif field.field_type == 'alphanumeric':
                        exists = existing_responses.filter(value_alphanumeric=value).exists()
                    else:
                        # For other field types, check value_text as fallback
                        exists = existing_responses.filter(value_text=str(value)).exists()
                    
                    if exists:
                        unique_field_errors.append({
                            'field_id': field.id,
                            'field_name': field.label,
                            'message': f'Field "{field.label}" must be unique. The value "{value}" already exists.'
                        })
            
            # If there are unique field violations, return error
            if unique_field_errors:
                return Response({
                    "error": "Unique field validation failed",
                    "unique_field_errors": unique_field_errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # VALIDATE FIELD TYPES
            type_validation_errors = []
            
            for field in form_fields:
                if field.id in submitted_responses:
                    value = submitted_responses[field.id]
                    
                    # Skip empty values (they're handled by required validation)
                    if value in [None, '', []]:
                        continue
                    
                    # Validate based on field type
                    if field.field_type == 'number':
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            type_validation_errors.append({
                                'field_id': field.id,
                                'field_name': field.label,
                                'message': f'Field "{field.label}" must be a valid number'
                            })
                    
                    elif field.field_type == 'email':
                        import re
                        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                        if not re.match(email_pattern, str(value).strip()):
                            type_validation_errors.append({
                                'field_id': field.id,
                                'field_name': field.label,
                                'message': f'Field "{field.label}" must be a valid email address'
                            })
                    
                    elif field.field_type == 'phonenumber':
                        import re
                        # Remove all non-digit characters for validation
                        phone_digits = re.sub(r'\D', '', str(value))
                        # Check if it has at least 10 digits (adjust based on your requirements)
                        if len(phone_digits) < 10 or len(phone_digits) > 15:
                            type_validation_errors.append({
                                'field_id': field.id,
                                'field_name': field.label,
                                'message': f'Field "{field.label}" must be a valid phone number with 10-15 digits'
                            })
                    
                    elif field.field_type == 'date':
                        # Simple date format validation (YYYY-MM-DD)
                        import re
                        if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(value)):
                            type_validation_errors.append({
                                'field_id': field.id,
                                'field_name': field.label,
                                'message': f'Field "{field.label}" must be a valid date in YYYY-MM-DD format'
                            })
                        else:
                            # Additional validation to ensure it's a real date
                            try:
                                from datetime import datetime
                                datetime.strptime(str(value), '%Y-%m-%d')
                            except ValueError:
                                type_validation_errors.append({
                                    'field_id': field.id,
                                    'field_name': field.label,
                                    'message': f'Field "{field.label}" must be a valid date'
                                })
                    
                    elif field.field_type == 'checkbox':
                        if not isinstance(value, bool) and str(value).lower() not in ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off']:
                            type_validation_errors.append({
                                'field_id': field.id,
                                'field_name': field.label,
                                'message': f'Field "{field.label}" must be a boolean value'
                            })
                    
                    elif field.field_type == 'image':
                        if not (isinstance(value, str) and value.startswith('data:image')):
                            type_validation_errors.append({
                                'field_id': field.id,
                                'field_name': field.label,
                                'message': f'Field "{field.label}" must be a valid base64 image'
                            })
            
            if type_validation_errors:
                return Response({
                    "error": "Field type validation failed",
                    "type_errors": type_validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # If all validations pass, create form submission
            submission = FormSubmission.objects.create(
                form=form_token.form,
                token=form_token
            )
            print(f"Created submission ID: {submission.id}")
            
            # Process each response
            saved_responses = []
            for i, response_data in enumerate(responses):
                field_id = response_data.get('field_id')
                value = response_data.get('value')
                
                print(f"Processing response {i+1}: field_id={field_id}, value={value}")
                
                if field_id is not None and value is not None:
                    try:
                        # Convert to integer if needed
                        field_id = int(field_id)
                        field = FormField.objects.get(id=field_id, form=form_token.form)
                        
                        print(f"Creating response for field: {field.label} (type: {field.field_type})")
                        
                        # Create FieldResponse instance
                        field_response = FieldResponse(
                            submission=submission,
                            field=field
                        )
                        
                        # Save value to the appropriate field based on field type
                        if field.field_type == 'text':
                            field_response.value_text = str(value)
                            
                        elif field.field_type == 'email':
                            field_response.value_email = str(value)
                            
                        elif field.field_type == 'phonenumber':
                            field_response.value_phonenumber = str(value)
                            
                        elif field.field_type == 'number':
                            try:
                                field_response.value_number = float(value)
                            except (ValueError, TypeError):
                                field_response.value_text = str(value)  # Fallback to text
                                
                        elif field.field_type == 'date':
                            field_response.value_date = value  # Should be in YYYY-MM-DD format
                            
                        elif field.field_type == 'checkbox':
                            # Convert various boolean representations
                            if isinstance(value, bool):
                                field_response.value_boolean = value
                            else:
                                str_value = str(value).lower()
                                field_response.value_boolean = str_value in ['true', '1', 'yes', 'on']
                                
                        elif field.field_type == 'image':
                            # Handle base64 image data
                            if isinstance(value, str) and value.startswith('data:image'):
                                try:
                                    format, imgstr = value.split(';base64,')
                                    ext = format.split('/')[-1]
                                    filename = f"submission_{submission.id}_field_{field.id}.{ext}"
                                    
                                    from django.core.files.base import ContentFile
                                    from base64 import b64decode
                                    
                                    data = ContentFile(b64decode(imgstr), name=filename)
                                    field_response.value_image.save(filename, data, save=False)
                                except Exception as img_error:
                                    print(f"Image processing error: {img_error}")
                                    field_response.value_text = "Image processing failed"
                            else:
                                field_response.value_text = str(value)
                                
                        elif field.field_type == 'dropdown':
                            field_response.value_text = str(value)  # Store dropdown as text
                            
                        elif field.field_type == 'alphanumeric':
                            field_response.value_alphanumeric = str(value)
                            
                        else:
                            field_response.value_text = str(value)  # Default fallback
                        
                        # Save the response
                        field_response.save()
                        
                        # Prepare response data (excluding sensitive or binary data)
                        response_value = value
                        if field.field_type == 'image' and field_response.value_image:
                            response_value = field_response.value_image.url if field_response.value_image else value
                        
                        saved_responses.append({
                            "field_id": field_id,
                            "field_name": field.label,
                            "field_type": field.field_type,
                            "value": response_value
                        })
                        
                        print(f"✅ Successfully saved {field.field_type} response for field {field_id}")
                        
                    except FormField.DoesNotExist:
                        print(f"❌ Field with ID {field_id} does not exist for this form")
                        # Don't fail the whole submission for invalid fields, just skip them
                        continue
                    except ValueError:
                        print(f"❌ Invalid field_id format: {field_id}")
                        continue
                    except Exception as e:
                        print(f"❌ Error saving response for field {field_id}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        # Continue with other fields instead of failing completely
                        continue
                else:
                    print(f"❌ Missing field_id or value in response {i+1}")
            
            # Mark token as used
            form_token.is_used = True
            form_token.save()
            
            print(f"Saved {len(saved_responses)} field responses")
            print("===========================")
            
            return Response({
                "success": True,
                "message": "Form submitted successfully!",
                "submission_id": submission.id,
                "saved_responses_count": len(saved_responses),
                "saved_responses": saved_responses
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print("❌ Submission error:", str(e))
            import traceback
            traceback.print_exc()
            return Response({
                "error": "Internal server error: " + str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def normalize_phone_number(self, phone):
        """Helper method to normalize phone numbers for comparison"""
        import re
        # Remove all non-digit characters
        return re.sub(r'\D', '', str(phone))

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import FormToken
# views.py
@api_view(['GET'])
def check_existing_tokens(request):
    form_id = request.GET.get('form_id')
    architecture_ids = request.GET.get('architecture_ids', '').split(',')
    
    if not form_id or not architecture_ids:
        return Response({'error': 'Missing parameters'}, status=400)
    
    # Filter tokens by form and architectures
    tokens = FormToken.objects.filter(
        form_id=form_id,
        architecture_id__in=architecture_ids
    ).select_related('form', 'architecture')
    
    # Serialize the tokens
    token_data = []
    for token in tokens:
        token_data.append({
            'id': token.id,
            'token': token.token,
            'form': token.form_id,
            'form_title': getattr(token.form, 'title', ''),
            'architecture': token.architecture_id,
            'architecture_name': getattr(token.architecture, 'name', ''),
            'is_valid': token.is_valid,
            'is_used': token.is_used,
            'created_at': token.created_at
        })
    
    return Response({
        'existing_tokens': token_data,
        'count': len(token_data)
    })

#---------------------------------------------main-------------------------------------------------------
from rest_framework import generics, status
from rest_framework.response import Response
from django.db.models import Prefetch
from .models import Architecture, FormSubmission, FormField, FieldResponse, FormToken
from .serializers import ArchitectureFieldResponseSerializer
import json

# class ArchitectureResponsesView(generics.ListAPIView):
#     """
#     Retrieve all field responses for a specific architecture ID
#     Includes both submitted responses and empty tokens for missing fields
#     """
#     serializer_class = ArchitectureFieldResponseSerializer

#     def get_queryset(self):
#         architecture_id = self.kwargs['architecture_id']
#         return FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id
#         ).select_related(
#             'field', 
#             'submission', 
#             'submission__token',
#             'submission__token__architecture'
#         ).only(
#             'id', 'field_id', 'value_text', 'value_number', 'value_date',
#             'value_boolean', 'value_alphanumeric', 'created_at',
#             'submission__id', 'submission__token__architecture_id',
#             'submission__token__architecture__name', 'submission__token__token',
#             'field__label', 'field__field_type', 'field__order', 'field__is_required'
#         )

#     def list(self, request, *args, **kwargs):
#         architecture_id = kwargs['architecture_id']
        
#         try:
#             # Check if architecture exists
#             architecture = Architecture.objects.get(id=architecture_id)
#         except Architecture.DoesNotExist:
#             return Response(
#                 {"error": "Architecture not found"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         # Get all tokens for this architecture
#         tokens = FormToken.objects.filter(architecture_id=architecture_id)
        
#         if not tokens.exists():
#             return Response(self.get_empty_responses(architecture))

#         # Get all form fields from all forms used in tokens
#         form_ids = tokens.values_list('form_id', flat=True).distinct()
#         all_form_fields = FormField.objects.filter(
#             form_id__in=form_ids, 
#             is_active=True
#         ).order_by('order').only(
#             'id', 'label', 'field_type', 'order', 'is_required', 'form_id'
#         )
        
#         # Get existing responses (exclude image fields from initial query)
#         existing_responses = FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id
#         ).exclude(field__field_type='image').select_related(
#             'field', 'submission', 'submission__token', 'submission__token__architecture'
#         )
        
#         # Handle image responses separately to avoid encoding issues
#         image_responses = FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id,
#             field__field_type='image'
#         ).select_related(
#             'field', 'submission', 'submission__token', 'submission__token__architecture'
#         )

#         # Create complete response data
#         response_data = self.prepare_complete_response_data(
#             architecture, tokens, all_form_fields, existing_responses, image_responses
#         )

#         return Response(response_data)

#     def get_empty_responses(self, architecture):
#         """Return empty response structure when no tokens exist"""
#         return {
#             'architecture_id': architecture.id,
#             'architecture_name': str(architecture),
#             'token_count': 0,
#             'submission_count': 0,
#             'tokens': [],
#             'submission_ids': [],
#             'responses': []
#         }

#     def prepare_complete_response_data(self, architecture, tokens, all_form_fields, existing_responses, image_responses):
#         """Prepare complete response data including empty tokens"""
        
#         # Get all submissions for these tokens
#         submissions = FormSubmission.objects.filter(token__in=tokens)
        
#         # Combine all responses
#         all_responses = list(existing_responses) + list(image_responses)
        
#         # Group responses by field for easy lookup
#         responses_by_field = {}
#         for response in all_responses:
#             field_id = response.field_id
#             if field_id not in responses_by_field:
#                 responses_by_field[field_id] = []
#             responses_by_field[field_id].append(response)

#         # Prepare response data
#         response_data = {
#             'architecture_id': architecture.id,
#             'architecture_name': str(architecture),
#             'token_count': tokens.count(),
#             'submission_count': submissions.count(),
#             'tokens': list(tokens.values_list('token', flat=True)),
#             'submission_ids': list(submissions.values_list('id', flat=True)),
#             'responses': []
#         }

#         for field in all_form_fields:
#             field_responses = responses_by_field.get(field.id, [])
            
#             if field_responses:
#                 # Serialize existing responses
#                 for response in field_responses:
#                     try:
#                         serializer = self.get_serializer(response, context={'request': self.request})
#                         response_data['responses'].append(serializer.data)
#                     except (UnicodeDecodeError, ValueError) as e:
#                         # Handle problematic responses gracefully
#                         error_response = {
#                             'id': response.id,
#                             'submission_id': response.submission.id if response.submission else None,
#                             'architecture_id': architecture.id,
#                             'architecture_name': str(architecture),
#                             'token': response.submission.token.token if response.submission and response.submission.token else None,
#                             'field': field.id,
#                             'field_label': field.label,
#                             'field_type': field.field_type,
#                             'field_order': field.order,
#                             'field_required': field.is_required,
#                             'value': f"Error: Could not decode value for {field.field_type} field",
#                             'created_at': response.created_at.isoformat() if response.created_at else None
#                         }
#                         response_data['responses'].append(error_response)
#             else:
#                 # Create empty token for missing field
#                 empty_response_data = {
#                     'id': None,
#                     'submission_id': None,
#                     'architecture_id': architecture.id,
#                     'architecture_name': str(architecture),
#                     'token': None,
#                     'field': field.id,
#                     'field_label': field.label,
#                     'field_type': field.field_type,
#                     'field_order': field.order,
#                     'field_required': field.is_required,
#                     'value': None,
#                     'created_at': None
#                 }
#                 response_data['responses'].append(empty_response_data)

#         return response_data

#==-------- above code is old code -=========================================================19-10-2025++++++++++++++++++++++=================---------=========================
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication 

# class ArchitectureResponsesView(generics.ListAPIView):
#     """
#     Retrieve all field responses for a specific architecture ID
#     Includes both submitted responses and empty tokens for missing fields
#     Accessible by architecture owner and admin users
#     """
#     serializer_class = ArchitectureFieldResponseSerializer
#     authentication_classes = [JWTAuthentication, SessionAuthentication, TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         architecture_id = self.kwargs['architecture_id']
#         user = self.request.user
        
#         # Base queryset - admin users can see all, regular users only their own
#         if user.is_staff or user.is_superuser:
#             # Admin users can access all responses
#             return FieldResponse.objects.filter(
#                 submission__token__architecture_id=architecture_id
#             ).select_related(
#                 'field', 
#                 'submission', 
#                 'submission__token',
#                 'submission__token__architecture'
#             ).only(
#                 'id', 'field_id', 'value_text', 'value_number', 'value_date',
#                 'value_boolean', 'value_alphanumeric', 'created_at',
#                 'submission__id', 'submission__token__architecture_id',
#                 'submission__token__architecture__name', 'submission__token__token',
#                 'field__label', 'field__field_type', 'field__order', 'field__is_required'
#             )
#         else:
#             # Regular users can only access their own architectures
#             return FieldResponse.objects.filter(
#                 submission__token__architecture_id=architecture_id,
#                 submission__token__architecture__created_by=user
#             ).select_related(
#                 'field', 
#                 'submission', 
#                 'submission__token',
#                 'submission__token__architecture'
#             ).only(
#                 'id', 'field_id', 'value_text', 'value_number', 'value_date',
#                 'value_boolean', 'value_alphanumeric', 'created_at',
#                 'submission__id', 'submission__token__architecture_id',
#                 'submission__token__architecture__name', 'submission__token__token',
#                 'field__label', 'field__field_type', 'field__order', 'field__is_required'
#             )

#     def has_permission_to_access_architecture(self, architecture_id, user):
#         """
#         Check if user has permission to access this architecture
#         Returns architecture object if user has permission, None otherwise
#         """
#         try:
#             if user.is_staff or user.is_superuser:
#                 # Admin users can access any architecture
#                 return Architecture.objects.get(id=architecture_id)
#             else:
#                 # Regular users can only access their own architectures
#                 return Architecture.objects.get(id=architecture_id, created_by=user)
#         except Architecture.DoesNotExist:
#             return None

#     def list(self, request, *args, **kwargs):
#         # Debug information to help troubleshoot
#         print(f"User: {request.user}")
#         print(f"User authenticated: {request.user.is_authenticated}")
#         print(f"User is active: {request.user.is_active}")
#         print(f"User is staff: {request.user.is_staff}")
#         print(f"User is superuser: {request.user.is_superuser}")
#         print(f"User groups: {[group.name for group in request.user.groups.all()]}")
        
#         # Check if user is authenticated (should be handled by permission_classes, but double-check)
#         if not request.user.is_authenticated:
#             return Response(
#                 {"error": "Authentication required"}, 
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
        
#         architecture_id = kwargs['architecture_id']
#         user = request.user
        
#         # Check if user has permission to access this architecture
#         architecture = self.has_permission_to_access_architecture(architecture_id, user)
#         if not architecture:
#             return Response(
#                 {"error": "Architecture not found or you don't have permission to access it"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         # Get all tokens for this architecture
#         # For admin users, get all tokens; for regular users, this is already filtered by ownership
#         if user.is_staff or user.is_superuser:
#             tokens = FormToken.objects.filter(architecture_id=architecture_id)
#         else:
#             tokens = FormToken.objects.filter(architecture_id=architecture_id)
        
#         if not tokens.exists():
#             return Response(self.get_empty_responses(architecture))

#         # Get all form fields from all forms used in tokens
#         form_ids = tokens.values_list('form_id', flat=True).distinct()
#         all_form_fields = FormField.objects.filter(
#             form_id__in=form_ids, 
#             is_active=True
#         ).order_by('order').only(
#             'id', 'label', 'field_type', 'order', 'is_required', 'form_id'
#         )
        
#         # Get existing responses (exclude image fields from initial query)
#         # Use the appropriate queryset based on user role
#         if user.is_staff or user.is_superuser:
#             existing_responses = FieldResponse.objects.filter(
#                 submission__token__architecture_id=architecture_id
#             ).exclude(field__field_type='image').select_related(
#                 'field', 'submission', 'submission__token', 'submission__token__architecture'
#             )
            
#             image_responses = FieldResponse.objects.filter(
#                 submission__token__architecture_id=architecture_id,
#                 field__field_type='image'
#             ).select_related(
#                 'field', 'submission', 'submission__token', 'submission__token__architecture'
#             )
#         else:
#             existing_responses = FieldResponse.objects.filter(
#                 submission__token__architecture_id=architecture_id,
#                 submission__token__architecture__created_by=user
#             ).exclude(field__field_type='image').select_related(
#                 'field', 'submission', 'submission__token', 'submission__token__architecture'
#             )
            
#             image_responses = FieldResponse.objects.filter(
#                 submission__token__architecture_id=architecture_id,
#                 submission__token__architecture__created_by=user,
#                 field__field_type='image'
#             ).select_related(
#                 'field', 'submission', 'submission__token', 'submission__token__architecture'
#             )

#         # Create complete response data
#         response_data = self.prepare_complete_response_data(
#             architecture, tokens, all_form_fields, existing_responses, image_responses
#         )

#         return Response(response_data)

#     def get_empty_responses(self, architecture):
#         """Return empty response structure when no tokens exist"""
#         return {
#             'architecture_id': architecture.id,
#             'architecture_name': str(architecture),
#             'token_count': 0,
#             'submission_count': 0,
#             'tokens': [],
#             'submission_ids': [],
#             'responses': []
#         }

#     def prepare_complete_response_data(self, architecture, tokens, all_form_fields, existing_responses, image_responses):
#         """Prepare complete response data including empty tokens"""
        
#         # Get all submissions for these tokens
#         submissions = FormSubmission.objects.filter(token__in=tokens)
        
#         # Combine all responses
#         all_responses = list(existing_responses) + list(image_responses)
        
#         # Group responses by field for easy lookup
#         responses_by_field = {}
#         for response in all_responses:
#             field_id = response.field_id
#             if field_id not in responses_by_field:
#                 responses_by_field[field_id] = []
#             responses_by_field[field_id].append(response)

#         # Prepare response data
#         response_data = {
#             'architecture_id': architecture.id,
#             'architecture_name': str(architecture),
#             'token_count': tokens.count(),
#             'submission_count': submissions.count(),
#             'tokens': list(tokens.values_list('token', flat=True)),
#             'submission_ids': list(submissions.values_list('id', flat=True)),
#             'responses': []
#         }

#         for field in all_form_fields:
#             field_responses = responses_by_field.get(field.id, [])
            
#             if field_responses:
#                 # Serialize existing responses
#                 for response in field_responses:
#                     try:
#                         serializer = self.get_serializer(response, context={'request': self.request})
#                         response_data['responses'].append(serializer.data)
#                     except (UnicodeDecodeError, ValueError) as e:
#                         # Handle problematic responses gracefully
#                         error_response = {
#                             'id': response.id,
#                             'submission_id': response.submission.id if response.submission else None,
#                             'architecture_id': architecture.id,
#                             'architecture_name': str(architecture),
#                             'token': response.submission.token.token if response.submission and response.submission.token else None,
#                             'field': field.id,
#                             'field_label': field.label,
#                             'field_type': field.field_type,
#                             'field_order': field.order,
#                             'field_required': field.is_required,
#                             'value': f"Error: Could not decode value for {field.field_type} field",
#                             'created_at': response.created_at.isoformat() if response.created_at else None
#                         }
#                         response_data['responses'].append(error_response)
#             else:
#                 # Create empty token for missing field
#                 empty_response_data = {
#                     'id': None,
#                     'submission_id': None,
#                     'architecture_id': architecture.id,
#                     'architecture_name': str(architecture),
#                     'token': None,
#                     'field': field.id,
#                     'field_label': field.label,
#                     'field_type': field.field_type,
#                     'field_order': field.order,
#                     'field_required': field.is_required,
#                     'value': None,
#                     'created_at': None
#                 }
#                 response_data['responses'].append(empty_response_data)

#         return response_data



    # class ArchitectureResponsesView(generics.ListAPIView):
    #     """
    #     Retrieve all field responses for a specific architecture ID
    #     Includes both submitted responses and empty tokens for missing fields
    #     Accessible by architecture owner and admin users
    #     """
    #     serializer_class = ArchitectureFieldResponseSerializer
    #     authentication_classes = [JWTAuthentication, SessionAuthentication, TokenAuthentication]
    #     permission_classes = [IsAuthenticated]

    #     def get_queryset(self):
    #         architecture_id = self.kwargs['architecture_id']
    #         user = self.request.user
            
    #         # Base queryset - admin users can see all, regular users only their own
    #         if user.is_staff or user.is_superuser:
    #             # Admin users can access all responses
    #             return FieldResponse.objects.filter(
    #                 submission__token__architecture_id=architecture_id
    #             ).select_related(
    #                 'field', 
    #                 'submission', 
    #                 'submission__token',
    #                 'submission__token__architecture'
    #             ).only(
    #                 'id', 'field_id', 'value_text', 'value_number', 'value_date',
    #                 'value_boolean', 'value_alphanumeric', 'created_at',
    #                 'submission__id', 'submission__token__architecture_id',
    #                 'submission__token__architecture__name', 'submission__token__token',
    #                 'field__label', 'field__field_type', 'field__order', 'field__is_required'
    #             )
    #         else:
    #             # Regular users can only access their own architectures
    #             return FieldResponse.objects.filter(
    #                 submission__token__architecture_id=architecture_id,
    #                 submission__token__architecture__created_by=user
    #             ).select_related(
    #                 'field', 
    #                 'submission', 
    #                 'submission__token',
    #                 'submission__token__architecture'
    #             ).only(
    #                 'id', 'field_id', 'value_text', 'value_number', 'value_date',
    #                 'value_boolean', 'value_alphanumeric', 'created_at',
    #                 'submission__id', 'submission__token__architecture_id',
    #                 'submission__token__architecture__name', 'submission__token__token',
    #                 'field__label', 'field__field_type', 'field__order', 'field__is_required'
    #             )

    #     def has_permission_to_access_architecture(self, architecture_id, user):
    #         """
    #         Check if user has permission to access this architecture
    #         Returns architecture object if user has permission, None otherwise
    #         """
    #         try:
    #             if user.is_staff or user.is_superuser:
    #                 # Admin users can access any architecture
    #                 return Architecture.objects.get(id=architecture_id)
    #             else:
    #                 # Regular users can only access their own architectures
    #                 return Architecture.objects.get(id=architecture_id, created_by=user)
    #         except Architecture.DoesNotExist:
    #             return None

    #     def list(self, request, *args, **kwargs):
    #         # Debug information to help troubleshoot
    #         print(f"User: {request.user}")
    #         print(f"User authenticated: {request.user.is_authenticated}")
    #         print(f"User is active: {request.user.is_active}")
    #         print(f"User is staff: {request.user.is_staff}")
    #         print(f"User is superuser: {request.user.is_superuser}")
    #         print(f"User groups: {[group.name for group in request.user.groups.all()]}")
            
    #         # Check if user is authenticated (should be handled by permission_classes, but double-check)
    #         if not request.user.is_authenticated:
    #             return Response(
    #                 {"error": "Authentication required"}, 
    #                 status=status.HTTP_401_UNAUTHORIZED
    #             )
            
    #         architecture_id = kwargs['architecture_id']
    #         user = request.user
            
    #         # Check if user has permission to access this architecture
    #         architecture = self.has_permission_to_access_architecture(architecture_id, user)
    #         if not architecture:
    #             return Response(
    #                 {"error": "Architecture not found or you don't have permission to access it"}, 
    #                 status=status.HTTP_404_NOT_FOUND
    #             )

    #         # Get all tokens for this architecture
    #         # For admin users, get all tokens; for regular users, this is already filtered by ownership
    #         if user.is_staff or user.is_superuser:
    #             tokens = FormToken.objects.filter(architecture_id=architecture_id)
    #         else:
    #             tokens = FormToken.objects.filter(architecture_id=architecture_id)
            
    #         if not tokens.exists():
    #             return Response(self.get_empty_responses(architecture))

    #         # Get all form fields from all forms used in tokens
    #         form_ids = tokens.values_list('form_id', flat=True).distinct()
    #         all_form_fields = FormField.objects.filter(
    #             form_id__in=form_ids, 
    #             is_active=True
    #         ).order_by('order').only(
    #             'id', 'label', 'field_type', 'order', 'is_required', 'form_id'
    #         )
            
    #         # Get existing responses (exclude image fields from initial query)
    #         # Use the appropriate queryset based on user role
    #         if user.is_staff or user.is_superuser:
    #             existing_responses = FieldResponse.objects.filter(
    #                 submission__token__architecture_id=architecture_id
    #             ).exclude(field__field_type='image').select_related(
    #                 'field', 'submission', 'submission__token', 'submission__token__architecture'
    #             )
                
    #             image_responses = FieldResponse.objects.filter(
    #                 submission__token__architecture_id=architecture_id,
    #                 field__field_type='image'
    #             ).select_related(
    #                 'field', 'submission', 'submission__token', 'submission__token__architecture'
    #             )
    #         else:
    #             existing_responses = FieldResponse.objects.filter(
    #                 submission__token__architecture_id=architecture_id,
    #                 submission__token__architecture__created_by=user
    #             ).exclude(field__field_type='image').select_related(
    #                 'field', 'submission', 'submission__token', 'submission__token__architecture'
    #             )
                
    #             image_responses = FieldResponse.objects.filter(
    #                 submission__token__architecture_id=architecture_id,
    #                 submission__token__architecture__created_by=user,
    #                 field__field_type='image'
    #             ).select_related(
    #                 'field', 'submission', 'submission__token', 'submission__token__architecture'
    #             )

    #         # Create complete response data
    #         response_data = self.prepare_complete_response_data(
    #             architecture, tokens, all_form_fields, existing_responses, image_responses
    #         )

    #         return Response(response_data)

    #     def get_empty_responses(self, architecture):
    #         """Return empty response structure when no tokens exist"""
    #         return {
    #             'architecture_id': architecture.id,
    #             'architecture_name': str(architecture),
    #             'token_count': 0,
    #             'submission_count': 0,
    #             'tokens': [],
    #             'submission_ids': [],
    #             'responses': []
    #         }

    #     def prepare_complete_response_data(self, architecture, tokens, all_form_fields, existing_responses, image_responses):
    #         """Prepare complete response data organized by submission"""
            
    #         # Get all submissions for these tokens, ordered by ID
    #         submissions = FormSubmission.objects.filter(token__in=tokens).order_by('id')
            
    #         # Combine all responses
    #         all_responses = list(existing_responses) + list(image_responses)
            
    #         # Group responses by submission_id and field_id for easy lookup
    #         responses_by_submission = {}
    #         for response in all_responses:
    #             submission_id = response.submission_id
    #             if submission_id not in responses_by_submission:
    #                 responses_by_submission[submission_id] = {}
    #             responses_by_submission[submission_id][response.field_id] = response

    #         # Prepare response data structure
    #         response_data = {
    #             'architecture_id': architecture.id,
    #             'architecture_name': str(architecture),
    #             'token_count': tokens.count(),
    #             'submission_count': submissions.count(),
    #             'tokens': list(tokens.values_list('token', flat=True)),
    #             'submission_ids': list(submissions.values_list('id', flat=True)),
    #             'responses': []
    #         }

    #         # For each submission, create entries for all fields
    #         for submission in submissions:
    #             submission_responses = responses_by_submission.get(submission.id, {})
                
    #             for field in all_form_fields:
    #                 response = submission_responses.get(field.id)
                    
    #                 if response:
    #                     # Existing response found for this field in this submission
    #                     try:
    #                         serializer = self.get_serializer(response, context={'request': self.request})
    #                         response_data['responses'].append(serializer.data)
    #                     except (UnicodeDecodeError, ValueError) as e:
    #                         # Handle problematic responses gracefully
    #                         error_response = {
    #                             'id': response.id,
    #                             'submission_id': submission.id,
    #                             'architecture_id': architecture.id,
    #                             'architecture_name': str(architecture),
    #                             'token': submission.token.token if submission.token else None,
    #                             'field': field.id,
    #                             'field_label': field.label,
    #                             'field_type': field.field_type,
    #                             'field_order': field.order,
    #                             'field_required': field.is_required,
    #                             'value': f"Error: Could not decode value for {field.field_type} field",
    #                             'created_at': response.created_at.isoformat() if response.created_at else None
    #                         }
    #                         response_data['responses'].append(error_response)
    #                 else:
    #                     # No response for this field in this submission - create null entry
    #                     null_response = {
    #                         'id': None,
    #                         'submission_id': submission.id,
    #                         'architecture_id': architecture.id,
    #                         'architecture_name': str(architecture),
    #                         'token': submission.token.token if submission.token else None,
    #                         'field': field.id,
    #                         'field_label': field.label,
    #                         'field_type': field.field_type,
    #                         'field_order': field.order,
    #                         'field_required': field.is_required,
    #                         'value': None,
    #                         'created_at': None
    #                     }
    #                     response_data['responses'].append(null_response)

    #         return response_data




class ArchitectureResponsesView(generics.ListAPIView):
    """
    Retrieve all field responses for a specific architecture ID
    Includes both submitted responses and empty tokens for missing fields
    Accessible by architecture owner and admin users
    """
    serializer_class = ArchitectureFieldResponseSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        architecture_id = self.kwargs['architecture_id']
        user = self.request.user
        
        # Base queryset - admin users can see all, regular users only their own
        if user.is_staff or user.is_superuser:
            # Admin users can access all responses
            return FieldResponse.objects.filter(
                submission__token__architecture_id=architecture_id
            ).select_related(
                'field', 
                'submission', 
                'submission__token',
                'submission__token__architecture'
            ).only(
                'id', 'field_id', 'value_text', 'value_number', 'value_date',
                'value_boolean', 'value_alphanumeric', 'value_email', 'value_phonenumber',
                'value_image',
                'created_at',
                'submission__id', 'submission__token__architecture_id',
                'submission__token__architecture__name', 'submission__token__token',
                'field__label', 'field__field_type', 'field__order', 'field__is_required'
            )
        else:
            # Regular users can only access their own architectures
            return FieldResponse.objects.filter(
                submission__token__architecture_id=architecture_id,
                submission__token__architecture__created_by=user
            ).select_related(
                'field', 
                'submission', 
                'submission__token',
                'submission__token__architecture'
            ).only(
                'id', 'field_id', 'value_text', 'value_number', 'value_date',
                'value_boolean', 'value_alphanumeric', 'value_email', 'value_phonenumber',
                'value_image',
                'created_at',
                'submission__id', 'submission__token__architecture_id',
                'submission__token__architecture__name', 'submission__token__token',
                'field__label', 'field__field_type', 'field__order', 'field__is_required'
            )

    def has_permission_to_access_architecture(self, architecture_id, user):
        """
        Check if user has permission to access this architecture
        Returns architecture object if user has permission, None otherwise
        """
        try:
            if user.is_staff or user.is_superuser:
                # Admin users can access any architecture
                return Architecture.objects.get(id=architecture_id)
            else:
                # Regular users can only access their own architectures
                return Architecture.objects.get(id=architecture_id, created_by=user)
        except Architecture.DoesNotExist:
            return None

    def list(self, request, *args, **kwargs):
        # Debug information to help troubleshoot
        print(f"User: {request.user}")
        print(f"User authenticated: {request.user.is_authenticated}")
        print(f"User is active: {request.user.is_active}")
        print(f"User is staff: {request.user.is_staff}")
        print(f"User is superuser: {request.user.is_superuser}")
        print(f"User groups: {[group.name for group in request.user.groups.all()]}")
        
        # Check if user is authenticated (should be handled by permission_classes, but double-check)
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        architecture_id = kwargs['architecture_id']
        user = request.user
        
        # Check if user has permission to access this architecture
        architecture = self.has_permission_to_access_architecture(architecture_id, user)
        if not architecture:
            return Response(
                {"error": "Architecture not found or you don't have permission to access it"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all tokens for this architecture
        tokens = FormToken.objects.filter(architecture_id=architecture_id)
        
        if not tokens.exists():
            return Response(self.get_empty_responses(architecture))

        # Get all form fields from all forms used in tokens
        form_ids = tokens.values_list('form_id', flat=True).distinct()
        all_form_fields = FormField.objects.filter(
            form_id__in=form_ids, 
            is_active=True
        ).order_by('order').only(
            'id', 'label', 'field_type', 'order', 'is_required', 'form_id'
        )
        
        # Get ALL existing responses including image fields
        if user.is_staff or user.is_superuser:
            existing_responses = FieldResponse.objects.filter(
                submission__token__architecture_id=architecture_id
            ).select_related(
                'field', 'submission', 'submission__token', 'submission__token__architecture'
            )
        else:
            existing_responses = FieldResponse.objects.filter(
                submission__token__architecture_id=architecture_id,
                submission__token__architecture__created_by=user
            ).select_related(
                'field', 'submission', 'submission__token', 'submission__token__architecture'
            )

        # Create complete response data
        response_data = self.prepare_complete_response_data(
            architecture, tokens, all_form_fields, existing_responses
        )

        return Response(response_data)

    def get_empty_responses(self, architecture):
        """Return empty response structure when no tokens exist"""
        return {
            'architecture_id': architecture.id,
            'architecture_name': str(architecture),
            'token_count': 0,
            'submission_count': 0,
            'tokens': [],
            'submission_ids': [],
            'responses': []
        }

    def prepare_complete_response_data(self, architecture, tokens, all_form_fields, existing_responses):
        """Prepare complete response data organized by submission"""
        
        # Get all submissions for these tokens, ordered by ID
        submissions = FormSubmission.objects.filter(token__in=tokens).order_by('id')
        
        # Group responses by submission_id and field_id for easy lookup
        responses_by_submission = {}
        for response in existing_responses:
            submission_id = response.submission_id
            if submission_id not in responses_by_submission:
                responses_by_submission[submission_id] = {}
            responses_by_submission[submission_id][response.field_id] = response

        # Prepare response data structure
        response_data = {
            'architecture_id': architecture.id,
            'architecture_name': str(architecture),
            'token_count': tokens.count(),
            'submission_count': submissions.count(),
            'tokens': list(tokens.values_list('token', flat=True)),
            'submission_ids': list(submissions.values_list('id', flat=True)),
            'responses': []
        }

        # For each submission, create entries for all fields
        for submission in submissions:
            submission_responses = responses_by_submission.get(submission.id, {})
            
            for field in all_form_fields:
                response = submission_responses.get(field.id)
                
                if response:
                    # Existing response found for this field in this submission
                    try:
                        serializer = self.get_serializer(response, context={'request': self.request})
                        response_data['responses'].append(serializer.data)
                    except Exception as e:
                        print(f"Error serializing response {response.id}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Handle problematic responses gracefully
                        error_response = {
                            'id': response.id,
                            'submission_id': submission.id,
                            'architecture_id': architecture.id,
                            'architecture_name': str(architecture),
                            'token': submission.token.token if submission.token else None,
                            'field': field.id,
                            'field_label': field.label,
                            'field_type': field.field_type,
                            'field_order': field.order,
                            'field_required': field.is_required,
                            'value': f"Error: {str(e)}",
                            'created_at': response.created_at.isoformat() if response.created_at else None
                        }
                        response_data['responses'].append(error_response)
                else:
                    # No response for this field in this submission - create null entry
                    null_response = {
                        'id': None,
                        'submission_id': submission.id,
                        'architecture_id': architecture.id,
                        'architecture_name': str(architecture),
                        'token': submission.token.token if submission.token else None,
                        'field': field.id,
                        'field_label': field.label,
                        'field_type': field.field_type,
                        'field_order': field.order,
                        'field_required': field.is_required,
                        'value': None,
                        'created_at': None
                    }
                    response_data['responses'].append(null_response)

        return response_data

    

#--------------------below code is old code main 24/1:20-=====================-----------------------------------

# class ArchitectureResponsesView(generics.ListAPIView):
#     """
#     Retrieve all field responses for a specific architecture ID
#     Includes both submitted responses and empty tokens for missing fields
#     """
#     serializer_class = ArchitectureFieldResponseSerializer
#     authentication_classes = [JWTAuthentication, SessionAuthentication, TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         architecture_id = self.kwargs['architecture_id']
#         user = self.request.user
        
#         # Filter to only include architectures created by the current user
#         return FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id,
#             submission__token__architecture__created_by=user  # Add this filter
#         ).select_related(
#             'field', 
#             'submission', 
#             'submission__token',
#             'submission__token__architecture'
#         ).only(
#             'id', 'field_id', 'value_text', 'value_number', 'value_date',
#             'value_boolean', 'value_alphanumeric', 'created_at',
#             'submission__id', 'submission__token__architecture_id',
#             'submission__token__architecture__name', 'submission__token__token',
#             'field__label', 'field__field_type', 'field__order', 'field__is_required'
#         )

#     def list(self, request, *args, **kwargs):
#         # Debug information to help troubleshoot
#         print(f"User: {request.user}")
#         print(f"User authenticated: {request.user.is_authenticated}")
#         print(f"User is active: {request.user.is_active}")
#         print(f"User is staff: {request.user.is_staff}")
#         print(f"User is superuser: {request.user.is_superuser}")
#         print(f"User groups: {[group.name for group in request.user.groups.all()]}")
        
#         # Check if user is authenticated (should be handled by permission_classes, but double-check)
#         if not request.user.is_authenticated:
#             return Response(
#                 {"error": "Authentication required"}, 
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
        
#         architecture_id = kwargs['architecture_id']
#         user = request.user
        
#         try:
#             # Check if architecture exists AND is owned by the current user
#             architecture = Architecture.objects.get(
#                 id=architecture_id,
#                 created_by=user  # Add this filter
#             )
#         except Architecture.DoesNotExist:
#             return Response(
#                 {"error": "Architecture not found or you don't have permission to access it"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         # Get all tokens for this architecture (already filtered by user via architecture)
#         tokens = FormToken.objects.filter(architecture_id=architecture_id)
        
#         if not tokens.exists():
#             return Response(self.get_empty_responses(architecture))

#         # Get all form fields from all forms used in tokens
#         form_ids = tokens.values_list('form_id', flat=True).distinct()
#         all_form_fields = FormField.objects.filter(
#             form_id__in=form_ids, 
#             is_active=True
#         ).order_by('order').only(
#             'id', 'label', 'field_type', 'order', 'is_required', 'form_id'
#         )
        
#         # Get existing responses (exclude image fields from initial query)
#         existing_responses = FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id
#         ).exclude(field__field_type='image').select_related(
#             'field', 'submission', 'submission__token', 'submission__token__architecture'
#         )
        
#         # Handle image responses separately to avoid encoding issues
#         image_responses = FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id,
#             field__field_type='image'
#         ).select_related(
#             'field', 'submission', 'submission__token', 'submission__token__architecture'
#         )

#         # Create complete response data
#         response_data = self.prepare_complete_response_data(
#             architecture, tokens, all_form_fields, existing_responses, image_responses
#         )

#         return Response(response_data)

#     def get_empty_responses(self, architecture):
#         """Return empty response structure when no tokens exist"""
#         return {
#             'architecture_id': architecture.id,
#             'architecture_name': str(architecture),
#             'token_count': 0,
#             'submission_count': 0,
#             'tokens': [],
#             'submission_ids': [],
#             'responses': []
#         }

#     def prepare_complete_response_data(self, architecture, tokens, all_form_fields, existing_responses, image_responses):
#         """Prepare complete response data including empty tokens"""
        
#         # Get all submissions for these tokens
#         submissions = FormSubmission.objects.filter(token__in=tokens)
        
#         # Combine all responses
#         all_responses = list(existing_responses) + list(image_responses)
        
#         # Group responses by field for easy lookup
#         responses_by_field = {}
#         for response in all_responses:
#             field_id = response.field_id
#             if field_id not in responses_by_field:
#                 responses_by_field[field_id] = []
#             responses_by_field[field_id].append(response)

#         # Prepare response data
#         response_data = {
#             'architecture_id': architecture.id,
#             'architecture_name': str(architecture),
#             'token_count': tokens.count(),
#             'submission_count': submissions.count(),
#             'tokens': list(tokens.values_list('token', flat=True)),
#             'submission_ids': list(submissions.values_list('id', flat=True)),
#             'responses': []
#         }

#         for field in all_form_fields:
#             field_responses = responses_by_field.get(field.id, [])
            
#             if field_responses:
#                 # Serialize existing responses
#                 for response in field_responses:
#                     try:
#                         serializer = self.get_serializer(response, context={'request': self.request})
#                         response_data['responses'].append(serializer.data)
#                     except (UnicodeDecodeError, ValueError) as e:
#                         # Handle problematic responses gracefully
#                         error_response = {
#                             'id': response.id,
#                             'submission_id': response.submission.id if response.submission else None,
#                             'architecture_id': architecture.id,
#                             'architecture_name': str(architecture),
#                             'token': response.submission.token.token if response.submission and response.submission.token else None,
#                             'field': field.id,
#                             'field_label': field.label,
#                             'field_type': field.field_type,
#                             'field_order': field.order,
#                             'field_required': field.is_required,
#                             'value': f"Error: Could not decode value for {field.field_type} field",
#                             'created_at': response.created_at.isoformat() if response.created_at else None
#                         }
#                         response_data['responses'].append(error_response)
#             else:
#                 # Create empty token for missing field
#                 empty_response_data = {
#                     'id': None,
#                     'submission_id': None,
#                     'architecture_id': architecture.id,
#                     'architecture_name': str(architecture),
#                     'token': None,
#                     'field': field.id,
#                     'field_label': field.label,
#                     'field_type': field.field_type,
#                     'field_order': field.order,
#                     'field_required': field.is_required,
#                     'value': None,
#                     'created_at': None
#                 }
#                 response_data['responses'].append(empty_response_data)

#         return response_data
#-==-------------------------------------------till here 24/1:30-==-=================================================================-
#*******************************************************((((((((((((((((((((((((((()))))))))))))))))))))))))))
# class ArchitectureResponsesView(generics.ListAPIView):
#     """
#     Retrieve all field responses for a specific architecture ID
#     Includes both submitted responses and empty tokens for missing fields
#     """
#     serializer_class = ArchitectureFieldResponseSerializer
#     authentication_classes = [JWTAuthentication, SessionAuthentication, TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         architecture_id = self.kwargs['architecture_id']
#         return FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id
#         ).select_related(
#             'field', 
#             'submission', 
#             'submission__token',
#             'submission__token__architecture'
#         ).only(
#             'id', 'field_id', 'value_text', 'value_number', 'value_date',
#             'value_boolean', 'value_alphanumeric', 'created_at',
#             'submission__id', 'submission__token__architecture_id',
#             'submission__token__architecture__name', 'submission__token__token',
#             'field__label', 'field__field_type', 'field__order', 'field__is_required'
#         )

#     def list(self, request, *args, **kwargs):
#         # Debug information to help troubleshoot
#         print(f"User: {request.user}")
#         print(f"User authenticated: {request.user.is_authenticated}")
#         print(f"User is active: {request.user.is_active}")
#         print(f"User is staff: {request.user.is_staff}")
#         print(f"User is superuser: {request.user.is_superuser}")
#         print(f"User groups: {[group.name for group in request.user.groups.all()]}")
        
#         # Check if user is authenticated (should be handled by permission_classes, but double-check)
#         if not request.user.is_authenticated:
#             return Response(
#                 {"error": "Authentication required"}, 
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
        
#         architecture_id = kwargs['architecture_id']
        
#         try:
#             # Check if architecture exists
#             architecture = Architecture.objects.get(id=architecture_id)
#         except Architecture.DoesNotExist:
#             return Response(
#                 {"error": "Architecture not found"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         # Get all tokens for this architecture
#         tokens = FormToken.objects.filter(architecture_id=architecture_id)
        
#         if not tokens.exists():
#             return Response(self.get_empty_responses(architecture))

#         # Get all form fields from all forms used in tokens
#         form_ids = tokens.values_list('form_id', flat=True).distinct()
#         all_form_fields = FormField.objects.filter(
#             form_id__in=form_ids, 
#             is_active=True
#         ).order_by('order').only(
#             'id', 'label', 'field_type', 'order', 'is_required', 'form_id'
#         )
        
#         # Get existing responses (exclude image fields from initial query)
#         existing_responses = FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id
#         ).exclude(field__field_type='image').select_related(
#             'field', 'submission', 'submission__token', 'submission__token__architecture'
#         )
        
#         # Handle image responses separately to avoid encoding issues
#         image_responses = FieldResponse.objects.filter(
#             submission__token__architecture_id=architecture_id,
#             field__field_type='image'
#         ).select_related(
#             'field', 'submission', 'submission__token', 'submission__token__architecture'
#         )

#         # Create complete response data
#         response_data = self.prepare_complete_response_data(
#             architecture, tokens, all_form_fields, existing_responses, image_responses
#         )

#         return Response(response_data)

#     def get_empty_responses(self, architecture):
#         """Return empty response structure when no tokens exist"""
#         return {
#             'architecture_id': architecture.id,
#             'architecture_name': str(architecture),
#             'token_count': 0,
#             'submission_count': 0,
#             'tokens': [],
#             'submission_ids': [],
#             'responses': []
#         }

#     def prepare_complete_response_data(self, architecture, tokens, all_form_fields, existing_responses, image_responses):
#         """Prepare complete response data including empty tokens"""
        
#         # Get all submissions for these tokens
#         submissions = FormSubmission.objects.filter(token__in=tokens)
        
#         # Combine all responses
#         all_responses = list(existing_responses) + list(image_responses)
        
#         # Group responses by field for easy lookup
#         responses_by_field = {}
#         for response in all_responses:
#             field_id = response.field_id
#             if field_id not in responses_by_field:
#                 responses_by_field[field_id] = []
#             responses_by_field[field_id].append(response)

#         # Prepare response data
#         response_data = {
#             'architecture_id': architecture.id,
#             'architecture_name': str(architecture),
#             'token_count': tokens.count(),
#             'submission_count': submissions.count(),
#             'tokens': list(tokens.values_list('token', flat=True)),
#             'submission_ids': list(submissions.values_list('id', flat=True)),
#             'responses': []
#         }

#         for field in all_form_fields:
#             field_responses = responses_by_field.get(field.id, [])
            
#             if field_responses:
#                 # Serialize existing responses
#                 for response in field_responses:
#                     try:
#                         serializer = self.get_serializer(response, context={'request': self.request})
#                         response_data['responses'].append(serializer.data)
#                     except (UnicodeDecodeError, ValueError) as e:
#                         # Handle problematic responses gracefully
#                         error_response = {
#                             'id': response.id,
#                             'submission_id': response.submission.id if response.submission else None,
#                             'architecture_id': architecture.id,
#                             'architecture_name': str(architecture),
#                             'token': response.submission.token.token if response.submission and response.submission.token else None,
#                             'field': field.id,
#                             'field_label': field.label,
#                             'field_type': field.field_type,
#                             'field_order': field.order,
#                             'field_required': field.is_required,
#                             'value': f"Error: Could not decode value for {field.field_type} field",
#                             'created_at': response.created_at.isoformat() if response.created_at else None
#                         }
#                         response_data['responses'].append(error_response)
#             else:
#                 # Create empty token for missing field
#                 empty_response_data = {
#                     'id': None,
#                     'submission_id': None,
#                     'architecture_id': architecture.id,
#                     'architecture_name': str(architecture),
#                     'token': None,
#                     'field': field.id,
#                     'field_label': field.label,
#                     'field_type': field.field_type,
#                     'field_order': field.order,
#                     'field_required': field.is_required,
#                     'value': None,
#                     'created_at': None
#                 }
#                 response_data['responses'].append(empty_response_data)

#         return response_data
#code is change by 20-10-25--=========---------------------------------------------------
#here is my updated code 19-10-2025============-------------------------------------------===================
# Add the token-based edit and delete views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

import logging
import base64
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import FormToken, FormSubmission, FieldResponse, FormField
from .serializers import ArchitectureFieldResponseSerializer

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
import logging
import base64

logger = logging.getLogger(__name__)
#888888888888888888888888888888888888888888888888888888888888new 22200000000000000000000000
def get_token_object(token_str):
    """
    Unified token lookup with proper normalization
    """
    try:
        normalized_token = normalize_token(token_str)
        
        # First try exact match with normalized token
        try:
            return FormToken.objects.get(token=normalized_token)
        except FormToken.DoesNotExist:
            pass
        
        # If not found, try case-insensitive search
        all_tokens = FormToken.objects.all()
        for form_token in all_tokens:
            try:
                if normalize_token(form_token.token) == normalized_token:
                    return form_token
            except ValueError:
                continue
        
        return None
        
    except ValueError as e:
        raise ValueError(f"Invalid token format: {str(e)}")


def normalize_token(token):
    """
    Normalize token by removing leading zeros and ensuring it's a valid numeric token
    """
    try:
        # Remove any whitespace
        token = str(token).strip()
        
        # Convert to integer to remove leading zeros, then back to string
        normalized = str(int(token))
        
        return normalized
    except (ValueError, TypeError) as e:
        raise ValueError(f"Token '{token}' is not a valid numeric token")


def check_user_permission(request, token_obj, action="access"):
    """
    Check if the current user has permission to access/modify the token data
    """
    # If no user is authenticated, deny access
    if not request.user or not request.user.is_authenticated:
        return False, "Authentication required to access this resource"
    
    # Superusers can access everything
    if request.user.is_superuser:
        return True, None
    
    # Check if user is the owner/creator of the token
    if hasattr(token_obj, 'created_by') and token_obj.created_by:
        if token_obj.created_by == request.user:
            return True, None
        else:
            return False, f"You do not have permission to {action} this token's data"
    
    # Check if user is associated with the token's architecture
    if hasattr(token_obj, 'architecture') and token_obj.architecture:
        # Assuming Architecture model has a users ManyToMany field
        if hasattr(token_obj.architecture, 'users') and request.user in token_obj.architecture.users.all():
            return True, None
        
        # Or check if user is in architecture's organization
        if hasattr(token_obj.architecture, 'organization') and token_obj.architecture.organization:
            if hasattr(token_obj.architecture.organization, 'users') and request.user in token_obj.architecture.organization.users.all():
                return True, None
    
    # Check if user has permission through the form
    if hasattr(token_obj, 'form') and token_obj.form:
        if hasattr(token_obj.form, 'created_by') and token_obj.form.created_by == request.user:
            return True, None
        
        # Check if user is in form's allowed users
        if hasattr(token_obj.form, 'allowed_users') and request.user in token_obj.form.allowed_users.all():
            return True, None
    
    return False, f"You do not have permission to {action} this token's data"


# @api_view(['GET', 'PUT', 'PATCH'])
# @permission_classes([IsAuthenticated])
# def edit_token_responses(request, token):
#     """
#     View or edit all field responses for a specific token (numeric token)
#     """
#     try:
#         # Get the token object using the unified token lookup
#         token_obj = get_token_object(token)
#         if not token_obj:
#             return Response(
#                 {"error": f"Token {token} not found"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )
        
#         # Check user permission for this token
#         has_permission, error_message = check_user_permission(request, token_obj, 
#                                                             "edit" if request.method in ['PUT', 'PATCH'] else "view")
#         if not has_permission:
#             return Response(
#                 {"error": error_message}, 
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Get or create the submission for this token
#         submission, created = FormSubmission.objects.get_or_create(
#             token=token_obj,
#             defaults={'form': token_obj.form}
#         )
        
#         if request.method == 'GET':
#             return handle_get_request(request, token_obj, submission, token)
        
#         elif request.method in ['PUT', 'PATCH']:
#             return handle_update_request(request, token_obj, submission, token)
        
#     except ValueError as e:
#         return Response(
#             {"error": str(e)}, 
#             status=status.HTTP_400_BAD_REQUEST
#         )
#     except Exception as e:
#         logger.error(f"Error in edit_token_responses for token {token}: {str(e)}")
#         return Response(
#             {"error": f"Internal server error: {str(e)}"}, 
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )  28/12/2025

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_token_responses(request, token):
    try:
        token_obj = get_token_object(token)
        if not token_obj:
            return Response({"error": f"Token {token} not found"}, status=404)

        action = "edit" if request.method in ['PUT', 'PATCH'] else "view"
        has_permission, error_message = check_user_permission(request, token_obj, action)
        if not has_permission:
            return Response({"error": error_message}, status=403)

        submission, created = FormSubmission.objects.get_or_create(
            token=token_obj,
            defaults={'form': token_obj.form}
        )

        if request.method == 'GET':
            return handle_get_request(request, token_obj, submission, token)

        return handle_update_request(request, token_obj, submission, token)

    except Exception as e:
        logger.error(f"Error in edit_token_responses: {e}")
        return Response({"error": "Internal server error"}, status=500)



def handle_get_request(request, token_obj, submission, token):
    """
    Handle GET request - retrieve all field responses safely
    """
    # Get all responses for this submission
    responses = FieldResponse.objects.filter(
        submission=submission
    ).select_related('field', 'field__form', 'submission', 'submission__token')
    
    # Get all fields for the form associated with this token
    form_fields = FormField.objects.filter(
        form=token_obj.form,
        is_active=True
    ).order_by('order')
    
    response_data = []
    field_responses_map = {response.field_id: response for response in responses}
    
    # Create response data for all form fields, including empty ones
    for field in form_fields:
        response = field_responses_map.get(field.id)
        
        if response:
            # Field has a response - handle value safely
            field_value = get_safe_field_value(response, field.field_type, request)
            
            response_data.append({
                'field_id': field.id,
                'field_label': field.label,
                'field_type': field.field_type,
                'field_required': field.is_required,
                'value': field_value,
                'response_id': response.id,
                'field_order': field.order
            })
        else:
            # Field doesn't have a response yet
            response_data.append({
                'field_id': field.id,
                'field_label': field.label,
                'field_type': field.field_type,
                'field_required': field.is_required,
                'value': None,
                'response_id': None,
                'field_order': field.order
            })
    
    return Response({
        'token': token,
        'normalized_token': normalize_token(token),
        'submission_id': submission.id,
        'form_id': token_obj.form.id,
        'form_title': token_obj.form.title,
        'architecture_id': token_obj.architecture.id,
        'architecture_name': token_obj.architecture.name,
        'responses': response_data,
        'available_fields': [
            {
                'id': field.id,
                'label': field.label,
                'type': field.field_type,
                'required': field.is_required,
                'order': field.order,
                'placeholder': field.placeholder,
                'options': field.options
            }
            for field in form_fields
        ]
    })


# def get_safe_field_value(response, field_type, request):
#     """
#     Safely extract field value without causing encoding errors
#     """
#     try:
#         # For image fields, return URL instead of binary data
#         if field_type == 'image' and response.value_image:
#             if hasattr(response.value_image, 'url'):
#                 return request.build_absolute_uri(response.value_image.url)
#             return str(response.value_image)
        
#         # For other field types, use get_value() but handle binary data
#         raw_value = response.get_value()
        
#         # Handle binary data safely
#         if isinstance(raw_value, (bytes, bytearray)):
#             try:
#                 # Convert binary data to base64 for safe JSON serialization
#                 return base64.b64encode(raw_value).decode('ascii')
#             except Exception as e:
#                 logger.warning(f"Error encoding binary data for field {response.field.id}: {e}")
#                 return "[Binary data]"
        
#         # Handle file objects
#         if hasattr(raw_value, 'read') and hasattr(raw_value, 'seek'):
#             try:
#                 raw_value.seek(0)
#                 binary_data = raw_value.read()
#                 if binary_data:
#                     return base64.b64encode(binary_data).decode('ascii')
#                 return None
#             except Exception as e:
#                 logger.warning(f"Error reading file object for field {response.field.id}: {e}")
#                 return "[File data]"
        
#         # Ensure the value is JSON-serializable
#         if isinstance(raw_value, (int, float, bool, str, type(None))):
#             return raw_value
        
#         # Convert other types to string
#         return str(raw_value)
        
#     except Exception as e:
#         logger.warning(f"Error getting safe value for field {response.field.id}: {e}")
#         return None



def get_safe_field_value(response, field_type, request):
    """
    Safely extract field value without causing encoding errors
    """
    try:
        # For image fields, return URL instead of binary data
        if field_type == 'image' and response.value_image:
            if hasattr(response.value_image, 'url'):
                return request.build_absolute_uri(response.value_image.url)
            return str(response.value_image)
        
        # For other field types, get the appropriate value
        raw_value = None
        
        # Get value based on field type
        if field_type == 'number':
            raw_value = response.value_number
        elif field_type == 'date':
            raw_value = response.value_date
        elif field_type == 'checkbox':
            raw_value = response.value_boolean
        elif field_type == 'alphanumeric':
            raw_value = response.value_alphanumeric
        elif field_type == 'email':
            raw_value = response.value_email
        elif field_type == 'phonenumber':
            raw_value = response.value_phonenumber
        else:  # text, dropdown, etc.
            raw_value = response.value_text
        
        # Handle None values
        if raw_value is None:
            return None
        
        # Handle binary data safely
        if isinstance(raw_value, (bytes, bytearray)):
            try:
                # Convert binary data to base64 for safe JSON serialization
                return base64.b64encode(raw_value).decode('ascii')
            except Exception as e:
                logger.warning(f"Error encoding binary data for field {response.field.id}: {e}")
                return "[Binary data]"
        
        # Handle file objects
        if hasattr(raw_value, 'read') and hasattr(raw_value, 'seek'):
            try:
                raw_value.seek(0)
                binary_data = raw_value.read()
                if binary_data:
                    return base64.b64encode(binary_data).decode('ascii')
                return None
            except Exception as e:
                logger.warning(f"Error reading file object for field {response.field.id}: {e}")
                return "[File data]"
        
        # Handle date objects
        if hasattr(raw_value, 'strftime'):
            return raw_value.isoformat()
        
        # Ensure the value is JSON-serializable
        if isinstance(raw_value, (int, float, bool, str, type(None))):
            return raw_value
        
        # Convert other types to string
        return str(raw_value)
        
    except Exception as e:
        logger.warning(f"Error getting safe value for field {response.field.id}: {e}")
        return None

# def handle_update_request(request, token_obj, submission, token):
#     """
#     Handle PUT/PATCH requests - update field responses
#     """
#     # Update field responses within a transaction
#     with transaction.atomic():
#         updated_responses = []
#         errors = []
        
#         # Get all active fields for the form
#         form_fields = FormField.objects.filter(
#             form=token_obj.form,
#             is_active=True
#         )
        
#         for field in form_fields:
#             field_key = f'field_{field.id}'
#             field_value = request.data.get(field_key)
            
#             # Skip if field value is not provided (for PATCH) or if it's None
#             if field_value is None and request.method == 'PATCH':
#                 continue
            
#             # For required fields, ensure value is provided
#             if field.is_required and field_value in [None, '']:
#                 errors.append(f"Field '{field.label}' is required")
#                 continue
            
#             try:
#                 # Get or create the field response
#                 response, created = FieldResponse.objects.get_or_create(
#                     submission=submission,
#                     field=field,
#                     defaults={'created_by': request.user if request.user.is_authenticated else None}
#                 )
                
#                 # Update the response value based on field type with validation
#                 update_response_value(response, field, field_value, errors)
                
#                 if errors and errors[-1].startswith(f"Field '{field.label}'"):
#                     # Skip saving if there was a validation error for this field
#                     continue
                
#                 response.save()
                
#                 # Get the display value for response
#                 try:
#                     display_value = get_safe_field_value(response, field.field_type, request)
#                 except:
#                     display_value = field_value
                
#                 updated_responses.append({
#                     'field_id': field.id,
#                     'field_label': field.label,
#                     'field_type': field.field_type,
#                     'value': display_value,
#                     'response_id': response.id,
#                     'updated': True
#                 })
                
#             except Exception as e:
#                 errors.append(f"Error updating field '{field.label}': {str(e)}")
#                 continue
        
#         if errors:
#             return Response({
#                 "error": "Some fields could not be updated",
#                 "details": errors,
#                 "updated_responses": updated_responses
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         return Response({
#             "message": f"Successfully updated {len(updated_responses)} field responses for token {token}",
#             "updated_responses": updated_responses,
#             "submission_id": submission.id,
#             "token": token,
#             "normalized_token": normalize_token(token),
#             "form_title": token_obj.form.title
#         }) ******************************************28/12/2025




# def handle_update_request(request, token_obj, submission, token):
#     """
#     Handle PUT/PATCH requests - update field responses including images
#     """
#     try:
#         # Check content type to handle both JSON and multipart/form-data
#         if request.content_type == 'multipart/form-data':
#             # For form data (with file uploads)
#             data = request.POST.dict()
#             files = request.FILES
#         else:
#             # For JSON data
#             data = request.data
#             files = {}
        
#         # Get all fields for the form
#         form_fields = FormField.objects.filter(
#             form=token_obj.form,
#             is_active=True
#         )
        
#         updated_responses = []
        
#         # Process each field in the form
#         for field in form_fields:
#             field_key = f'field_{field.id}'
            
#             # Check if this field is in the request
#             has_data = field_key in data
#             has_file = field_key in files
            
#             if has_data or has_file:
#                 # Get or create response object
#                 response, created = FieldResponse.objects.get_or_create(
#                     submission=submission,
#                     field=field
#                 )
                
#                 # Determine the value to set
#                 if field.field_type == 'image' and has_file:
#                     # For image fields with file upload
#                     image_file = files[field_key]
#                     response.set_value(image_file)
#                     updated_responses.append(response)
#                 elif field.field_type == 'image' and has_data:
#                     # For image fields with data (could be base64 or null)
#                     value = data.get(field_key)
#                     if value in ['', 'null', None]:
#                         response.clear_value()  # Clear the image
#                     else:
#                         response.set_value(value)  # Handle base64 or other image data
#                     updated_responses.append(response)
#                 elif has_data:
#                     # For non-image fields
#                     value = data.get(field_key)
#                     response.set_value(value)
#                     updated_responses.append(response)
        
#         # Validate required fields
#         missing_required = []
#         for field in form_fields.filter(is_required=True):
#             # Check if required field has a value
#             response_exists = FieldResponse.objects.filter(
#                 submission=submission,
#                 field=field
#             ).exists()
            
#             if response_exists:
#                 # Check if the response has a value
#                 response = FieldResponse.objects.filter(
#                     submission=submission,
#                     field=field
#                 ).first()
#                 if not response or not response.has_value():
#                     missing_required.append(field.label)
#             else:
#                 missing_required.append(field.label)
        
#         if missing_required:
#             return Response({
#                 'error': 'Missing required fields',
#                 'missing_fields': missing_required
#             }, status=400)
        
#         # Return success response
#         return Response({
#             'success': True,
#             'message': f'Successfully updated {len(updated_responses)} field(s)',
#             'submission_id': submission.id,
#             'token': token,
#             'updated_fields': [resp.field.label for resp in updated_responses]
#         }, status=200)
        
#     except Exception as e:
#         logger.error(f"Error in handle_update_request: {e}")
#         return Response({"error": str(e)}, status=500)  


def handle_update_request(request, token_obj, submission, token):
    """
    Handle PUT/PATCH requests - update field responses including images
    """
    try:
        # Check content type to handle both JSON and multipart/form-data
        if request.content_type == 'multipart/form-data':
            # For form data (with file uploads)
            data = request.POST.dict()
            files = request.FILES
        else:
            # For JSON data
            data = request.data
            files = {}
        
        # Get all fields for the form
        form_fields = FormField.objects.filter(
            form=token_obj.form,
            is_active=True
        )
        
        updated_responses = []
        errors = []
        
        # Process each field in the form
        for field in form_fields:
            field_key = f'field_{field.id}'
            
            # Check if this field is in the request
            has_data = field_key in data
            has_file = field_key in files
            
            if has_data or has_file:
                # Get or create response object
                response, created = FieldResponse.objects.get_or_create(
                    submission=submission,
                    field=field
                )
                
                # Determine the value to set
                if field.field_type == 'image' and has_file:
                    # For image fields with file upload
                    image_file = files[field_key]
                    response.set_value(image_file)
                    updated_responses.append(response)
                elif field.field_type == 'image' and has_data:
                    # For image fields with data (could be base64 or null)
                    value = data.get(field_key)
                    if value in ['', 'null', None]:
                        response.clear_value()  # Clear the image
                    else:
                        response.set_value(value)  # Handle base64 or other image data
                    updated_responses.append(response)
                elif has_data:
                    # For non-image fields
                    value = data.get(field_key)
                    
                    # Special handling for specific field types
                    if field.field_type == 'email':
                        # Validate email format
                        import re
                        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                        if value and not re.match(email_regex, value):
                            errors.append(f"Field '{field.label}' must be a valid email address")
                            continue
                    
                    elif field.field_type == 'phonenumber':
                        # Validate phone number format
                        import re
                        digits_only = re.sub(r'\D', '', value) if value else ''
                        if value and (len(digits_only) < 10 or len(digits_only) > 15):
                            errors.append(f"Field '{field.label}' must have 10-15 digits")
                            continue
                    
                    elif field.field_type == 'alphanumeric':
                        # Validate alphanumeric
                        import re
                        if not re.match(r'^[A-Za-z0-9\s]+$', value):
                            errors.append(f"Field '{field.label}' must contain only letters and numbers")
                            continue
                    
                    response.set_value(value)
                    updated_responses.append(response)
        
        # Validate required fields
        missing_required = []
        for field in form_fields.filter(is_required=True):
            # Check if required field has a value
            response_exists = FieldResponse.objects.filter(
                submission=submission,
                field=field
            ).exists()
            
            if response_exists:
                # Check if the response has a value
                response = FieldResponse.objects.filter(
                    submission=submission,
                    field=field
                ).first()
                if not response or not response.has_value():
                    missing_required.append(field.label)
            else:
                missing_required.append(field.label)
        
        if missing_required:
            errors.append(f"Missing required fields: {', '.join(missing_required)}")
        
        # Return errors if any
        if errors:
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }, status=400)
        
        # Return success response
        return Response({
            'success': True,
            'message': f'Successfully updated {len(updated_responses)} field(s)',
            'submission_id': submission.id,
            'token': token,
            'updated_fields': [resp.field.label for resp in updated_responses]
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in handle_update_request: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)



# def update_response_value(response, field, field_value, errors):
#     """
#     Update the response value with proper validation
#     """
#     if field.field_type == 'number':
#         if field_value not in [None, '']:
#             try:
#                 response.value_number = float(field_value)
#             except (ValueError, TypeError):
#                 errors.append(f"Field '{field.label}' must be a valid number")
#         else:
#             response.value_number = None
    
#     elif field.field_type == 'date':
#         if field_value not in [None, '']:
#             response.value_date = field_value
#         else:
#             response.value_date = None
    
#     elif field.field_type == 'checkbox':
#         if field_value not in [None, '']:
#             # Convert string to boolean
#             if isinstance(field_value, str):
#                 field_value = field_value.lower() in ['true', '1', 'yes', 'on']
#             response.value_boolean = bool(field_value)
#         else:
#             response.value_boolean = False
    
#     elif field.field_type == 'alphanumeric':
#         response.value_alphanumeric = field_value
    
#     elif field.field_type == 'image':
#         # For image fields, we expect a file path or URL in this context
#         # For actual file uploads, you'd need a different approach
#         response.value_text = field_value
    
#     else:  # text, dropdown, and others
#         response.value_text = field_value 28/12/2025







def update_response_value(response, field, field_value, file_value, errors):
    """
    Update the response value with proper validation
    """
    if field.field_type == 'number':
        try:
            response.value_number = float(field_value) if field_value else None
        except ValueError:
            errors.append(f"Field '{field.label}' must be a valid number")

    elif field.field_type == 'date':
        response.value_date = field_value or None

    elif field.field_type == 'checkbox':
        if isinstance(field_value, str):
            field_value = field_value.lower() in ['true', '1', 'yes', 'on']
        response.value_boolean = bool(field_value)

    elif field.field_type == 'alphanumeric':
        # Clean alphanumeric value
        import re
        if field_value:
            field_value = re.sub(r'[^a-zA-Z0-9\s]', '', str(value))
        response.value_alphanumeric = field_value

    elif field.field_type == 'email':
        # Store email (lowercase)
        if field_value:
            field_value = field_value.lower().strip()
            # Basic email validation
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, field_value):
                errors.append(f"Field '{field.label}' must be a valid email address")
        response.value_email = field_value

    elif field.field_type == 'phonenumber':
        # Clean phone number
        if field_value:
            import re
            # Keep only digits and optional leading +
            phone_value = re.sub(r'[^\d+]', '', field_value)
            # Ensure + is only at the beginning if present
            if phone_value.startswith('+'):
                phone_value = '+' + re.sub(r'\+', '', phone_value[1:])
            else:
                phone_value = re.sub(r'\+', '', phone_value)
            
            # Basic validation
            digits_only = re.sub(r'\D', '', phone_value)
            if len(digits_only) < 10 or len(digits_only) > 15:
                errors.append(f"Field '{field.label}' must have 10-15 digits")
            
            response.value_phonenumber = phone_value

    elif field.field_type == 'image':
        if file_value:
            # delete old image
            if response.value_image:
                response.value_image.delete(save=False)
            response.value_image = file_value

    else:  # text, dropdown, etc.
        response.value_text = field_value



# def update_response_value(response, field, field_value, file_value, errors):

#     if field.field_type == 'number':
#         try:
#             response.value_number = float(field_value) if field_value else None
#         except ValueError:
#             errors.append(f"Field '{field.label}' must be a valid number")

#     elif field.field_type == 'date':
#         response.value_date = field_value or None

#     elif field.field_type == 'checkbox':
#         if isinstance(field_value, str):
#             field_value = field_value.lower() in ['true', '1', 'yes', 'on']
#         response.value_boolean = bool(field_value)

#     elif field.field_type == 'alphanumeric':
#         response.value_alphanumeric = field_value

#     elif field.field_type == 'image':
#         if file_value:
#             # delete old image
#             if response.value_image:
#                 response.value_image.delete(save=False)
#             response.value_image = file_value

#     else:
#         response.value_text = field_value



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_token_responses(request, token):
    """
    Delete all field responses for a specific token and the token itself (numeric token)
    """
    try:
        # Get the token object using the unified token lookup
        token_obj = get_token_object(token)
        if not token_obj:
            return Response(
                {"error": f"Token {token} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check user permission for deletion
        has_permission, error_message = check_user_permission(request, token_obj, "delete")
        if not has_permission:
            return Response(
                {"error": error_message}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Delete the submission if it exists (this will cascade delete all field responses)
        submission = FormSubmission.objects.filter(token=token_obj).first()
        if submission:
            submission.delete()
        
        # Delete the token itself
        token_obj.delete()
        
        return Response(
            {"message": f"Token {token} and all associated responses deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )
        
    except ValueError as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# views.py
# views.py
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from .serializers import (
    PasswordResetRequestSerializer, 
    ResendOTPSerializer,
    VerifyOTPSerializer, 
    PasswordResetConfirmSerializer,
   CustomSentRecordForIDSerializer,
)

# Get the custom user model
User = get_user_model()

class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = serializer.save()
        
        # Always return success for security
        return Response({
            "detail": "If the email exists in our system, an OTP has been sent to your email.",
            "message": "OTP sent successfully. Check your email.",
            "email": result['email'],
            "resend_allowed": True
        }, status=status.HTTP_200_OK)

class ResendOTPView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ResendOTPSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = serializer.save()
        
        return Response({
            "detail": result['message'],
            "message": "OTP resent successfully." if result['success'] else "Failed to resend OTP.",
            "email": result['email'],
            "success": result['success']
        }, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyOTPSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        return Response({
            "detail": "OTP verified successfully.",
            "message": "You can now reset your password.",
            "email": user.email
        }, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        return Response({
            "detail": "Password has been reset successfully.",
            "message": "You can now login with your new password."
        }, status=status.HTTP_200_OK)
#------------------------------------------23-10-2025-=------------------------------------------------------------------------------------------------
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Architecture

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def custom_sent_to_admin(request, architecture_id):
    """
    Mark architecture record as sent to admin
    Only allowed if:
    1. User is the creator of the architecture
    2. All tokens related to this architecture have is_used = 1
    """
    try:
        # Get the architecture object
        architecture = get_object_or_404(Architecture, id=architecture_id)
        
        # Check if current user is the creator of this architecture
        if architecture.created_by != request.user:
            return Response({
                'status': 'error',
                'message': 'Access denied',
                'details': 'You can only submit your own data for ID card processing. This record belongs to another user.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if there are any tokens related to this architecture
        # Use the correct related name: formtoken_set (default for FormToken model)
        tokens = architecture.formtoken_set.all()
        
        if tokens.exists():
            # Check if any token has is_used = False (not used)
            unused_tokens = tokens.filter(is_used=False)
            
            if unused_tokens.exists():
                unused_count = unused_tokens.count()
                total_tokens = tokens.count()
                
                return Response({
                    'status': 'error',
                    'message': 'You cannot send data to make ID card until you completely fill all tokens',
                    'details': f'You have {unused_count} unused tokens out of {total_tokens} total tokens. Please use all tokens before sending to admin.',
                    'unused_tokens_count': unused_count,
                    'total_tokens_count': total_tokens
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # If user is owner and (no tokens or all tokens are used), proceed with updating
        architecture.custm_sent_to_admin = True
        architecture.save()
        
        return Response({
            'status': 'success',
            'message': 'Data successfully sent for ID card processing!',
            'data': {
                'id': architecture.id,
                'name': architecture.name,
                'custm_sent_to_admin': True
            }
        }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Error processing your request: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)

#-------===========================23/3:40 pm-----------------============
# serializers.py

# views.py
class CustomSentRecordForIDViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet to get architectures with custom_sent_to_admin=True
    Only accessible by admin/superuser
    """
    serializer_class = CustomSentRecordForIDSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    queryset = Architecture.objects.filter(custm_sent_to_admin=True)


# views.py
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from django.contrib.auth import get_user_model
from student_api.models import Architecture
from .serializers import UserProfileSerializer
# This will get your CustomUser model
User = get_user_model()

class UserProfileView(generics.RetrieveAPIView):
    """
    Get user profile details
    - /api/profile/ - returns current authenticated user details
    - /api/profile/<architecture_id>/ - returns user who created the architecture (admin only)
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        architecture_id = self.kwargs.get('architecture_id')
        
        # If architecture_id is provided
        if architecture_id:
            return self.get_architecture_creator(user, architecture_id)
        
        # No architecture_id - return current user
        return user

    def get_architecture_creator(self, user, architecture_id):
        """
        Get the creator user of an architecture
        """
        # Check if user has admin role
        if not hasattr(user, 'role') or user.role != 'admin':
            raise PermissionDenied({
                "detail": "You do not have permission to perform this action.",
                "code": "admin_required",
                "message": "Only admin users can view creator details of architectures"
            })

        try:
            # Get architecture object
            architecture = Architecture.objects.get(id=architecture_id)
            
            # Get the creator from created_by field
            creator = architecture.created_by
            
            if not creator:
                raise NotFound({
                    "detail": "Creator information not available",
                    "code": "creator_not_found",
                    "message": f"This architecture (ID: {architecture_id}) does not have creator information",
                    "architecture_id": architecture_id,
                    "architecture_name": architecture.name
                })
            
            return creator
            
        except Architecture.DoesNotExist:
            raise NotFound({
                "detail": "Architecture not found",
                "code": "architecture_not_found",
                "message": f"No architecture found with ID: {architecture_id}",
                "architecture_id": architecture_id
            })
        except ValueError:
            raise NotFound({
                "detail": "Invalid architecture ID",
                "code": "invalid_id",
                "message": f"'{architecture_id}' is not a valid architecture ID"
            })
# views.py
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from .models import Architecture
from .serializers import ArchitectureSerializer1

class ArchitectureDetailView(generics.RetrieveAPIView):
    """
    Get architecture details by ID
    - Only returns exact model fields
    - Only accessible to admin users
    """
    serializer_class = ArchitectureSerializer1
    permission_classes = [permissions.IsAuthenticated]
    queryset = Architecture.objects.all()
    lookup_field = 'id'

    def check_permissions(self, request):
        """Check if user has admin role"""
        super().check_permissions(request)
        
        # Check if user is admin
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            raise PermissionDenied("Only admin users can access architecture details")

    def get_object(self):
        try:
            architecture_id = self.kwargs.get('id')
            return Architecture.objects.get(id=architecture_id)
        except Architecture.DoesNotExist:
            raise NotFound("Architecture not found")
        except ValueError:
            raise NotFound("Invalid architecture ID")
    


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from .models import Architecture
from .serializers import ArchitectureSerializer
import time

class IsAdminUser(IsAuthenticated):
    """
    Custom permission to only allow admin users to access the view.
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if not request.user.is_staff:
            raise PermissionDenied("Only admin users can access this resource.")
        return True

class statusArchitecture(viewsets.ModelViewSet):
    queryset = Architecture.objects.all()
    serializer_class = ArchitectureSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def _get_new_entries_count(self, exclude_ids=[]):
        """
        Count ONLY new entries where custm_sent_to_admin is True
        Optionally exclude specific IDs
        """
        queryset = Architecture.objects.filter(
            custm_sent_to_admin=True,
            is_active=True
        )
        
        if exclude_ids:
            queryset = queryset.exclude(id__in=exclude_ids)
            
        return queryset.count()
    
    # Status update actions - DO NOT modify custm_sent_to_admin
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_pending(self, request, pk=None):
        try:
            architecture = self.get_object()
            if not architecture.is_active:
                raise ValidationError("Cannot update status of inactive architecture.")
            
            # Check if this was a new entry (for counter only)
            was_new_entry = architecture.custm_sent_to_admin
            
            architecture.mark_as_pending()
            
            # Get updated count - exclude this ID if it was a new entry
            exclude_ids = [architecture.id] if was_new_entry else []
            new_entries_count = self._get_new_entries_count(exclude_ids)
            
            return Response({
                'status': 'success',
                'message': 'marked as pending',
                'architecture_id': architecture.id,
                'current_status': architecture.get_status_display(),
                'was_new_entry': was_new_entry,
                'should_exclude_from_count': was_new_entry,  # Tell frontend to exclude this
                'new_entries_count': new_entries_count
            })
        except ObjectDoesNotExist:
            return Response(
                {'error': 'Architecture not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_accepted(self, request, pk=None):
        try:
            architecture = self.get_object()
            if not architecture.is_active:
                raise ValidationError("Cannot update status of inactive architecture.")
            
            if architecture.is_accepted():
                return Response(
                    {'warning': 'Architecture is already accepted'}, 
                    status=status.HTTP_200_OK
                )
            
            # Check if this was a new entry (for counter only)
            was_new_entry = architecture.custm_sent_to_admin
            
            architecture.mark_as_accepted()
            
            # Get updated count - exclude this ID if it was a new entry
            exclude_ids = [architecture.id] if was_new_entry else []
            new_entries_count = self._get_new_entries_count(exclude_ids)
            
            return Response({
                'status': 'success',
                'message': 'marked as accepted',
                'architecture_id': architecture.id,
                'current_status': architecture.get_status_display(),
                'was_new_entry': was_new_entry,
                'should_exclude_from_count': was_new_entry,
                'new_entries_count': new_entries_count
            })
        except ObjectDoesNotExist:
            return Response(
                {'error': 'Architecture not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_rejected(self, request, pk=None):
        try:
            architecture = self.get_object()
            if not architecture.is_active:
                raise ValidationError("Cannot update status of inactive architecture.")
            
            if architecture.is_rejected():
                return Response(
                    {'warning': 'Architecture is already rejected'}, 
                    status=status.HTTP_200_OK
                )
            
            # Check if this was a new entry (for counter only)
            was_new_entry = architecture.custm_sent_to_admin
            
            architecture.mark_as_rejected()
            
            # Get updated count - exclude this ID if it was a new entry
            exclude_ids = [architecture.id] if was_new_entry else []
            new_entries_count = self._get_new_entries_count(exclude_ids)
            
            return Response({
                'status': 'success',
                'message': 'marked as rejected',
                'architecture_id': architecture.id,
                'current_status': architecture.get_status_display(),
                'was_new_entry': was_new_entry,
                'should_exclude_from_count': was_new_entry,
                'new_entries_count': new_entries_count
            })
        except ObjectDoesNotExist:
            return Response(
                {'error': 'Architecture not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_completed(self, request, pk=None):
        try:
            architecture = self.get_object()
            if not architecture.is_active:
                raise ValidationError("Cannot update status of inactive architecture.")
            
            if not architecture.is_accepted():
                return Response(
                    {'error': 'Architecture must be accepted before marking as completed'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if architecture.is_completed():
                return Response(
                    {'warning': 'Architecture is already completed'}, 
                    status=status.HTTP_200_OK
                )
            
            # Check if this was a new entry (for counter only)
            was_new_entry = architecture.custm_sent_to_admin
            
            architecture.mark_as_completed()
            
            # Get updated count - exclude this ID if it was a new entry
            exclude_ids = [architecture.id] if was_new_entry else []
            new_entries_count = self._get_new_entries_count(exclude_ids)
            
            return Response({
                'status': 'success',
                'message': 'marked as completed',
                'architecture_id': architecture.id,
                'current_status': architecture.get_status_display(),
                'was_new_entry': was_new_entry,
                'should_exclude_from_count': was_new_entry,
                'new_entries_count': new_entries_count
            })
        except ObjectDoesNotExist:
            return Response(
                {'error': 'Architecture not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Get new entries count with optional exclusion
    @action(detail=False, methods=['get', 'post'], permission_classes=[IsAdminUser])
    def new_entries_count(self, request):
        """
        Get count of ONLY new entries (custm_sent_to_admin = True)
        Optionally exclude specific IDs from the count
        """
        exclude_ids = request.data.get('exclude_ids', []) if request.method == 'POST' else []
        
        new_entries_count = self._get_new_entries_count(exclude_ids)
        
        return Response({
            'new_entries_count': new_entries_count,
            'excluded_ids': exclude_ids,
            'message': f'Found {new_entries_count} new entries'
        })
    
    # Mark entries as seen (frontend only - no DB changes)
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def mark_entries_seen(self, request):
        """
        Mark specific entries as seen by admin (frontend only)
        Returns updated count excluding these IDs
        """
        architecture_ids = request.data.get('architecture_ids', [])
        
        if not architecture_ids:
            return Response(
                {'error': 'architecture_ids field is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Count how many of these were actually new entries
        new_entries_to_exclude = Architecture.objects.filter(
            id__in=architecture_ids,
            custm_sent_to_admin=True,
            is_active=True
        ).count()
        
        # Return count excluding these IDs
        current_new_entries_count = self._get_new_entries_count(architecture_ids)
        
        return Response({
            'status': 'success',
            'message': f'Marked {new_entries_to_exclude} entries as seen',
            'marked_count': new_entries_to_exclude,
            'excluded_ids': architecture_ids,
            'new_entries_count': current_new_entries_count
        })
    
    # Get all new entries (for initial load)
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def new_entries(self, request):
        """
        Get all new entries (for initial frontend state)
        """
        new_entries = Architecture.objects.filter(
            custm_sent_to_admin=True,
            is_active=True
        ).values_list('id', flat=True)
        
        return Response({
            'new_entry_ids': list(new_entries),
            'count': len(new_entries)
        })
    
    # Filter by status
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def by_status(self, request):
        status_param = request.query_params.get('status')
        
        if not status_param:
            return Response(
                {'error': 'Status parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            status_value = int(status_param)
            if status_value not in [0, 1, 2, 3]:
                return Response(
                    {'error': 'Status must be 0 (Pending), 1 (Accepted), 2 (Rejected), or 3 (Completed)'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            architectures = Architecture.objects.filter(status=status_value, is_active=True)
            
            serializer = self.get_serializer(architectures, many=True)
            return Response({
                'count': architectures.count(),
                'status': status_value,
                'status_display': dict(Architecture.STATUS_CHOICES).get(status_value, 'Unknown'),
                'results': serializer.data
            })
            
        except ValueError:
            return Response(
                {'error': 'Status parameter must be a valid integer (0, 1, 2, 3)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Additional action: Get status statistics
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def status_stats(self, request):
        """
        Get statistics for all status types
        """
        stats = {}
        for status_value, status_display in Architecture.STATUS_CHOICES:
            count = Architecture.objects.filter(status=status_value, is_active=True).count()
            stats[status_display.lower()] = count
        
        total = Architecture.objects.filter(is_active=True).count()
        stats['total'] = total
        
        # Add new entries count to stats
        stats['new_entries'] = self._get_new_entries_count()
        
        return Response(stats)

























from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import (
    Statistic, PortfolioItem, Service, Testimonial, 
    Client, Slide1, Slide2
)
from .serializers import (
    StatisticSerializer, PortfolioItemSerializer,
    ServiceSerializer, TestimonialSerializer, ClientSerializer,
    Slide1Serializer, Slide2Serializer,
    Slide1DetailSerializer, Slide2DetailSerializer
)

# Get the custom user model
User = get_user_model()

# Statistic ViewSet
class StatisticViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Statistic model with full CRUD operations
    """
    queryset = Statistic.objects.all()
    serializer_class = StatisticSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Statistic deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

# PortfolioItem ViewSet
class PortfolioItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PortfolioItem model with full CRUD operations
    """
    queryset = PortfolioItem.objects.all().order_by('-id')
    serializer_class = PortfolioItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Portfolio item deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get portfolio items by category
        """
        category = request.query_params.get('category', None)
        if category:
            items = PortfolioItem.objects.filter(category=category)
            serializer = self.get_serializer(items, many=True)
            return Response(serializer.data)
        return Response([])

# Service ViewSet
class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Service model with full CRUD operations
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Service deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

# Testimonial ViewSet
class TestimonialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Testimonial model with full CRUD operations
    """
    queryset = Testimonial.objects.all().order_by('-id')
    serializer_class = TestimonialSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Testimonial deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

# Client ViewSet
class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Client model with full CRUD operations
    """
    queryset = Client.objects.all().order_by('name')
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Client deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

# Slide1 ViewSet
class Slide1ViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Slide1 model with full CRUD operations
    """
    queryset = Slide1.objects.all().order_by('-id')
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return Slide1DetailSerializer
        return Slide1Serializer
    
    def perform_create(self, serializer):
        # Automatically assign the current user
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Slide1 deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'])
    def my_slides(self, request):
        """
        Get current user's slides
        """
        if request.user.is_authenticated:
            slides = Slide1.objects.filter(user=request.user).order_by('-id')
            serializer = Slide1DetailSerializer(slides, many=True)
            return Response(serializer.data)
        return Response({"detail": "Authentication required"}, status=401)

# Slide2 ViewSet
class Slide2ViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Slide2 model with full CRUD operations
    """
    queryset = Slide2.objects.all().order_by('-id')
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return Slide2DetailSerializer
        return Slide2Serializer
    
    def perform_create(self, serializer):
        # Automatically assign the current user
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Slide2 deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'])
    def my_slides(self, request):
        """
        Get current user's slides
        """
        if request.user.is_authenticated:
            slides = Slide2.objects.filter(user=request.user).order_by('-id')
            serializer = Slide2DetailSerializer(slides, many=True)
            return Response(serializer.data)
        return Response({"detail": "Authentication required"}, status=401)





from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from .models import Architecture
from .serializers import ArchitectureSerializer

class CustomerDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get counts by status
        status_counts = Architecture.objects.filter(
            created_by=user
        ).values('status').annotate(
            count=Count('id')
        )
        
        # Convert to dictionary
        counts_dict = {item['status']: item['count'] for item in status_counts}
        
        # Get total counts
        total_forms = Architecture.objects.filter(created_by=user).count()
        pending_forms = counts_dict.get(Architecture.STATUS_PENDING, 0)
        approved_forms = counts_dict.get(Architecture.STATUS_ACCEPTED, 0)
        rejected_forms = counts_dict.get(Architecture.STATUS_REJECTED, 0)
        completed_forms = counts_dict.get(Architecture.STATUS_COMPLETED, 0)
        
        # Get recent forms (last 5)
        recent_forms = Architecture.objects.filter(
            created_by=user
        ).order_by('-created_at')[:5]
        
        # Serialize recent forms
        serializer = ArchitectureSerializer(recent_forms, many=True)
        
        # Calculate approval rate
        approval_rate = 0
        if total_forms > 0:
            approval_rate = round((approved_forms / total_forms) * 100)
        
        data = {
            'stats': {
                'totalForms': total_forms,
                'pendingForms': pending_forms,
                'approvedForms': approved_forms,
                'rejectedForms': rejected_forms,
                'completedForms': completed_forms,
                'approvalRate': approval_rate
            },
            'recentForms': serializer.data,
            'user': {
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'email': user.email
            }
        }
        
        return Response(data, status=status.HTTP_200_OK)


class ArchitectureStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get status summary
        architectures = Architecture.objects.filter(created_by=user)
        
        data = {
            'status_choices': [
                {'value': 0, 'label': 'Pending'},
                {'value': 1, 'label': 'Accepted'},
                {'value': 2, 'label': 'Rejected'},
                {'value': 3, 'label': 'Completed'}
            ],
            'counts': {
                'total': architectures.count(),
                'by_status': {
                    '0': architectures.filter(status=0).count(),
                    '1': architectures.filter(status=1).count(),
                    '2': architectures.filter(status=2).count(),
                    '3': architectures.filter(status=3).count()
                }
            }
        }
        
        return Response(data, status=status.HTTP_200_OK)



























# views.py (add these views)



# registration_views.py
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
import logging

from .serializers import (
    RegistrationInitSerializer,
    RegistrationOTPVerifySerializer,
    RegistrationOTPResendSerializer
)
from .utils.otp_utils import (
    generate_otp,
    send_registration_otp_email,
    store_registration_data,
    delete_registration_data,
    store_registration_otp,
    verify_registration_otp,
    can_resend_otp
)

logger = logging.getLogger(__name__)
User = get_user_model()

class RegistrationInitView(APIView):
    """
    First step: Initialize registration and send OTP
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegistrationInitSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            username = serializer.validated_data['username']
            
            # Store all registration data in cache (10 minutes)
            registration_data = {
                'full_name': serializer.validated_data['full_name'],
                'username': username,
                'email': email,
                'phone_number': serializer.validated_data.get('phone_number', ''),
                'college_company': serializer.validated_data['college_company'],
                'address': serializer.validated_data['address'],
                'role': serializer.validated_data.get('role', 'customer'),
                'password': serializer.validated_data['password']  # Store password
            }
            store_registration_data(email, registration_data, timeout=600)
            
            # Generate and store OTP
            otp = generate_otp()
            store_registration_otp(email, otp)
            
            # Log OTP for development
            logger.info(f"Generated OTP for {email}: {otp}")
            
            # Try to send OTP email
            try:
                send_registration_otp_email(email, username, otp)
                email_sent = True
                email_message = "OTP sent successfully to your email"
            except Exception as e:
                logger.error(f"Failed to send OTP email: {str(e)}")
                email_sent = False
                email_message = "Could not send email. Please check your email configuration."
                
                # In development, return OTP for testing
                if settings.DEBUG:
                    return Response(
                        {
                            'message': 'OTP generated successfully (Development Mode)',
                            'email': email,
                            'otp': otp,  # Only in DEBUG mode!
                            'expires_in': '1 minute',
                            'resend_allowed': True,
                            'email_sent': False,
                            'warning': 'Email configuration issue. Use this OTP for testing.'
                        },
                        status=status.HTTP_200_OK
                    )
            
            return Response(
                {
                    'message': email_message,
                    'email': email,
                    'expires_in': '1 minute',
                    'resend_allowed': True,
                    'email_sent': email_sent
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegistrationVerifyView(APIView):
    """
    Second step: Verify OTP and create user
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegistrationOTPVerifySerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            registration_data = serializer.validated_data['registration_data']
            
            # Verify OTP
            otp_code = request.data.get('otp_code')
            is_valid, message = verify_registration_otp(email, otp_code)
            
            if not is_valid:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Delete registration data from cache
            delete_registration_data(email)
            
            # Create the user
            user = User.objects.create_user(
                username=registration_data['username'],
                email=registration_data['email'],
                password=registration_data['password'],
                first_name=registration_data['full_name'].split()[0] if registration_data['full_name'] else '',
                last_name=' '.join(registration_data['full_name'].split()[1:]) if len(registration_data['full_name'].split()) > 1 else ''
            )
            
            # Set additional fields if they exist in your User model
            if hasattr(user, 'phone_number'):
                user.phone_number = registration_data.get('phone_number', '')
            
            if hasattr(user, 'college_company'):
                user.college_company = registration_data.get('college_company', '')
            
            if hasattr(user, 'address'):
                user.address = registration_data.get('address', '')
            
            if hasattr(user, 'role'):
                user.role = registration_data.get('role', 'customer')
            
            # If you have approval system
            if hasattr(user, 'is_approved'):
                user.is_approved = False
                user.is_active = True  # Active but not approved
            
            user.save()
            
            # Generate JWT tokens (optional - user might need to wait for approval)
            refresh = RefreshToken.for_user(user)
            
            return Response(
                {
                    'message': 'Registration successful! Your account is pending admin approval.',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'full_name': registration_data['full_name']
                    },
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    },
                    'requires_approval': True
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegistrationResendOTPView(APIView):
    """
    Resend OTP for registration
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegistrationOTPResendSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            # Check rate limiting
            can_resend, message = can_resend_otp(email)
            if not can_resend:
                return Response(
                    {'error': message},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # Get registration data
            registration_data = cache.get(f"registration_data_{email}")
            
            if not registration_data:
                return Response(
                    {'error': 'Registration session expired. Please start over.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate new OTP
            otp = generate_otp()
            store_registration_otp(email, otp)
            
            # Log OTP for development
            logger.info(f"Resent OTP for {email}: {otp}")
            
            # Send OTP email
            try:
                send_registration_otp_email(email, registration_data['username'], otp)
                
                # Update resend count
                cache_key = f"otp_resend_count_{email}"
                resend_count = cache.get(cache_key, 0)
                cache.set(cache_key, resend_count + 1, timeout=600)  # 10 minutes
                
                return Response(
                    {
                        'message': 'OTP resent successfully',
                        'email': email,
                        'expires_in': '1 minute'
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                logger.error(f"Failed to resend OTP: {str(e)}")
                
                if settings.DEBUG:
                    return Response(
                        {
                            'message': 'OTP generated (Development Mode)',
                            'email': email,
                            'otp': otp,
                            'expires_in': '1 minute'
                        },
                        status=status.HTTP_200_OK
                    )
                
                return Response(
                    {'error': 'Failed to send OTP email. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_architecture(request, architecture_id):
    """
    Custom endpoint to delete an architecture
    Only the owner (creator) or admin users can delete
    """
    try:
        # Get the architecture
        architecture = get_object_or_404(Architecture, id=architecture_id)
        
        # Check if user is admin or owner
        is_admin = request.user.is_staff or request.user.is_superuser
        is_owner = architecture.created_by_id == request.user.id
        
        if not (is_admin or is_owner):
            return Response(
                {"error": "You don't have permission to delete this architecture"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Set children's parent to null
        architecture.children.update(parent=None)
        
        # Delete tokens if they exist (try different possible related names)
        try:
            architecture.formtoken_set.all().delete()
        except AttributeError:
            try:
                architecture.tokens.all().delete()
            except AttributeError:
                pass
        
        # Store name for response
        arch_name = architecture.name
        arch_id = architecture.id
        
        # Delete the architecture
        architecture.delete()
        
        return Response(
            {
                "success": True,
                "message": f"Architecture '{arch_name}' deleted successfully",
                "deleted_id": arch_id
            },
            status=status.HTTP_200_OK
        )
        
    except Architecture.DoesNotExist:
        return Response(
            {"error": "Architecture not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error deleting architecture: {str(e)}")
        return Response(
            {"error": f"Failed to delete: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from django.contrib.auth import get_user_model
from .serializers import UserProfileSerializer

User = get_user_model()

class useridprofile(generics.RetrieveAPIView):
    """
    Get user profile details by user ID
    - GET /api/user-profile/<user_id>/ - returns specific user profile (admin only)
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'user_id'

    def get_queryset(self):
        """
        Override queryset to ensure only admin can access other users
        """
        user = self.request.user
        
        # Check if user has admin role
        if not hasattr(user, 'role') or user.role != 'admin':
            raise PermissionDenied({
                "detail": "You do not have permission to perform this action.",
                "code": "admin_required",
                "message": "Only admin users can view other users' profiles"
            })
        
        # Admin can access all users
        return User.objects.all()

    def get_object(self):
        """
        Get user by ID from URL
        """
        user = self.request.user
        user_id = self.kwargs.get('user_id')
        
        # Check if user has admin role
        if not hasattr(user, 'role') or user.role != 'admin':
            raise PermissionDenied({
                "detail": "You do not have permission to perform this action.",
                "code": "admin_required",
                "message": "Only admin users can view other users' profiles"
            })

        try:
            # Get user by ID
            target_user = User.objects.get(id=user_id)
            return target_user
            
        except User.DoesNotExist:
            raise NotFound({
                "detail": "User not found",
                "code": "user_not_found",
                "message": f"No user found with ID: {user_id}",
                "user_id": user_id
            })
        except (ValueError, TypeError):
            raise NotFound({
                "detail": "Invalid user ID",
                "code": "invalid_id",
                "message": f"'{user_id}' is not a valid user ID"
            })