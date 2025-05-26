"""
Django settings for projeto_selecao_aleatoria project.

ÍNDICE DE CONFIGURAÇÕES:
1. CONFIGURAÇÕES BASE E PATH
2. SEGURANÇA E DEBUG
3. AWS E ARMAZENAMENTO 
4. SWAGGER E JWT
5. APPS INSTALADOS
6. MIDDLEWARE E CORS
7. TEMPLATES E URLS
8. BANCO DE DADOS
9. AUTENTICAÇÃO E SENHAS
10. INTERNACIONALIZAÇÃO
11. ARQUIVOS ESTÁTICOS
12. REST FRAMEWORK
13. LOGGING

Para documentação completa do Django, veja:
https://docs.djangoproject.com/en/5.2/topics/settings/
"""

#==============================================================================
# 1. CONFIGURAÇÕES BASE E PATH
#==============================================================================
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent 

# Carrega variáveis de ambiente do arquivo .env
load_dotenv(BASE_DIR / '.env')

# Valor padrão para campos de chave primária automática 
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#==============================================================================
# 2. SEGURANÇA E DEBUG
#==============================================================================
# ATENÇÃO: Valores que devem ser substituídos em produção
SECRET_KEY = 'django-insecure-nmfd6vg_x@z4n9ckfu@a1@%ih-cuf=dg0=8&d@yocx3%hb=d^y'
DEBUG = True
ALLOWED_HOSTS = []

#==============================================================================
# 3. AWS E ARMAZENAMENTO
#==============================================================================
# Configurações de credenciais AWS
AWS_ACCESS_KEY_ID        = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY    = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME  = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME       = os.getenv("AWS_S3_REGION_NAME", "us-east-2")
AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

# Configuração do armazenamento
if not AWS_STORAGE_BUCKET_NAME:
    # Fallback para storage local quando não houver bucket configurado
    import logging
    logging.warning("⚠️ AWS_STORAGE_BUCKET_NAME não definido: usando FileSystemStorage")
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
else:
    # Configura S3 como backend
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

#==============================================================================
# 4. SWAGGER E JWT
#==============================================================================
# Configurações do Swagger UI
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Format: Bearer <JWT token>'
        },
    },
    'USE_SESSION_AUTH': True,
    'LOGIN_URL': '/admin/login/',
    'LOGOUT_URL': '/admin/logout/',
    'PERSIST_AUTH': True,
    'REFETCH_SCHEMA_WITH_AUTH': True,
    'REFETCH_SCHEMA_ON_LOGOUT': True,
}

# Configurações do JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

#==============================================================================
# 5. APPS INSTALADOS
#==============================================================================
INSTALLED_APPS = [
    # Apps padrão do Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    
    # Apps de terceiros
    'rest_framework',     # Framework de API REST
    'drf_yasg',           # Documentação Swagger
    'storages',           # Gerenciamento de armazenamento S3
    
    # Apps do projeto
    "core.apps.CoreConfig",

     
]

#==============================================================================
# 6. MIDDLEWARE E CORS
#==============================================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware' 
]

# Configuração CORS - em produção, especifique apenas origens permitidas
#CORS_ALLOW_ALL_ORIGINS = True  

CORS_ALLOWED_ORIGINS = [
     "http://localhost:4200",
     
]

CORS_ALLOW_CREDENTIALS = True


#==============================================================================
# 7. TEMPLATES E URLS
#==============================================================================
ROOT_URLCONF = 'config.urls' 
WSGI_APPLICATION = 'config.wsgi.application' 

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

#==============================================================================
# 8. BANCO DE DADOS
#==============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

#==============================================================================
# 9. AUTENTICAÇÃO E SENHAS
#==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

#==============================================================================
# 10. INTERNACIONALIZAÇÃO
#==============================================================================
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

#==============================================================================
# 11. ARQUIVOS ESTÁTICOS
#==============================================================================
STATIC_URL = 'static/'
# Para usar S3 para arquivos estáticos, descomente a linha abaixo
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'

#==============================================================================
# 12. REST FRAMEWORK
#==============================================================================
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Autenticação JWT
        'rest_framework.authentication.SessionAuthentication',        # Autenticação por sessão
        'rest_framework.authentication.BasicAuthentication',          # Autenticação básica
    ],
}

#==============================================================================
# 13. LOGGING
#==============================================================================
# Garantir que o diretório de logs existe
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'docker': {
            'format': '[DOCKER] {levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/projeto.log'),
            'formatter': 'verbose',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        },
        'docker_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/docker_rpa.log'),
            'formatter': 'docker',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'docker_rpa': {
            'handlers': ['console', 'docker_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}