# apps.py
# Este arquivo define a configuração da aplicação Django 'core'.
# A classe AppConfig permite personalizar o comportamento da aplicação.

from django.apps import AppConfig


class CoreConfig(AppConfig):
    # Configura o tipo de campo automático para IDs das tabelas
    # BigAutoField é um campo inteiro de 64 bits, permitindo valores maiores que AutoField
    default_auto_field = 'django.db.models.BigAutoField'
    
    # Nome interno da aplicação, usado em várias partes do Django
    name = 'core'
    
    # Nome legível da aplicação, exibido no painel de administração
    verbose_name = 'Seleção Aleatória'

    def ready(self):
        import core.services.s3.signals
  