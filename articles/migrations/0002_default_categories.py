from django.db import migrations
from django.utils.text import slugify


def add_default_categories(apps, schema_editor):
    Category = apps.get_model("articles", "Category")
    for name in ("Texnologiya", "Proqramlaşdırma", "Elm", "Təhsil", "Karyera", "Biznes"):
        Category.objects.get_or_create(
            name=name,
            defaults={"slug": slugify(name, allow_unicode=True)},
        )


class Migration(migrations.Migration):
    dependencies = [("articles", "0001_initial")]
    operations = [migrations.RunPython(add_default_categories, migrations.RunPython.noop)]
