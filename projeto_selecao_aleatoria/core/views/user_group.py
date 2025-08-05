# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

User = get_user_model()

# Serializer para o grupo do usuário
class UserGroupSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    tipo_usuario = serializers.CharField(required=False)
    grupos = serializers.ListField(child=serializers.CharField())
    organizacao = serializers.CharField(required=False)
    is_admin = serializers.BooleanField()
    is_admin_tipo1 = serializers.BooleanField()
    is_usuario_tipo1 = serializers.BooleanField()

# Opção 1: APIView (Mais flexível)
class UserGroupAPIView(APIView):
    """
    Endpoint para buscar informações do grupo do usuário autenticado
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Busca todos os grupos do usuário
        grupos = list(user.groups.values_list('name', flat=True))
        
        # Determina o tipo de usuário
        tipo_usuario = getattr(user, 'tipo_usuario', None)
        organizacao = getattr(user, 'organizacao', None)
        
        # Verifica tipos específicos
        is_admin = (
            user.is_superuser or 
            tipo_usuario == 'admin' or 
            'Admin' in grupos
        )
        
        is_admin_tipo1 = (
            tipo_usuario == 'admin_tipo1' or 
            'Administrador-Tipo1' in grupos
        )
        
        is_usuario_tipo1 = (
            tipo_usuario == 'usuario_tipo1' or 
            'Usuario-Tipo1' in grupos
        )
        
        data = {
            'user_id': user.id,
            'username': user.username,
            'tipo_usuario': tipo_usuario,
            'grupos': grupos,
            'organizacao': organizacao,
            'is_admin': is_admin,
            'is_admin_tipo1': is_admin_tipo1,
            'is_usuario_tipo1': is_usuario_tipo1,
        }
        
        serializer = UserGroupSerializer(instance=data)
        return Response(serializer.data, status=status.HTTP_200_OK)

# Opção 2: Function-based view (Mais simples)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_group(request):
    """
    Retorna informações do grupo do usuário autenticado
    """
    user = request.user
    
    # Busca grupos
    grupos = list(user.groups.values_list('name', flat=True))
    
    # Informações básicas
    data = {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'grupos': grupos,
        'is_superuser': user.is_superuser,
    }
    
    # Se usando modelo customizado
    if hasattr(user, 'tipo_usuario'):
        data.update({
            'tipo_usuario': user.tipo_usuario,
            'organizacao': getattr(user, 'organizacao', None),
            'is_admin': user.tipo_usuario == 'admin',
            'is_admin_tipo1': user.tipo_usuario == 'admin_tipo1',
            'is_usuario_tipo1': user.tipo_usuario == 'usuario_tipo1',
        })
    
    return Response(data, status=status.HTTP_200_OK)

# Opção 3: Endpoint para buscar grupo de qualquer usuário (apenas para admins)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_group_by_id(request, user_id):
    """
    Busca informações do grupo de um usuário específico
    Apenas para administradores
    """
    # Verifica se é admin
    if not (request.user.is_superuser or 
            getattr(request.user, 'tipo_usuario', None) == 'admin'):
        return Response(
            {'error': 'Permissão negada. Apenas administradores podem acessar.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Usuário não encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    grupos = list(user.groups.values_list('name', flat=True))
    
    data = {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'grupos': grupos,
        'is_superuser': user.is_superuser,
        'is_active': user.is_active,
    }
    
    # Informações do modelo customizado
    if hasattr(user, 'tipo_usuario'):
        data.update({
            'tipo_usuario': user.tipo_usuario,
            'organizacao': getattr(user, 'organizacao', None),
        })
    
    return Response(data, status=status.HTTP_200_OK)

# Opção 4: ViewSet para operações completas de usuário
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

class UserGroupViewSet(ViewSet):
    """
    ViewSet para operações relacionadas a grupos de usuários
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        GET /api/user-groups/me/
        Retorna informações do usuário atual
        """
        user = request.user
        grupos = list(user.groups.values_list('name', flat=True))
        
        data = {
            'user_id': user.id,
            'username': user.username,
            'grupos': grupos,
            'tipo_usuario': getattr(user, 'tipo_usuario', None),
            'organizacao': getattr(user, 'organizacao', None),
        }
        
        return Response(data)
    
    @action(detail=True, methods=['get'])
    def groups(self, request, pk=None):
        """
        GET /api/user-groups/{user_id}/groups/
        Retorna grupos de um usuário específico (apenas admins)
        """
        # Verifica permissão
        if not self._is_admin(request.user):
            return Response(
                {'error': 'Permissão negada'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = User.objects.get(pk=pk)
            grupos = list(user.groups.values_list('name', flat=True))
            
            return Response({
                'user_id': user.id,
                'username': user.username,
                'grupos': grupos
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuário não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _is_admin(self, user):
        """Verifica se usuário é admin"""
        return (
            user.is_superuser or 
            getattr(user, 'tipo_usuario', None) == 'admin' or
            user.groups.filter(name='Admin').exists()
        )