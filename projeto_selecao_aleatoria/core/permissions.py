# core/permissions.py
from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permissão personalizada para permitir apenas donos ou admins acessarem seus resultados.
    """
    
    def has_object_permission(self, request, view, obj):
        # Verificar se o usuário é staff/admin
        if request.user.is_staff:
            return True
            
        # Verificar se o objeto tem o atributo user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Verificar se o objeto tem o atributo user_id
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
            
        return False