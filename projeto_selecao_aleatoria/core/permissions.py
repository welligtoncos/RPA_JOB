# core/permissions.py
# Este arquivo define permissões personalizadas para controle de acesso aos recursos da API.
# Define quem pode acessar quais objetos com base em relações de propriedade.

from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permissão personalizada para permitir apenas donos ou admins acessarem objetos.
    
    Esta permissão:
    - Permite acesso total a administradores do sistema
    - Permite acesso ao proprietário do objeto
    - Nega acesso a todos os outros usuários
    
    Compatível com:
    - Objetos que têm um campo 'user' relacionado ao usuário
    - Objetos que têm um campo 'user_id' com o ID do usuário
    
    Usado em APIs como ResultadoDownloadViewSet para proteger recursos do usuário.
    """
    
    def has_object_permission(self, request, view, obj):
        # Administradores (is_staff=True) sempre têm acesso
        if request.user.is_staff:
            return True
            
        # Verifica se o objeto tem um relacionamento direto com o usuário (ForeignKey)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Verifica se o objeto armazena apenas o ID do usuário
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
            
        # Se nenhuma associação de usuário for encontrada, nega acesso
        return False