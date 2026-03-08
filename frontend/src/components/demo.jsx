// // components/ProtectedRoute.jsx
// import { useState, useEffect } from "react";
// import Login from "./LoginClient/Login";
// import Register from "./LoginClient/Register";

// const ProtectedRoute = ({ children, allowedRoles = [] }) => {
//   const [user, setUser] = useState(null);
//   const [showLoginModal, setShowLoginModal] = useState(false);
//   const [showRegisterModal, setShowRegisterModal] = useState(false);
//   const [isCheckingAuth, setIsCheckingAuth] = useState(true);

//   useEffect(() => {
//     checkAuthentication();
//   }, []);

//   const checkAuthentication = () => {
//     const userData = JSON.parse(localStorage.getItem("user"));
//     setUser(userData);
//     setIsCheckingAuth(false);
//   };

//   const handleLoginSuccess = (userData) => {
//     localStorage.setItem("user", JSON.stringify(userData));
//     setUser(userData);
//     setShowLoginModal(false);
//   };

//   const handleRegisterSuccess = () => {
//     setShowRegisterModal(false);
//     setShowLoginModal(true);
//   };

//   const handleCloseLoginModal = () => {
//     setShowLoginModal(false);
//   };

//   const handleCloseRegisterModal = () => {
//     setShowRegisterModal(false);
//   };

//   const handleSwitchToRegister = () => {
//     setShowLoginModal(false);
//     setShowRegisterModal(true);
//   };

//   const handleSwitchToLogin = () => {
//     setShowRegisterModal(false);
//     setShowLoginModal(true);
//   };

//   // Show loading while checking authentication
//   if (isCheckingAuth) {
//     return (
//       <div className="min-h-screen flex items-center justify-center bg-gray-50">
//         <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
//       </div>
//     );
//   }

//   // If not authenticated, show content with login overlay
//   if (!user) {
//     return (
//       <>
//         {/* Render the protected content (blurred/disabled) */}
//         <div className={`relative ${!user ? 'filter blur-sm pointer-events-none' : ''}`}>
//           {children}
//         </div>

//         {/* Login Overlay */}
//         {!user && (
//           <div className="fixed inset-0 z-50 flex items-center justify-center  bg-opacity-50">
//             <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
//               <div className="p-6">
//                 <div className="text-center mb-6">
//                   <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
//                     <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                       <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
//                     </svg>
//                   </div>
//                   <h3 className="text-2xl font-bold text-gray-900 mb-2">Sign In Required</h3>
//                   <p className="text-gray-600">
//                     Please log in to access this content
//                   </p>
//                 </div>

//                 <div className="space-y-4">
//                   <button
//                     onClick={() => setShowLoginModal(true)}
//                     className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2"
//                   >
//                     <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                       <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
//                     </svg>
//                     <span>Sign In to Continue</span>
//                   </button>

//                   <button
//                     onClick={() => setShowRegisterModal(true)}
//                     className="w-full border border-gray-300 text-gray-700 py-3 px-4 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
//                   >
//                     Create New Account
//                   </button>
//                 </div>

//                 <div className="mt-6 text-center">
//                   <p className="text-sm text-gray-500">
//                     By continuing, you agree to our Terms of Service
//                   </p>
//                 </div>
//               </div>
//             </div>
//           </div>
//         )}

//         {/* Login Modal */}
//         {showLoginModal && (
//           <div className="fixed inset-0 z-[60] overflow-y-auto">
//             <div className="fixed inset-0 bg-opacity-50 transition-opacity"></div>
//             <div className="flex min-h-full items-center justify-center p-4">
//               <div className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
//                 <Login 
//                   onClose={handleCloseLoginModal}
//                   onSwitchToRegister={handleSwitchToRegister}
//                   onLoginSuccess={handleLoginSuccess}
//                 />
//               </div>
//             </div>
//           </div>
//         )}

//         {/* Register Modal */}
//         {showRegisterModal && (
//           <div className="fixed inset-0 z-[60] overflow-y-auto">
//             <div className="fixed inset-0  bg-opacity-50 transition-opacity"></div>
//             <div className="flex min-h-full items-center justify-center p-4">
//               <div className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
//                 <Register 
//                   onClose={handleCloseRegisterModal}
//                   onSwitchToLogin={handleSwitchToLogin}
//                   onRegisterSuccess={handleRegisterSuccess}
//                 />
//               </div>
//             </div>
//           </div>
//         )}
//       </>
//     );
//   }

