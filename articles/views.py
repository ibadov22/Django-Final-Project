from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import ArticleForm, CommentForm, ProfileForm, SignUpForm
from .models import Article, Category, Comment, User


def visible_articles(user):
    articles = Article.objects.select_related("author", "category")
    if user.is_authenticated:
        if user.is_editor:
            return articles
        # Keep the author's drafts in their feed while hiding them from everyone else.
        return articles.filter(
            Q(status=Article.Status.PUBLISHED) | Q(author_id=user.pk)
        )
    return articles.filter(status=Article.Status.PUBLISHED)


def home(request):
    articles = visible_articles(request.user)
    query = request.GET.get("q", "").strip()
    order = request.GET.get("s", "new")
    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query) | Q(tags__icontains=query) | Q(author__username__icontains=query))
    if order == "popular":
        articles = articles.order_by("-views", "-created_at")
    paginator = Paginator(articles, 8)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "articles/home_feed.html", {"page_obj": page_obj, "query": query, "order": order})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    articles = visible_articles(request.user).filter(category=category)
    page_obj = Paginator(articles, 8).get_page(request.GET.get("page"))
    return render(request, "articles/home_feed.html", {"page_obj": page_obj, "category": category, "query": "", "order": "new"})


def article_detail(request, slug):
    article = get_object_or_404(Article.objects.select_related("author", "category"), slug=slug)
    if article.status != Article.Status.PUBLISHED and not (
        request.user.is_authenticated and (request.user.is_editor or request.user == article.author)
    ):
        raise Http404
    Article.objects.filter(pk=article.pk).update(views=F("views") + 1)
    article.refresh_from_db(fields=["views"])
    form = CommentForm()
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"login?next={article.get_absolute_url()}#comments")
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            comment.author = request.user
            comment.save()
            messages.success(request, "Şərhiniz əlavə olundu.")
            return redirect(f"{article.get_absolute_url()}#comments")
    return render(request, "articles/detail.html", {"article": article, "form": form, "comments": article.comments.select_related("author")})


@login_required
def article_create(request):
    form = ArticleForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()
            if article.status == Article.Status.DRAFT:
                messages.success(request, "Məqalə qaralama kimi yadda saxlanıldı.")
            else:
                messages.success(request, "Məqalə uğurla dərc edildi.")
            # Return to the feed so the author can immediately see the new item there.
            return redirect("home")
        errors = []
        for field_name, field_errors in form.errors.items():
            label = form.fields[field_name].label if field_name in form.fields else "Forma"
            errors.extend(f"{label}: {error}" for error in field_errors)
        messages.error(request, "Məqalə yadda saxlanmadı. " + " ".join(errors))
    return render(request, "articles/form.html", {"form": form, "heading": "Yeni məqalə", "button": "Məqaləni yadda saxla"})


@login_required
def article_edit(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not (request.user.is_editor or request.user == article.author):
        raise Http404
    form = ArticleForm(request.POST or None, instance=article)
    if request.method == "POST" and form.is_valid():
        form.save()
        if article.status == Article.Status.DRAFT:
            messages.success(request, "Dəyişikliklər yadda saxlanıldı. Məqalə qaralama olaraq qaldı.")
        else:
            messages.success(request, "Məqalə dərc edildi və dəyişikliklər yadda saxlanıldı.")
        return redirect(article.get_absolute_url())
    return render(request, "articles/form.html", {"form": form, "heading": "Məqaləni redaktə et", "button": "Dəyişiklikləri yadda saxla", "article": article})


@login_required
@require_POST
def article_delete(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not (request.user.is_editor or request.user == article.author):
        raise Http404
    article.delete()
    messages.success(request, "Məqalə silindi.")
    return redirect("home")


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Xoş gəlmisiniz! Hesabınız yaradıldı.")
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil yeniləndi.")
        return redirect("profile")
    own_articles = request.user.articles.select_related("category")
    return render(request, "articles/profile.html", {"form": form, "own_articles": own_articles})


def is_admin(user):
    return user.is_authenticated and user.is_editor


@user_passes_test(is_admin)
def article_management(request):
    articles = Article.objects.select_related("author", "category").order_by("-created_at", "-pk")
    query = request.GET.get("q", "").strip()
    if query:
        articles = articles.filter(
            Q(title__icontains=query)
            | Q(body__icontains=query)
            | Q(author__username__icontains=query)
        )
    page_obj = Paginator(articles, 15).get_page(request.GET.get("page"))
    return render(
        request,
        "articles/management.html",
        {"page_obj": page_obj, "query": query},
    )


@user_passes_test(is_admin)
def user_management(request):
    users = User.objects.order_by("-date_joined")
    if not request.user.is_superuser:
        users = users.exclude(is_superuser=True).exclude(role=User.Role.ADMIN)
    return render(request, "articles/users.html", {"users": users})


@login_required
@require_POST
def toggle_user_block(request, user_id):
    if not request.user.is_editor:
        raise Http404
    target = get_object_or_404(User, pk=user_id)
    if target == request.user or target.is_superuser or (not request.user.is_superuser and target.role != User.Role.USER):
        messages.error(request, "Bu hesab üçün əməliyyat mümkün deyil.")
        return redirect("user_management")
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    messages.success(request, f"{target.username} istifadəçisinin hesabı {'aktiv edildi' if target.is_active else 'bloklandı'}.")
    return redirect("user_management")


@login_required
@require_POST
def toggle_admin_role(request, user_id):
    if not request.user.is_superuser:
        raise Http404
    target = get_object_or_404(User, pk=user_id)
    if target.is_superuser:
        messages.error(request, "Super Admin rolunu bu bölmədən dəyişmək mümkün deyil.")
    else:
        target.role = User.Role.USER if target.role == User.Role.ADMIN else User.Role.ADMIN
        target.save(update_fields=["role"])
        messages.success(request, f"{target.username} üçün rol yeniləndi.")
    return redirect("user_management")
