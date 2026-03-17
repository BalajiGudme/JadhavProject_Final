

#90000000000000000000000------===================================3/10/2025

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import delete_architecture
from .views import useridprofile
from .views import (
    # OptimizedLandingPageView,
   PasswordResetRequestView,
    ResendOTPView,
    VerifyOTPView,
    PasswordResetConfirmView,
    CustomSentRecordForIDViewSet,
    UserProfileView,
    ArchitectureDetailView,

    CustomerDashboardAPIView, ArchitectureStatusAPIView,RegistrationInitView,RegistrationVerifyView, RegistrationResendOTPView,
)
# Create router
router = DefaultRouter()
router.register(r'forms', views.FormViewSet, basename='form')
router.register(r'form-fields', views.FormFieldViewSet, basename='formfield')
router.register(r'public-forms', views.PublicFormViewSet, basename='publicform')
router.register(r'submissions', views.FormSubmissionViewSet, basename='submission')
router.register(r'architecture', views.ArchitectureViewSet, basename='architecture')
router.register(r'form-tokens', views.FormTokenViewSet, basename='formtoken')
router.register(r'custom-sent-record-for-id-viewSet', CustomSentRecordForIDViewSet,basename=' CustomSentRecordForID')
router.register(r'statusArchitecture', views.statusArchitecture, basename='statusarchitecture')


router.register(r'statistics', views.StatisticViewSet, basename='statistic')
router.register(r'portfolio', views.PortfolioItemViewSet, basename='portfolio')
router.register(r'services', views.ServiceViewSet, basename='service')
router.register(r'testimonials', views.TestimonialViewSet, basename='testimonial')
router.register(r'clients', views.ClientViewSet, basename='client')
router.register(r'slide1', views.Slide1ViewSet, basename='slide1')
router.register(r'slide2', views.Slide2ViewSet, basename='slide2')

# Manual URLs for custom actions
urlpatterns = [
    # Form endpoints
    path('forms/<int:pk>/publish/', views.FormViewSet.as_view({'post': 'publish'}), name='form-publish'),
    path('forms/<int:pk>/unpublish/', views.FormViewSet.as_view({'post': 'unpublish'}), name='form-unpublish'),
    path('forms/by-architecture/', views.FormViewSet.as_view({'get': 'by_architecture'}), name='forms-by-architecture'),
    
    # Public form endpoints
    path('public-forms/<int:pk>/submit/', views.PublicFormViewSet.as_view({'post': 'submit'}), name='public-form-submit'),
    
    # Architecture endpoints
    path('architecture-tree/', views.ArchitectureTreeView.as_view(), name='architecture-tree'),
    path('architecture/<int:pk>/tree/', views.ArchitectureViewSet.as_view({'get': 'tree'}), name='architecture-tree-detail'),
    path('architecture/<int:pk>/children/', views.ArchitectureViewSet.as_view({'get': 'children'}), name='architecture-children'),
    path('architecture/<int:pk>/hierarchy/', views.ArchitectureViewSet.as_view({'get': 'hierarchy'}), name='architecture-hierarchy'),
    path('architecture/<int:pk>/statistics/', views.ArchitectureViewSet.as_view({'get': 'statistics'}), name='architecture-statistics'),
    path('architecture/<int:pk>/forms/', views.ArchitectureViewSet.as_view({'get': 'forms'}), name='architecture-forms'),
    path('architecture/<int:pk>/tokens/', views.ArchitectureViewSet.as_view({'get': 'tokens'}), name='architecture-tokens'),
    
    # Form submission endpoints
    path('submit-form/<int:pk>/', views.FormSubmitView.as_view(), name='submit-form'),
    path('submissions/by-token/', views.FormSubmissionViewSet.as_view({'get': 'by_token'}), name='submissions-by-token'),
    
    # Form token endpoints
    path('form-tokens/generate-multiple/', views.FormTokenViewSet.as_view({'post': 'generate_multiple'}), name='formtoken-generate-multiple'),
    path('form-tokens/validate-token/', views.FormTokenViewSet.as_view({'post': 'validate_token'}), name='formtoken-validate'),
    path('form-tokens/by-architecture/', views.FormTokenViewSet.as_view({'get': 'by_architecture'}), name='formtokens-by-architecture'),
    
    # QR Code endpoint
    path('generate-qr-codes/', views.QRCodeView.as_view(), name='generate-qr-codes'),
   path('submit-form/', views.SubmitFormByTokenView.as_view(), name='submit-form'),
    path('form-tokens/check-existing/', views.check_existing_tokens, name='check-existing-tokens'),
    # Include all router URLs
    path('architecture/<int:architecture_id>/responses/', 
         views.ArchitectureResponsesView.as_view(), 
         name='architecture-responses'),

    # path('architecture/<int:architecture_id>/tokens-responses/', 
    #      views.ArchitectureTokensResponsesView.as_view(), 
    #      name='architecture-tokens-responses'),

    #------------------------
    path('token/<int:token>/edit/', views.edit_token_responses, name='edit-token-responses'),
    path('token/<int:token>/delete/', views.delete_token_responses, name='delete-token-responses'),
  
    # Authentication endpoints
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/admin-login/', views.AdminTokenObtainPairView.as_view(), name='admin_token_obtain_pair'),
    path('auth/users/', views.UserListView.as_view(), name='user-list'),
    path('auth/pending-users/', views.pending_users, name='pending-users'),
    path('auth/approve-user/<int:user_id>/', views.approve_user, name='approve-user'),
    path('auth/reject-user/<int:user_id>/', views.reject_user, name='reject-user'),
    
     # Password Reset with OTP (Class-based views)/8/10/205
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('auth/password-reset/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
     path('customsentoadmin/<int:architecture_id>/', 
         views.custom_sent_to_admin, 
         name='custom_sent_to_admin'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
      path('profile/<int:architecture_id>/', views.UserProfileView.as_view(), name='architecture-creator-profile'),
    # path(
    #     'api/admin/custom-sent-records/<int:architecture_id>/',
    #     views.CustomSentRecordForIDViewSet.as_view(),
    #     name='custom-sent-record-for-id'
    # ),
    path('architecture/<int:id>/', ArchitectureDetailView.as_view(), name='architecture-detail'),
    path('', include(router.urls)),


    path('dashboard/customer/', CustomerDashboardAPIView.as_view(), name='customer-dashboard'),
    path('architecture/status-summary/', ArchitectureStatusAPIView.as_view(), name='architecture-status-summary'),

path('auth/register/init/', RegistrationInitView.as_view(), name='register-init'),
    path('auth/register/verify/', RegistrationVerifyView.as_view(), name='register-verify'),
    path('auth/register/resend-otp/', RegistrationResendOTPView.as_view(), name='register-resend'),

# Custom delete endpoint for architecture

    path('architecture/<int:architecture_id>/delete/', delete_architecture, name='delete-architecture'),
 path('user-profile/<int:user_id>/', useridprofile.as_view(), name='user-profile-by-id'),



# path('landing-page/', OptimizedLandingPageView.as_view(), name='landing-page'),
]