//   // Check roles if user is authenticated
//   if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
//     return (
//       <div className="min-h-screen flex items-center justify-center bg-gray-50">
//         <div className="bg-white p-8 rounded-lg shadow-md text-center max-w-md">
//           <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
//             <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z" />
//             </svg>
//           </div>
//           <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
//           <p className="text-gray-600 mb-4">
//             You don't have permission to access this page. 
//           </p>
//           <p className="text-sm text-gray-500 mb-2">
//             Your role: <span className="font-semibold">{user.role}</span>
//           </p>
//           <p className="text-sm text-gray-500 mb-6">
//             Required: {allowedRoles.join(", ")}
//           </p>
//           <button
//             onClick={() => window.history.back()}
//             className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors"
//           >
//             Go Back
//           </button>
//         </div>
//       </div>
//     );
//   }

//   // User is authenticated and has required role
//   return children;
// };

// export default ProtectedRoute;


from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging
import base64

logger = logging.getLogger(__name__)

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


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_token_responses(request, token):
    """
    View or edit all field responses for a specific token (numeric token)
    Only the user who owns the token can access or modify it
    """
    try:
        logger.info(f"=== DEBUG START: User {request.user.id} ({request.user.email}) accessing token {token} ===")
        
        token_obj = get_token_object(token)
        
        if not token_obj:
            logger.warning(f"Token {token} not found")
            return Response(
                {"error": f"Token {token} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(f"Token object found: ID={token_obj.id}, token={token_obj.token}")
        
        # Get existing submission
        submission = FormSubmission.objects.filter(token=token_obj).first()
        
        if submission:
            logger.info(f"Submission found: ID={submission.id}")
            logger.info(f"Submission student: {submission.student}")
            if submission.student:
                logger.info(f"Submission student details: ID={submission.student.id}, Email={submission.student.email}, Name={submission.student.full_name}")
            else:
                logger.info("Submission has NO student assigned")
        else:
            logger.info("No submission found for this token")
        
        # If no submission exists, create one and assign current user as owner
        if not submission:
            logger.info(f"Creating new submission for user {request.user.id}")
            submission, created = FormSubmission.objects.get_or_create(
                token=token_obj,
                defaults={
                    'form': token_obj.form,
                    'student': request.user
                }
            )
            if created:
                logger.info(f"Created new submission {submission.id}")
        
        # If submission exists but no student assigned, assign current user
        if submission and not submission.student:
            logger.info(f"Assigning submission {submission.id} to user {request.user.id}")
            submission.student = request.user
            submission.save()
        
        # CRITICAL: Final ownership check
        logger.info(f"=== OWNERSHIP CHECK ===")
        logger.info(f"Request User: ID={request.user.id}, Email={request.user.email}")
        logger.info(f"Submission Student: ID={submission.student.id if submission.student else 'None'}, Email={submission.student.email if submission.student else 'None'}")
        
        if submission.student != request.user:
            logger.warning(f"OWNERSHIP VIOLATION: User {request.user.id} != Submission Student {submission.student.id}")
            logger.warning(f"User {request.user.id} tried to access token owned by {submission.student.id}")
            
            # ADDITIONAL DEBUG: Check if there are multiple submissions
            all_submissions = FormSubmission.objects.filter(token=token_obj)
            logger.warning(f"Found {all_submissions.count()} submissions for this token")
            for sub in all_submissions:
                logger.warning(f"  - Submission {sub.id}: Student {sub.student.id if sub.student else 'None'}")
            
            return Response(
                {
                    "error": "Access Denied", 
                    "message": "You cannot view or edit responses for this token as it belongs to another user.",
                    "detail": f"Token {normalize_token(token)} is assigned to {submission.student.full_name} ({submission.student.email})"
                }, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        logger.info(f"=== ACCESS GRANTED: Ownership verified ===")
        
        # Handle requests
        if request.method == 'GET':
            return handle_get_request(request, token_obj, submission, normalize_token(token))
        
        elif request.method in ['PUT', 'PATCH']:
            return handle_update_request(request, token_obj, submission, normalize_token(token))
        
    except ValueError as e:
        logger.error(f"Value error for token {token}: {str(e)}")
        return Response(
            {"error": f"Invalid token format: {str(e)}"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error in edit_token_responses for token {token}: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Internal server error: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def handle_get_request(request, token_obj, submission, token):
    """
    Handle GET request - retrieve all field responses safely
    """
    # Ownership is already verified in the main function
    
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
        'submission_id': submission.id,
        'form_id': token_obj.form.id,
        'form_title': token_obj.form.title,
        'architecture_id': token_obj.architecture.id,
        'architecture_name': token_obj.architecture.name,
        'student_id': submission.student.id if submission.student else None,
        'student_name': submission.student.full_name if submission.student else None,
        'student_email': submission.student.email if submission.student else None,
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


def get_safe_field_value(response, field_type, request):
    """
    Safely extract field value without causing encoding errors
    FIXED: Handle missing get_value() method
    """
    try:
        # For image fields, return URL instead of binary data
        if field_type == 'image' and response.value_image:
            if hasattr(response.value_image, 'url'):
                return request.build_absolute_uri(response.value_image.url)
            return str(response.value_image)
        
        # FIX: Check if get_value method exists, otherwise use direct field access
        if hasattr(response, 'get_value'):
            raw_value = response.get_value()
        else:
            # Fallback: Get value based on field type
            if field_type == 'number':
                raw_value = response.value_number
            elif field_type == 'date':
                raw_value = response.value_date
            elif field_type == 'checkbox':
                raw_value = response.value_boolean
            elif field_type == 'alphanumeric':
                raw_value = response.value_alphanumeric
            elif field_type == 'image':
                raw_value = response.value_image
            else:  # text, dropdown, etc.
                raw_value = response.value_text
        
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
        
        # Ensure the value is JSON-serializable
        if isinstance(raw_value, (int, float, bool, str, type(None))):
            return raw_value
        
        # Convert other types to string
        return str(raw_value)
        
    except Exception as e:
        logger.warning(f"Error getting safe value for field {response.field.id}: {e}")
        return None


def handle_update_request(request, token_obj, submission, token):
    """
    Handle PUT/PATCH requests - update field responses
    Only the user who owns the submission can update it
    """
    # Ownership is already verified in the main function
    
    # Update field responses within a transaction
    with transaction.atomic():
        updated_responses = []
        errors = []
        
        # Get all active fields for the form
        form_fields = FormField.objects.filter(
            form=token_obj.form,
            is_active=True
        )
        
        for field in form_fields:
            field_key = f'field_{field.id}'
            field_value = request.data.get(field_key)
            
            # Skip if field value is not provided (for PATCH) or if it's None
            if field_value is None and request.method == 'PATCH':
                continue
            
            # For required fields, ensure value is provided
            if field.is_required and field_value in [None, '']:
                errors.append(f"Field '{field.label}' is required")
                continue
            
            try:
                # Get or create the field response
                response, created = FieldResponse.objects.get_or_create(
                    submission=submission,
                    field=field,
                    defaults={'created_by': request.user if request.user.is_authenticated else None}
                )
                
                # Update the response value based on field type with validation
                update_response_value(response, field, field_value, errors)
                
                if errors and errors[-1].startswith(f"Field '{field.label}'"):
                    # Skip saving if there was a validation error for this field
                    continue
                
                response.save()
                
                # Get the display value for response
                try:
                    display_value = get_safe_field_value(response, field.field_type, request)
                except:
                    display_value = field_value
                
                updated_responses.append({
                    'field_id': field.id,
                    'field_label': field.label,
                    'field_type': field.field_type,
                    'value': display_value,
                    'response_id': response.id,
                    'updated': True
                })
                
            except Exception as e:
                errors.append(f"Error updating field '{field.label}': {str(e)}")
                continue
        
        if errors:
            return Response({
                "error": "Some fields could not be updated",
                "details": errors,
                "updated_responses": updated_responses
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            "message": f"Successfully updated {len(updated_responses)} field responses for token {token}",
            "updated_responses": updated_responses,
            "submission_id": submission.id,
            "token": token,
            "form_title": token_obj.form.title
        })


def update_response_value(response, field, field_value, errors):
    """
    Update the response value with proper validation
    """
    if field.field_type == 'number':
        if field_value not in [None, '']:
            try:
                response.value_number = float(field_value)
            except (ValueError, TypeError):
                errors.append(f"Field '{field.label}' must be a valid number")
        else:
            response.value_number = None
    
    elif field.field_type == 'date':
        if field_value not in [None, '']:
            response.value_date = field_value
        else:
            response.value_date = None
    
    elif field.field_type == 'checkbox':
        if field_value not in [None, '']:
            # Convert string to boolean
            if isinstance(field_value, str):
                field_value = field_value.lower() in ['true', '1', 'yes', 'on']
            response.value_boolean = bool(field_value)
        else:
            response.value_boolean = False
    
    elif field.field_type == 'alphanumeric':
        response.value_alphanumeric = field_value
    
    elif field.field_type == 'image':
        # For image fields, we expect a file path or URL in this context
        # For actual file uploads, you'd need a different approach
        response.value_text = field_value
    
    else:  # text, dropdown, and others
        response.value_text = field_value


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_token_responses(request, token):
    """
    Delete all field responses for a specific token and the token itself (numeric token)
    Only the user who owns the token can delete it
    """
    try:
        logger.info(f"=== DEBUG DELETE: User {request.user.id} ({request.user.email}) deleting token {token} ===")
        
        token_obj = get_token_object(token)
        
        if not token_obj:
            logger.warning(f"Token {token} not found for deletion")
            return Response(
                {"error": f"Token {token} not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the submission and check ownership
        submission = FormSubmission.objects.filter(token=token_obj).first()
        
        # If no submission exists, check if user can delete the token
        if not submission:
            logger.warning(f"No submission found for token {token} during deletion")
            return Response(
                {
                    "error": "Delete Permission Denied",
                    "message": "You cannot delete this token.",
                    "detail": "This token is not assigned to any user and cannot be deleted."
                }, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Debug logging
        logger.info(f"Submission found: ID={submission.id}")
        if submission.student:
            logger.info(f"Submission student: ID={submission.student.id}, Email={submission.student.email}")
        
        # Check ownership - user must own the submission to delete it
        if submission.student != request.user:
            logger.warning(f"DELETE OWNERSHIP VIOLATION: User {request.user.id} != Submission Student {submission.student.id}")
            
            # ADDITIONAL DEBUG: Check if there are multiple submissions
            all_submissions = FormSubmission.objects.filter(token=token_obj)
            logger.warning(f"Found {all_submissions.count()} submissions for this token")
            for sub in all_submissions:
                logger.warning(f"  - Submission {sub.id}: Student {sub.student.id if sub.student else 'None'}")
            
            return Response(
                {
                    "error": "Delete Permission Denied",
                    "message": "You cannot delete this token.",
                    "detail": f"This token belongs to {submission.student.full_name}. You can only delete your own tokens."
                }, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        logger.info(f"=== DELETE GRANTED: User {request.user.id} owns token {token} ===")
        
        # Delete the submission (this will cascade delete all field responses)
        submission.delete()
        
        # Delete the token itself
        token_obj.delete()
        
        logger.info(f"Successfully deleted token {token} and all associated data")
        
        return Response(
            {"message": f"Token {normalize_token(token)} and all associated responses deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )
        
    except ValueError as e:
        logger.error(f"Value error during delete for token {token}: {str(e)}")
        return Response(
            {"error": f"Invalid token format: {str(e)}"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error in delete_token_responses for token {token}: {str(e)}", exc_info=True)
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================================================
# DEBUG AND REPAIR ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_token_ownership(request, token):
    """
    Debug endpoint to check token ownership
    """
    try:
        normalized_token = normalize_token(token)
        
        # Check all possible token matches
        tokens = FormToken.objects.filter(token=normalized_token)
        if not tokens:
            tokens = FormToken.objects.all()
            matched_tokens = []
            for t in tokens:
                try:
                    if normalize_token(t.token) == normalized_token:
                        matched_tokens.append(t)
                except:
                    continue
            tokens = matched_tokens
        
        result = {
            'request_user': {
                'id': request.user.id,
                'email': request.user.email,
                'full_name': request.user.full_name
            },
            'search_token': token,
            'normalized_token': normalized_token,
            'found_tokens': [],
            'submissions': []
        }
        
        for token_obj in tokens:
            token_info = {
                'token_id': token_obj.id,
                'token_value': token_obj.token,
                'form': token_obj.form.title,
                'architecture': token_obj.architecture.name
            }
            result['found_tokens'].append(token_info)
            
            # Check submissions for this token
            submissions = FormSubmission.objects.filter(token=token_obj)
            for submission in submissions:
                submission_info = {
                    'submission_id': submission.id,
                    'student_id': submission.student.id if submission.student else None,
                    'student_email': submission.student.email if submission.student else None,
                    'student_name': submission.student.full_name if submission.student else None,
                    'created': submission.created_at
                }
                result['submissions'].append(submission_info)
        
        return Response(result)
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_token_ownership(request, token):
    """
    Emergency endpoint to reset token ownership to current user
    """
    try:
        logger.info(f"=== RESET TOKEN OWNERSHIP: User {request.user.id} resetting token {token} ===")
        
        normalized_token = normalize_token(token)
        token_obj = get_token_object(normalized_token)
        
        if not token_obj:
            return Response({"error": "Token not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Delete all existing submissions for this token
        deleted_count, _ = FormSubmission.objects.filter(token=token_obj).delete()
        logger.info(f"Deleted {deleted_count} existing submissions for token {token}")
        
        # Create new submission for current user
        submission = FormSubmission.objects.create(
            token=token_obj,
            form=token_obj.form,
            student=request.user
        )
        
        logger.info(f"Created new submission {submission.id} for user {request.user.id}")
        
        return Response({
            "message": f"Token {normalized_token} ownership reset successfully",
            "deleted_submissions": deleted_count,
            "new_owner": {
                "id": request.user.id,
                "email": request.user.email,
                "name": request.user.full_name
            },
            "new_submission_id": submission.id
        })
        
    except Exception as e:
        logger.error(f"Error resetting token {token}: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def repair_token_ownership(request, token):
    """
    Repair token ownership - transfer ownership to current user
    """
    try:
        logger.info(f"=== REPAIR TOKEN OWNERSHIP: User {request.user.id} repairing token {token} ===")
        
        normalized_token = normalize_token(token)
        token_obj = get_token_object(normalized_token)
        
        if not token_obj:
            return Response({"error": "Token not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all submissions for this token
        all_submissions = FormSubmission.objects.filter(token=token_obj)
        logger.info(f"Found {all_submissions.count()} submissions for token {token}")
        
        if all_submissions.count() > 1:
            logger.warning(f"Multiple submissions found for token {token}, will delete duplicates")
        
        # Keep only the first submission and update its owner
        if all_submissions.exists():
            # Update the first submission
            submission = all_submissions.first()
            old_owner = submission.student
            submission.student = request.user
            submission.save()
            
            # Delete duplicate submissions
            if all_submissions.count() > 1:
                duplicates = all_submissions.exclude(id=submission.id)
                duplicate_count = duplicates.count()
                duplicates.delete()
                logger.info(f"Deleted {duplicate_count} duplicate submissions")
            
            logger.info(f"Updated submission {submission.id} from user {old_owner.id if old_owner else 'None'} to user {request.user.id}")
        else:
            # Create new submission
            submission = FormSubmission.objects.create(
                token=token_obj,
                form=token_obj.form,
                student=request.user
            )
            logger.info(f"Created new submission {submission.id} for user {request.user.id}")
        
        return Response({
            "message": f"Token {normalized_token} ownership repaired successfully",
            "action": "updated" if all_submissions.exists() else "created",
            "previous_owner": {
                "id": old_owner.id if all_submissions.exists() and old_owner else None,
                "email": old_owner.email if all_submissions.exists() and old_owner else None
            } if all_submissions.exists() else None,
            "new_owner": {
                "id": request.user.id,
                "email": request.user.email,
                "name": request.user.full_name
            },
            "submission_id": submission.id,
            "duplicates_deleted": all_submissions.count() - 1 if all_submissions.count() > 1 else 0
        })
        
    except Exception as e:
        logger.error(f"Error repairing token {token}: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)