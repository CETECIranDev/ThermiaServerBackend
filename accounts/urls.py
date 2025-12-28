from django.urls import path,include
from .views import *
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'clinic/users', views.ClinicUserViewSet, basename='clinic-users')

urlpatterns = [
    # authentication
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.UserLogoutView.as_view(), name='logout'),

    # user profile
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),

    # clinic management
    path('clinics/', views.ClinicCreateView.as_view(), name='clinic-create'),
    path('clinics/list/', views.ClinicListView.as_view(), name='clinic-list'),

    path('', include(router.urls)),

]