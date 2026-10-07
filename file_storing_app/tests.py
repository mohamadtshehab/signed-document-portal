import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import Document
from .utils import CertificateAuthority, MalwareScanner


class PublicPageTests(SimpleTestCase):
    def test_root_and_home_load(self):
        response = self.client.get("/")
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)

    def test_verification_requires_registration_session(self):
        self.assertRedirects(
            self.client.get(reverse("verify")),
            reverse("register"),
            fetch_redirect_response=False,
        )


class CertificateTests(SimpleTestCase):
    def test_generated_ca_signs_document(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            authority = CertificateAuthority()
            key, certificate = authority.initialize_ca()
            document = SimpleUploadedFile("document.txt", b"sample document")
            signature = authority.sign_document(document, key)
            self.assertTrue(authority.verify_document(document, signature, certificate))
            self.assertEqual(authority.load_ca_certificate(), certificate)

    def test_unavailable_scanner_rejects_upload(self):
        document = SimpleUploadedFile("document.txt", b"sample document")
        with patch("file_storing_app.utils.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(ValidationError):
                MalwareScanner.is_safe(document)
        self.assertEqual(document.read(), b"sample document")


class UploadTests(TestCase):
    def test_upload_and_download(self):
        user = get_user_model().objects.create_user(
            phone_number="0912345678",
            password="test-password-123",
            birth_date="1990-01-01",
            national_id="12345678901",
        )
        self.client.force_login(user)
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            CertificateAuthority().initialize_ca()
            upload = SimpleUploadedFile("sample.pdf", b"sample document", content_type="application/pdf")
            with patch("file_storing_app.views.MalwareScanner.is_safe", return_value=True):
                response = self.client.post(reverse("uploads"), {"file": upload})
            self.assertRedirects(response, reverse("success"), fetch_redirect_response=False)
            document = Document.objects.get(user=user)
            self.assertEqual(self.client.get(reverse("download", args=[document.pk])).content, b"sample document")
