from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Article, Category, Comment, User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-poçt")
    first_name = forms.CharField(max_length=150, required=False, label="Ad")
    last_name = forms.CharField(max_length=150, required=False, label="Soyad")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = User.Role.USER
        if commit:
            user.save()
        return user


class ArticleForm(forms.ModelForm):
    image = forms.FileField(required=False, label="Məqalə şəkli")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.order_by("name")
        self.fields["category"].empty_label = "Kateqoriya seçin"
        self.fields["category"].required = True
        if not (user and user.is_authenticated and user.is_editor):
            if self.instance.pk and self.instance.status == Article.Status.PUBLISHED:
                self.initial["status"] = Article.Status.PENDING
            self.fields["status"].choices = [
                (Article.Status.DRAFT, "Qaralama"),
                (Article.Status.PENDING, "Admin təsdiqinə göndər"),
            ]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Şəklin ölçüsü 5 MB-dan çox ola bilməz.")
        signature = image.read(12)
        image.seek(0)
        valid_image = (
            signature.startswith(b"\x89PNG\r\n\x1a\n")
            or signature.startswith(b"\xff\xd8\xff")
            or signature.startswith((b"GIF87a", b"GIF89a"))
            or (signature.startswith(b"RIFF") and signature[8:12] == b"WEBP")
        )
        if not valid_image:
            raise forms.ValidationError("Yalnız PNG, JPEG, GIF və WebP şəkilləri yükləmək olar.")
        return image

    class Meta:
        model = Article
        fields = ("title", "summary", "category", "tags", "image", "body", "status")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Məqalənin başlığı", "autofocus": True}),
            "summary": forms.Textarea(attrs={"rows": 2, "placeholder": "Oxucular üçün qısa təqdimat (istəyə bağlı)"}),
            "tags": forms.TextInput(attrs={"placeholder": "django, python, texnologiya"}),
            "body": forms.Textarea(attrs={"rows": 18, "placeholder": "Məqalənizi yazın. Abzaslar üçün boş sətir buraxın."}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "placeholder": "Fikrinizi bölüşün...", "maxlength": 1000})}


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "bio")
        labels = {"first_name": "Ad", "last_name": "Soyad", "email": "E-poçt", "bio": "Haqqımda"}
        widgets = {"bio": forms.Textarea(attrs={"rows": 4, "maxlength": 1000, "placeholder": "Özünüz və maraqlarınız haqqında yazın"})}
