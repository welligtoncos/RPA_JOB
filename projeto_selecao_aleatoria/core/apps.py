from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Seleção Aleatória'

    def ready(self):
        # importa só para garantir que os receivers sejam registrados
        import core.signals