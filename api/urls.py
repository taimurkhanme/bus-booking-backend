from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views.auth_views import RegisterView, LoginView, LogoutView, ProfileView, ChangePasswordView
from .views.bus_views import BusListView, BusDetailView, BusSearchView, RouteListView, RouteDetailView, RouteSeatsView, CityListView
from .views.booking_views import BookingCreateView, BookingListView, BookingDetailView, BookingCancelView
from .views.payment_views import PaymentCreateOrderView, PaymentVerifyView, PaymentWebhookView

from django.http import JsonResponse
from api.models import User

def create_temp_admin(request):
    try:
        email = "admin@busbook.pk"
        if User.objects.filter(email=email).exists():
            return JsonResponse({"status": "error", "message": "Admin user already exists!"}, status=400)
        
        user = User.objects.create_superuser(
            email=email,
            username="admin",
            phone="03001234567",
            password="AdminPassword123"
        )
        return JsonResponse({"status": "success", "message": f"Admin user created successfully! Email: {email}, Password: AdminPassword123"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

urlpatterns = [
    # Temporary Admin Creator
    path('create-admin/', create_temp_admin, name='create_temp_admin'),

    # Authentication Endpoints
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', LoginView.as_view(), name='auth_login'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/profile/', ProfileView.as_view(), name='auth_profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth_change_password'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Buses Endpoints
    path('buses/', BusListView.as_view(), name='buses_list'),
    path('buses/<int:pk>/', BusDetailView.as_view(), name='bus_detail'),
    path('buses/search/', BusSearchView.as_view(), name='bus_search'),
    path('buses/cities/', CityListView.as_view(), name='buses_cities'),

    # Routes Endpoints
    path('routes/', RouteListView.as_view(), name='routes_list'),
    path('routes/<int:pk>/', RouteDetailView.as_view(), name='route_detail'),
    path('routes/<int:pk>/seats/', RouteSeatsView.as_view(), name='route_seats'),

    # Bookings Endpoints
    path('bookings/', BookingListView.as_view(), name='bookings_list'),
    path('bookings/create/', BookingCreateView.as_view(), name='bookings_create'),
    path('bookings/<str:booking_id>/', BookingDetailView.as_view(), name='booking_detail'),
    path('bookings/<str:booking_id>/cancel/', BookingCancelView.as_view(), name='booking_cancel'),

    # Payments Endpoints
    path('payment/create-order/', PaymentCreateOrderView.as_view(), name='payment_create_order'),
    path('payment/verify/', PaymentVerifyView.as_view(), name='payment_verify'),
    path('payment/webhook/', PaymentWebhookView.as_view(), name='payment_webhook'),
]
