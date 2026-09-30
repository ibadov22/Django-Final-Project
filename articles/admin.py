from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Article, ArticleReaction, Category, Comment, Favorite, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Sayt profili və icazələri", {"fields": ("role", "bio")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Sayt icazələri", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "views", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("title", "body", "author__username")
    readonly_fields = ("views", "created_at", "updated_at")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("article", "author", "created_at")
    search_fields = ("body", "author__username", "article__title")


@admin.register(ArticleReaction)
class ArticleReactionAdmin(admin.ModelAdmin):
    list_display = ("article", "user", "value")
    list_filter = ("value",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("article", "user", "created_at")
