from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


CATEGORY_NAMES = (
    "Proqramlaşdırma",
    "Sistem inzibatçılığı",
    "Dizayn",
    "Menecment",
    "Marketinq",
    "Elmi-populyar",
)


def update_categories(apps, schema_editor):
    Category = apps.get_model("articles", "Category")
    Article = apps.get_model("articles", "Article")
    mapping = {
        "Texnologiya": "Sistem inzibatçılığı",
        "Elm": "Elmi-populyar",
        "Təhsil": "Elmi-populyar",
        "Karyera": "Menecment",
        "Biznes": "Marketinq",
    }
    for old_name, new_name in mapping.items():
        old_category = Category.objects.filter(name=old_name).first()
        if old_category is None:
            continue
        new_category, _ = Category.objects.get_or_create(
            name=new_name,
            defaults={"slug": slugify(new_name, allow_unicode=True)},
        )
        Article.objects.filter(category_id=old_category.pk).update(category_id=new_category.pk)
        old_category.delete()
    for name in CATEGORY_NAMES:
        Category.objects.get_or_create(name=name, defaults={"slug": slugify(name, allow_unicode=True)})
    default_category = Category.objects.get(name="Proqramlaşdırma")
    Article.objects.filter(category__isnull=True).update(category_id=default_category.pk)


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0003_single_super_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="bio",
            field=models.TextField(blank=True, max_length=1000, verbose_name="Haqqımda"),
        ),
        migrations.AlterField(
            model_name="article",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Qaralama"),
                    ("pending", "Təsdiq gözləyir"),
                    ("published", "Dərc edilib"),
                ],
                db_index=True,
                default="draft",
                max_length=12,
                verbose_name="Status",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="image",
            field=models.FileField(blank=True, upload_to="article_images/%Y/%m/", verbose_name="Məqalə şəkli"),
        ),
        migrations.CreateModel(
            name="ArticleReaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.CharField(choices=[("like", "Bəyən"), ("dislike", "Bəyənmə")], max_length=10)),
                ("article", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reactions", to="articles.article")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="article_reactions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="articlereaction",
            constraint=models.UniqueConstraint(fields=("article", "user"), name="articles_unique_user_reaction"),
        ),
        migrations.CreateModel(
            name="Favorite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("article", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorites", to="articles.article")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorites", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="favorite",
            constraint=models.UniqueConstraint(fields=("article", "user"), name="articles_unique_user_favorite"),
        ),
        migrations.RunPython(update_categories, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="article",
            name="category",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="articles", to="articles.category", verbose_name="Kateqoriya"),
        ),
    ]
