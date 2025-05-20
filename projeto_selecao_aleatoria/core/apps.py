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
        # Este método é chamado quando a aplicação é inicializada
        # Importamos o módulo services.s3 para garantir que os receivers de signals sejam registrados
        # Os receivers são funções que respondem a eventos do Django (como salvar modelos)
        import core.s3_manager
        #import core.services.s3

        # Importamos outros módulos que podem conter receivers
        # (descomente conforme necessário)
        # import core.signals