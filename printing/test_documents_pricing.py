import tempfile
import zipfile
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfWriter

from accounts.models import User

from .models import Document, PrintOrder, PrintPrice, PrintShop

PW = "Pass12345!x"


def make_pdf(pages=3):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def make_docx(pages=2):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
        archive.writestr("docProps/app.xml", f"<Properties><Pages>{pages}</Pages></Properties>")
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DocumentTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("stud", "s@x.com", PW, role="STUDENT")
        self.other = User.objects.create_user("stud2", "s2@x.com", PW, role="STUDENT")
        self.owner = User.objects.create_user("own", "o@x.com", PW, role="SHOP_OWNER")
        self.client.login(username="stud", password=PW)

    def upload(self, name, content, ctype="application/octet-stream", **extra):
        return self.client.post(
            reverse("printing:document_upload"),
            {"file": SimpleUploadedFile(name, content, ctype), **extra})

    def test_pdf_upload_detects_pages_and_hides_original_name_on_disk(self):
        response = self.upload("report.pdf", make_pdf(3))
        self.assertRedirects(response, reverse("printing:document_list"))
        doc = Document.objects.get()
        self.assertEqual((doc.user, doc.page_count, doc.file_name), (self.student, 3, "report.pdf"))
        self.assertNotIn("report", doc.file.name)

    def test_docx_upload_reads_pages(self):
        self.upload("thesis.docx", make_docx(7))
        self.assertEqual(Document.objects.get().page_count, 7)

    def test_docx_without_page_info_requires_manual_count(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", "<w:document/>")
        self.assertEqual(self.upload("a.docx", buffer.getvalue()).status_code, 200)
        self.assertEqual(Document.objects.count(), 0)
        self.upload("a.docx", buffer.getvalue(), page_count=4)
        self.assertEqual(Document.objects.get().page_count, 4)

    def test_wrong_extension_rejected(self):
        self.assertEqual(self.upload("virus.exe", b"MZ...").status_code, 200)
        self.assertEqual(Document.objects.count(), 0)

    def test_fake_pdf_rejected(self):
        self.upload("fake.pdf", b"this is not a pdf")
        self.assertEqual(Document.objects.count(), 0)

    def test_pdf_allows_manual_page_count_when_detection_fails(self):
        response = self.upload("damaged.pdf", b"%PDF-1.4 damaged", page_count=2)
        self.assertRedirects(response, reverse("printing:document_list"))
        self.assertEqual(Document.objects.get().page_count, 2)

    def test_over_25mb_rejected(self):
        self.upload("big.pdf", b"%PDF-" + b"0" * (25 * 1024 * 1024 + 1))
        self.assertEqual(Document.objects.count(), 0)

    def test_students_only_see_and_download_own_documents(self):
        self.upload("mine.pdf", make_pdf(1))
        doc = Document.objects.get()
        self.assertContains(self.client.get(reverse("printing:document_list")), "mine.pdf")
        self.assertEqual(self.client.get(reverse("printing:document_download", args=[doc.pk])).status_code, 200)
        self.client.logout(); self.client.login(username="stud2", password=PW)
        self.assertNotContains(self.client.get(reverse("printing:document_list")), "mine.pdf")
        self.assertEqual(self.client.get(reverse("printing:document_download", args=[doc.pk])).status_code, 404)

    def test_delete_unused_document_ok_but_used_blocked(self):
        self.upload("a.pdf", make_pdf(1)); self.upload("b.pdf", make_pdf(1))
        a, b = Document.objects.order_by("pk")
        shop = PrintShop.objects.create(owner=self.owner, name="S", location="L")
        price = PrintPrice.objects.create(shop=shop, paper_size="A4", color_option="Full Color", price_per_page=5)
        PrintOrder.objects.create(user=self.student, shop=shop, document=b, price=price)
        self.client.post(reverse("printing:document_delete", args=[a.pk]))
        self.client.post(reverse("printing:document_delete", args=[b.pk]))
        self.assertEqual(list(Document.objects.values_list("pk", flat=True)), [b.pk])

    def test_shop_owner_cannot_open_student_pages(self):
        self.client.logout(); self.client.login(username="own", password=PW)
        self.assertEqual(self.client.get(reverse("printing:document_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("printing:document_upload")).status_code, 403)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse("printing:document_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class PricingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("own", "o@x.com", PW, role="SHOP_OWNER")
        self.owner2 = User.objects.create_user("own2", "o2@x.com", PW, role="SHOP_OWNER")
        self.student = User.objects.create_user("stud", "s@x.com", PW, role="STUDENT")
        self.client.login(username="own", password=PW)

    def make_shop(self):
        self.client.post(reverse("printing:shop_create"), {"name": "Copy Corner", "location": "Near CIT-U", "is_active": "on"})
        return PrintShop.objects.get(name="Copy Corner")

    def test_owner_creates_shop_and_price(self):
        shop = self.make_shop()
        self.assertEqual(shop.owner, self.owner)
        self.client.post(reverse("printing:price_create", args=[shop.pk]),
                         {"paper_size": "A4", "color_option": "Black & White", "price_per_page": "2.50"})
        self.assertEqual(shop.prices.get().price_per_page, Decimal("2.50"))

    def test_price_must_be_positive_and_unique(self):
        shop = self.make_shop()
        url = reverse("printing:price_create", args=[shop.pk])
        data = {"paper_size": "A4", "color_option": "Black & White", "price_per_page": "0"}
        self.client.post(url, data)
        self.assertEqual(shop.prices.count(), 0)
        data["price_per_page"] = "2"
        self.client.post(url, data); self.client.post(url, data)
        self.assertEqual(shop.prices.count(), 1)

    def test_owner_cannot_touch_another_owners_shop_or_price(self):
        shop = PrintShop.objects.create(owner=self.owner2, name="Other", location="X")
        price = PrintPrice.objects.create(shop=shop, paper_size="A4", color_option="Full Color", price_per_page=5)
        self.assertEqual(self.client.get(reverse("printing:shop_edit", args=[shop.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("printing:price_delete", args=[price.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("printing:price_create", args=[shop.pk]), {}).status_code, 404)

    def test_price_in_use_cannot_be_deleted(self):
        shop = self.make_shop()
        price = PrintPrice.objects.create(shop=shop, paper_size="A4", color_option="Full Color", price_per_page=5)
        doc = Document.objects.create(user=self.student, file="documents/a.pdf", page_count=2, file_name="a.pdf")
        PrintOrder.objects.create(user=self.student, shop=shop, document=doc, price=price)
        self.client.post(reverse("printing:price_delete", args=[price.pk]))
        self.client.post(reverse("printing:shop_delete", args=[shop.pk]))
        self.assertTrue(PrintPrice.objects.filter(pk=price.pk).exists())
        self.assertTrue(PrintShop.objects.filter(pk=shop.pk).exists())

    def test_student_cannot_open_shop_pages(self):
        self.client.logout(); self.client.login(username="stud", password=PW)
        self.assertEqual(self.client.get(reverse("printing:shop_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("printing:shop_create")).status_code, 403)
