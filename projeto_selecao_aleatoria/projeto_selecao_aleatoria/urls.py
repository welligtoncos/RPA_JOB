from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import DockerHistoricoViewSet, HistoricoRPAViewSet, RPADockerViewSet, RPAViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

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
router.register(r'historico-rpa', HistoricoRPAViewSet, basename='historico-rpa')
router.register(r'docker-historico', DockerHistoricoViewSet, basename='docker-historico')
router.register(r'docker-rpa', RPADockerViewSet, basename='docker-rpa')
router.register(r'docker-historico', DockerHistoricoViewSet, basename='docker-historico')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),  # Aqui já inclui as rotas registradas no router

    # ✅ JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ✅ Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]   
