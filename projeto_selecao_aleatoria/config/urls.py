from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import (
    DockerHistoricoViewSet, 
    HistoricoRPAViewSet, 
    RPADockerViewSet, 
    RPAViewSet,
    UserProcessamentoViewSet, 
    UserDockerProcessamentoViewSet,
    ResultadoDownloadViewSet
)
 
from core.views.user_group import UserGroupAPIView, get_user_group, get_user_group_by_id

from core.views.views_processamento_rpa import ProcessamentoRPAViewSet

from core.views.UploadParaInputSAView import UploadParaInputSAView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

# 🔥 Importa o drf_yasg
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Projeto Seleção Aleatória API",
        default_version='v1',
        description="Documentação da API de Processamento RPA",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Define seu router normalmente
router = DefaultRouter()
router.register(r'rpa', RPAViewSet, basename='rpa')
router.register(r'historico-rpa', HistoricoRPAViewSet, basename='histforico-rpa')
router.register(r'docker-historico', DockerHistoricoViewSet, basename='docker-historico')
router.register(r'docker-rpa', RPADockerViewSet, basename='docker-rpa')
router.register(r'resultados', ResultadoDownloadViewSet, basename='resultados')
router.register(r'processamentos', ProcessamentoRPAViewSet, basename='processamentos')

# Router para as APIs de processamento por usuário
router.register(
    r'usuarios/(?P<user_id>\d+)/processamentos',
    UserProcessamentoViewSet,
    basename='user-processamento'
)
router.register(
    r'usuarios/(?P<user_id>\d+)/docker-processamentos',
    UserDockerProcessamentoViewSet,
    basename='user-docker-processamento'
)  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),  # Todas as rotas em um único router

    # ✅ JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
     # 🔥 Novos endpoints para grupos de usuário
    # Opção 1: APIView
    path('api/user/group/', UserGroupAPIView.as_view(), name='user-group'),
    
    # Opção 2: Function-based view
    path('api/user/me/group/', get_user_group, name='user-me-group'),
    
    # Opção 3: Buscar grupo por ID (apenas admins)
    path('api/user/<int:user_id>/group/', get_user_group_by_id, name='user-group-by-id'),

    # ✅ Autenticação para Swagger - Adicionar estas linhas
    path('accounts/login/', RedirectView.as_view(url='/admin/login/?next=/swagger/', permanent=False), name='account_login'),
    path('login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    
      # ✅ Upload para input_sa sob /api/
    path('api/s3/upload-input-sa/', UploadParaInputSAView.as_view(), name='upload-input-sa'),


    # ✅ Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]