from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Article, Comment, User


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
    class Meta:
        model = Article
        fields = ("title", "summary", "category", "tags", "body", "status")
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
        fields = ("first_name", "last_name", "email")
        labels = {"first_name": "Ad", "last_name": "Soyad", "email": "E-poçt"}
