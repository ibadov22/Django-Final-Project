import re
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        USER = "user", "İstifadəçi"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER, verbose_name="Rol")
    bio = models.TextField(max_length=1000, blank=True, verbose_name="Haqqımda")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("role",),
                condition=models.Q(role="super_admin"),
                name="articles_single_super_admin",
            )
        ]

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPER_ADMIN
        elif self.role == self.Role.SUPER_ADMIN:
            raise ValidationError("Super Admin rolu yalnız superuser hesabına verilə bilər.")
        super().save(*args, **kwargs)

    @property
    def is_editor(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def __str__(self):
        return self.get_full_name() or self.username


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name="Ad")
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Kateqoriya"
        verbose_name_plural = "Kateqoriyalar"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qaralama"
        PENDING = "pending", "Təsdiq gözləyir"
        PUBLISHED = "published", "Dərc edilib"

    title = models.CharField(max_length=180, validators=[MinLengthValidator(5)], verbose_name="Başlıq")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    summary = models.CharField(max_length=280, blank=True, verbose_name="Qısa təsvir")
    body = models.TextField(validators=[MinLengthValidator(30)], verbose_name="Məqalə mətni")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="articles", verbose_name="Kateqoriya")
    image = models.FileField(upload_to="article_images/%Y/%m/", blank=True, verbose_name="Məqalə şəkli")
    tags = models.CharField(max_length=200, blank=True, help_text="Teqləri vergüllə ayırın", verbose_name="Teqlər")
    author = models.ForeignKey("articles.User", on_delete=models.CASCADE, related_name="articles", verbose_name="Müəllif")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True, verbose_name="Status")
    views = models.PositiveIntegerField(default=0, editable=False, verbose_name="Baxış sayı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaradılma tarixi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yenilənmə tarixi")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Məqalə"
        verbose_name_plural = "Məqalələr"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True)[:180] or "meqale"
            candidate, number = base, 2
            while Article.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{number}"
                number += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def tag_list(self):
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    @property
    def rating(self):
        return self.reactions.filter(value=ArticleReaction.Value.LIKE).count() - self.reactions.filter(value=ArticleReaction.Value.DISLIKE).count()

    @property
    def like_count(self):
        return self.reactions.filter(value=ArticleReaction.Value.LIKE).count()

    @property
    def dislike_count(self):
        return self.reactions.filter(value=ArticleReaction.Value.DISLIKE).count()

    @property
    def reading_minutes(self):
        return max(1, round(len(re.findall(r"\w+", self.body)) / 200))

    def get_absolute_url(self):
        return reverse("article_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("articles.User", on_delete=models.CASCADE, related_name="comments")
    body = models.TextField(max_length=1000, validators=[MinLengthValidator(2), MaxLengthValidator(1000)], verbose_name="Şərh")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Şərh"
        verbose_name_plural = "Şərhlər"

    def __str__(self):
        return f"{self.author}: {self.body[:40]}"


class ArticleReaction(models.Model):
    class Value(models.TextChoices):
        LIKE = "like", "Bəyən"
        DISLIKE = "dislike", "Bəyənmə"

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey("articles.User", on_delete=models.CASCADE, related_name="article_reactions")
    value = models.CharField(max_length=10, choices=Value.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("article", "user"), name="articles_unique_user_reaction")]


class Favorite(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="favorites")
    user = models.ForeignKey("articles.User", on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("article", "user"), name="articles_unique_user_favorite")]
