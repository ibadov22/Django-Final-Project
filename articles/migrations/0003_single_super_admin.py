from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0002_default_categories"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AlterModelOptions(name="user", options={}),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                condition=models.Q(role="super_admin"),
                fields=("role",),
                name="articles_single_super_admin",
            ),
        ),
    ]
