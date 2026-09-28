from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "articles"
    verbose_name = "Məqalələr"

    def ready(self):
        from django.db.models.signals import post_save
        from django.dispatch import receiver
        from django.contrib.auth import get_user_model

        User = get_user_model()

        @receiver(post_save, sender=User)
        def keep_superuser_role(sender, instance, **kwargs):
            if instance.is_superuser and instance.role != User.Role.SUPER_ADMIN:
                sender.objects.filter(pk=instance.pk).update(role=User.Role.SUPER_ADMIN)
