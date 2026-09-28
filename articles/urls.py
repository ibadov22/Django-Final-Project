from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("qeydiyyat/", views.register, name="register"),
    path("giris/", auth_views.LoginView.as_view(template_name="registration/login.html", redirect_authenticated_user=True), name="login"),
    path("cixis/", auth_views.LogoutView.as_view(), name="logout"),
    path("meqaleler/yeni/", views.article_create, name="article_create"),
    # Azerbaijani titles produce Unicode slugs; <slug:...> only accepts ASCII.
    path("meqaleler/<str:slug>/", views.article_detail, name="article_detail"),
    path("meqaleler/<str:slug>/redakte/", views.article_edit, name="article_edit"),
    path("meqaleler/<str:slug>/sil/", views.article_delete, name="article_delete"),
    # Category slugs may contain Azerbaijani letters such as ı, ə and ş.
    path("kateqoriya/<str:slug>/", views.category_detail, name="category_detail"),
    path("profil/", views.profile, name="profile"),
    path("idarəetmə/məqalələr/", views.article_management, name="article_management"),
    path("idarəetmə/istifadəçilər/", views.user_management, name="user_management"),
    path("idarəetmə/istifadəçilər/<int:user_id>/blokla/", views.toggle_user_block, name="toggle_user_block"),
    path("idarəetmə/istifadəçilər/<int:user_id>/rol/", views.toggle_admin_role, name="toggle_admin_role"),
]
