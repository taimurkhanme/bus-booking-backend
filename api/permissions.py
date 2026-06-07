from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of a booking or admins to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user and request.user.is_staff:
            return True
            
        # Check if the booking user matches request user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'booking') and hasattr(obj.booking, 'user'):
            return obj.booking.user == request.user
            
        return False
