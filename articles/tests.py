from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Article, Category


User = get_user_model()


class RoleAndArticleFlowTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_superuser(
            username="root_test", email="root@example.test", password="Strong-Root-123!"
        )
        self.admin = User.objects.create_user(
            username="editor_test", password="Strong-Editor-123!", role=User.Role.ADMIN
        )
        self.author = User.objects.create_user(username="author_test", password="Strong-Author-123!")
        self.other_author = User.objects.create_user(username="other_test", password="Strong-Other-123!")
        self.other_admin = User.objects.create_user(
            username="other_editor_test", password="Strong-Other-123!", role=User.Role.ADMIN
        )
        self.category = Category.objects.create(name="Test kateqoriyası", slug="test-kateqoriyasi")
        self.published = self.make_article(self.author, "Dərc edilmiş məqalə", Article.Status.PUBLISHED)
        self.author_draft = self.make_article(self.author, "Müəllifin qaralaması", Article.Status.DRAFT)
        self.other_draft = self.make_article(self.other_author, "Başqa müəllifin qaralaması", Article.Status.DRAFT)

    def make_article(self, author, title, status):
        return Article.objects.create(
            author=author,
            category=self.category,
            title=title,
            body=("Məqalənin əsas mətni ana səhifədə tam görünməlidir. " * 5),
            status=status,
        )

    def article_data(self, title, status=Article.Status.PUBLISHED):
        return {
            "title": title,
            "summary": "Qısa təqdimat",
            "category": str(self.category.pk),
            "tags": "django, imtahan",
            "body": "Yeni məqalənin tam əsas mətni bu hissədə saxlanılır və oxucuya göstərilir.",
            "status": status,
        }

    def test_guest_reads_published_articles_only(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.published.title)
        self.assertContains(response, self.published.body)
        self.assertNotContains(response, self.author_draft.title)
        self.assertEqual(self.client.get(self.published.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.author_draft.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse("article_create")).status_code, 302)

    def test_user_sees_own_draft_and_only_edits_or_deletes_own_articles(self):
        self.client.force_login(self.author)
        home = self.client.get(reverse("home"))
        self.assertContains(home, self.author_draft.title)
        self.assertNotContains(home, self.other_draft.title)
        self.assertEqual(self.client.get(self.other_draft.get_absolute_url()).status_code, 404)

        edit_url = reverse("article_edit", kwargs={"slug": self.author_draft.slug})
        response = self.client.post(edit_url, self.article_data("Müəllifin yenilənmiş qaralaması", Article.Status.DRAFT))
        self.assertEqual(response.status_code, 302)
        self.author_draft.refresh_from_db()
        self.assertEqual(self.author_draft.title, "Müəllifin yenilənmiş qaralaması")

        other_edit = reverse("article_edit", kwargs={"slug": self.other_draft.slug})
        other_delete = reverse("article_delete", kwargs={"slug": self.other_draft.slug})
        self.assertEqual(self.client.post(other_edit, self.article_data("İcazəsiz dəyişiklik")).status_code, 404)
        self.assertEqual(self.client.post(other_delete).status_code, 404)

        delete_url = reverse("article_delete", kwargs={"slug": self.author_draft.slug})
        self.assertEqual(self.client.post(delete_url).status_code, 302)
        self.assertFalse(Article.objects.filter(pk=self.author_draft.pk).exists())

    def test_user_can_publish_or_save_draft_and_sees_full_body_on_home(self):
        self.client.force_login(self.author)
        for status, title in (
            (Article.Status.PUBLISHED, "İstifadəçinin dərc etdiyi yazı"),
            (Article.Status.DRAFT, "İstifadəçinin saxladığı qaralama"),
        ):
            response = self.client.post(reverse("article_create"), self.article_data(title, status))
            self.assertRedirects(response, reverse("home"))
            article = Article.objects.get(title=title)
            self.assertEqual(article.author, self.author)
            self.assertEqual(article.status, status)
            self.assertContains(self.client.get(reverse("home")), article.body)

    def test_admin_can_manage_all_articles_and_block_users_but_cannot_assign_admin(self):
        self.client.force_login(self.admin)
        create = self.client.post(reverse("article_create"), self.article_data("Admin tərəfindən yaradıldı"))
        self.assertRedirects(create, reverse("home"))

        edit_url = reverse("article_edit", kwargs={"slug": self.published.slug})
        self.assertEqual(self.client.post(edit_url, self.article_data("Admin redaktə etdi")).status_code, 302)
        self.published.refresh_from_db()
        self.assertEqual(self.published.title, "Admin redaktə etdi")

        delete_url = reverse("article_delete", kwargs={"slug": self.other_draft.slug})
        self.assertEqual(self.client.post(delete_url).status_code, 302)
        self.assertFalse(Article.objects.filter(pk=self.other_draft.pk).exists())

        block_url = reverse("toggle_user_block", kwargs={"user_id": self.author.pk})
        self.assertEqual(self.client.post(block_url).status_code, 302)
        self.author.refresh_from_db()
        self.assertFalse(self.author.is_active)

        cannot_block_editor = reverse("toggle_user_block", kwargs={"user_id": self.other_admin.pk})
        self.assertEqual(self.client.post(cannot_block_editor).status_code, 302)
        self.other_admin.refresh_from_db()
        self.assertTrue(self.other_admin.is_active)

        promote_url = reverse("toggle_admin_role", kwargs={"user_id": self.other_author.pk})
        self.assertEqual(self.client.post(promote_url).status_code, 404)

    def test_super_admin_can_assign_and_revoke_admin_and_block_users(self):
        self.client.force_login(self.super_admin)
        self.assertTrue(self.super_admin.is_editor)

        create = self.client.post(reverse("article_create"), self.article_data("Super Admin yaratdı"))
        self.assertRedirects(create, reverse("home"))
        edit_url = reverse("article_edit", kwargs={"slug": self.published.slug})
        self.assertEqual(self.client.post(edit_url, self.article_data("Super Admin redaktə etdi")).status_code, 302)
        delete_url = reverse("article_delete", kwargs={"slug": self.other_draft.slug})
        self.assertEqual(self.client.post(delete_url).status_code, 302)
        self.assertFalse(Article.objects.filter(pk=self.other_draft.pk).exists())

        promote_url = reverse("toggle_admin_role", kwargs={"user_id": self.author.pk})
        self.assertEqual(self.client.post(promote_url).status_code, 302)
        self.author.refresh_from_db()
        self.assertEqual(self.author.role, User.Role.ADMIN)
        self.assertTrue(self.author.is_editor)

        self.assertEqual(self.client.post(promote_url).status_code, 302)
        self.author.refresh_from_db()
        self.assertEqual(self.author.role, User.Role.USER)

        block_url = reverse("toggle_user_block", kwargs={"user_id": self.other_author.pk})
        self.assertEqual(self.client.post(block_url).status_code, 302)
        self.other_author.refresh_from_db()
        self.assertFalse(self.other_author.is_active)
        self.assertFalse(self.client.login(username="other_test", password="Strong-Other-123!"))

        self.assertEqual(
            self.client.post(reverse("toggle_user_block", kwargs={"user_id": self.super_admin.pk})).status_code,
            302,
        )
        self.super_admin.refresh_from_db()
        self.assertTrue(self.super_admin.is_active)

    def test_article_management_lists_every_authors_draft_for_admins_only(self):
        url = reverse("article_management")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(url), self.other_draft.title)
        self.client.force_login(self.super_admin)
        self.assertContains(self.client.get(url), self.other_draft.title)

    def test_only_one_super_admin_can_exist(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_superuser(
                    username="second_root", email="second-root@example.test", password="Strong-Root-456!"
                )

    def test_registration_login_and_logout(self):
        registration = self.client.post(reverse("register"), {
            "username": "new_reader",
            "first_name": "Yeni",
            "last_name": "Oxucu",
            "email": "new-reader@example.test",
            "password1": "Distinct-Passphrase-892!",
            "password2": "Distinct-Passphrase-892!",
        })
        self.assertRedirects(registration, reverse("home"))
        new_user = User.objects.get(username="new_reader")
        self.assertEqual(new_user.role, User.Role.USER)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)
        login = self.client.post(reverse("login"), {"username": "new_reader", "password": "Distinct-Passphrase-892!"})
        self.assertEqual(login.status_code, 302)
