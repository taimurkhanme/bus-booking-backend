from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from ..serializers import UserSerializer, UserRegistrationSerializer

User = get_user_model()

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            user_data = UserSerializer(user).data
            
            return Response({
                'success': True,
                'data': {
                    'user': user_data,
                    **tokens
                },
                'message': 'Registration successful.'
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            'success': False,
            'error': 'Registration failed.',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'success': False,
                'error': 'Email and password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if not user.is_active:
                return Response({
                    'success': False,
                    'error': 'This account has been deactivated.'
                }, status=status.HTTP_403_FORBIDDEN)
                
            tokens = get_tokens_for_user(user)
            user_data = UserSerializer(user).data
            
            return Response({
                'success': True,
                'data': {
                    'user': user_data,
                    **tokens
                },
                'message': 'Login successful.'
            }, status=status.HTTP_200_OK)
            
        return Response({
            'success': False,
            'error': 'Invalid email or password.'
        }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({
                    'success': False,
                    'error': 'Refresh token is required.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Logout successful.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request):
        # Support multipart form-data (profile_picture file upload)
        user = request.user
        data = request.data.copy()
        
        # If frontend sent first_name as 'name'
        if 'name' in data and not 'first_name' in data:
            data['first_name'] = data['name']
            
        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data,
                'message': 'Profile updated successfully.'
            }, status=status.HTTP_200_OK)
            
        return Response({
            'success': False,
            'error': 'Profile update failed.',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response({
                'success': False,
                'error': 'Both old and new passwords are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if not user.check_password(old_password):
            return Response({
                'success': False,
                'error': 'Incorrect current password.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        user.password = make_password(new_password)
        user.save()
        
        return Response({
            'success': True,
            'message': 'Password changed successfully.'
        }, status=status.HTTP_200_OK)
