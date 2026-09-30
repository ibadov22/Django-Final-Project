from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import ArticleForm, CommentForm, ProfileForm, SignUpForm
from .models import Article, ArticleReaction, Category, Comment, Favorite, User


def visible_articles(user):
    articles = Article.objects.select_related("author", "category")
    if user.is_authenticated:
        if user.is_editor:
            return articles
        return articles.filter(
            Q(status=Article.Status.PUBLISHED) | Q(author_id=user.pk)
        )
    return articles.filter(status=Article.Status.PUBLISHED)


def home(request):
    articles = visible_articles(request.user).annotate(
        like_total=Count("reactions", filter=Q(reactions__value=ArticleReaction.Value.LIKE)),
        dislike_total=Count("reactions", filter=Q(reactions__value=ArticleReaction.Value.DISLIKE)),
    )
    query = request.GET.get("q", "").strip()
    order = request.GET.get("s", "new")
    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query) | Q(tags__icontains=query) | Q(author__username__icontains=query))
    if order == "popular":
        articles = articles.order_by((F("like_total") - F("dislike_total")).desc(), "-views", "-created_at")
    else:
        articles = articles.order_by("-created_at")
    paginator = Paginator(articles, 8)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "articles/home_feed.html", {"page_obj": page_obj, "query": query, "order": order})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    articles = visible_articles(request.user).filter(category=category)
    page_obj = Paginator(articles, 8).get_page(request.GET.get("page"))
    return render(request, "articles/home_feed.html", {"page_obj": page_obj, "category": category, "query": "", "order": "new"})


def authors(request):
    authors_list = User.objects.filter(articles__status=Article.Status.PUBLISHED, is_active=True).annotate(published_count=Count("articles", filter=Q(articles__status=Article.Status.PUBLISHED))).distinct().order_by("username")
    return render(request, "articles/authors.html", {"authors": authors_list})


def author_detail(request, username):
    author = get_object_or_404(User, username=username, is_active=True)
    articles = Article.objects.filter(author=author, status=Article.Status.PUBLISHED).select_related("category")
    if request.user.is_authenticated and (request.user.is_editor or request.user == author):
        articles = Article.objects.filter(author=author).select_related("category")
    page_obj = Paginator(articles, 8).get_page(request.GET.get("page"))
    return render(request, "articles/author_detail.html", {"author_profile": author, "page_obj": page_obj})


@login_required
def favorites(request):
    articles = Article.objects.filter(favorites__user=request.user, status=Article.Status.PUBLISHED).select_related("author", "category")
    return render(request, "articles/home_feed.html", {"page_obj": Paginator(articles, 8).get_page(request.GET.get("page")), "query": "", "order": "new", "feed_title": "Seçilmiş məqalələr"})


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
    current_reaction = None
    is_favorite = False
    if request.user.is_authenticated:
        current_reaction = ArticleReaction.objects.filter(article=article, user=request.user).values_list("value", flat=True).first()
        is_favorite = Favorite.objects.filter(article=article, user=request.user).exists()
    return render(request, "articles/detail.html", {
        "article": article,
        "form": form,
        "comments": article.comments.select_related("author"),
        "current_reaction": current_reaction,
        "is_favorite": is_favorite,
    })


@login_required
def article_create(request):
    form = ArticleForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            if not request.user.is_editor and article.status != Article.Status.DRAFT:
                article.status = Article.Status.PENDING
            article.save()
            messages.success(request, "Məqalə qaralama kimi yadda saxlanıldı." if article.status == Article.Status.DRAFT else "Məqalə admin təsdiqinə göndərildi." if article.status == Article.Status.PENDING else "Məqalə dərc edildi.")
            return redirect(article.get_absolute_url())
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
    form = ArticleForm(request.POST or None, request.FILES or None, instance=article, user=request.user)
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        if request.user != article.author and not request.user.is_editor:
            raise Http404
        if not request.user.is_editor:
            updated.status = Article.Status.PENDING if updated.status != Article.Status.DRAFT else Article.Status.DRAFT
        updated.save()
        if updated.status == Article.Status.DRAFT:
            messages.success(request, "Dəyişikliklər yadda saxlanıldı. Məqalə qaralama olaraq qaldı.")
        elif updated.status == Article.Status.PENDING:
            messages.success(request, "Dəyişikliklər admin təsdiqinə göndərildi.")
        else:
            messages.success(request, "Məqalə dərc edildi və dəyişikliklər yadda saxlanıldı.")
        return redirect(updated.get_absolute_url())
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


@login_required
@require_POST
def react_to_article(request, slug, value):
    if value not in ArticleReaction.Value.values:
        raise Http404
    article = get_object_or_404(Article, slug=slug, status=Article.Status.PUBLISHED)
    reaction, created = ArticleReaction.objects.get_or_create(article=article, user=request.user, defaults={"value": value})
    if not created:
        if reaction.value == value:
            reaction.delete()
        else:
            reaction.value = value
            reaction.save(update_fields=["value"])
    return redirect(article.get_absolute_url())


@login_required
@require_POST
def toggle_favorite(request, slug):
    article = get_object_or_404(Article, slug=slug, status=Article.Status.PUBLISHED)
    favorite, created = Favorite.objects.get_or_create(article=article, user=request.user)
    if not created:
        favorite.delete()
    return redirect(article.get_absolute_url())


@user_passes_test(is_admin)
@require_POST
def approve_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if article.status != Article.Status.PENDING:
        messages.info(request, "Bu məqalə təsdiq gözləmir.")
    else:
        article.status = Article.Status.PUBLISHED
        article.save(update_fields=["status", "updated_at"])
        messages.success(request, "Məqalə təsdiqlənərək dərc edildi.")
    return redirect("article_management")


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
