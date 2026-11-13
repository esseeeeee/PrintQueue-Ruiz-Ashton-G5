from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from accounts.models import User

from .models import Document, Payment, PrintOrder, PrintPrice, PrintShop
from .validators import validate_document_file
from django.core.files.uploadedfile import SimpleUploadedFile


class DataModelTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("stud", "s@x.com", "Pass12345!x", role="STUDENT")
        self.other = User.objects.create_user("stud2", "s2@x.com", "Pass12345!x", role="STUDENT")
        self.owner = User.objects.create_user("own", "o@x.com", "Pass12345!x", role="SHOP_OWNER")
        self.owner2 = User.objects.create_user("own2", "o2@x.com", "Pass12345!x", role="SHOP_OWNER")
        self.shop = PrintShop.objects.create(owner=self.owner, name="Copy Corner", location="Near CIT-U")
        self.shop2 = PrintShop.objects.create(owner=self.owner2, name="Other", location="Elsewhere")
        self.price = PrintPrice.objects.create(
            shop=self.shop, paper_size="A4", color_option="Black & White", price_per_page=Decimal("2.00"))
        self.doc = Document.objects.create(user=self.student, file="documents/a.pdf", page_count=10)

    def order(self, **kw):
        return PrintOrder.objects.create(
            user=self.student, shop=self.shop, document=self.doc, price=self.price, **kw)

    def test_total_is_pages_times_price(self):
        self.assertEqual(self.order().total_amount, Decimal("20.00"))

    def test_br01_unique_email(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("dup", "S@x.com".lower(), "Pass12345!x")

    def test_br02_role_check(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("bad", "bad@x.com", "Pass12345!x", role="HACKER")

    def test_br03_file_rules(self):
        with self.assertRaises(ValidationError):
            validate_document_file(SimpleUploadedFile("a.exe", b"x"))
        validate_document_file(SimpleUploadedFile("a.docx", b"x"))

    def test_br04_price_positive(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PrintPrice.objects.create(shop=self.shop, paper_size="Long",
                                      color_option="Full Color", price_per_page=0)

    def test_br05_status_check(self):
        o = self.order()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PrintOrder.objects.filter(pk=o.pk).update(status="LOST")

    def test_br06_total_not_negative(self):
        o = self.order()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PrintOrder.objects.filter(pk=o.pk).update(total_amount=-1)

    def test_br07_students_see_only_own_orders(self):
        self.order()
        self.assertEqual(PrintOrder.objects.for_student(self.other).count(), 0)
        self.assertEqual(PrintOrder.objects.for_student(self.student).count(), 1)

    def test_br08_owner_sees_only_own_shop_orders(self):
        self.order()
        self.assertEqual(PrintOrder.objects.for_shop_owner(self.owner2).count(), 0)
        self.assertEqual(PrintOrder.objects.for_shop_owner(self.owner).count(), 1)

    def test_br09_document_with_order_cannot_be_deleted(self):
        self.order()
        with self.assertRaises(ProtectedError):
            self.doc.delete()

    def test_br10_payment_only_when_ready(self):
        o = self.order()
        with self.assertRaises(ValidationError):
            Payment.objects.create(order=o, amount_paid=20, collected_by=self.owner)
        o.status = PrintOrder.Status.READY
        o.save()
        p = Payment.objects.create(order=o, amount_paid=20, collected_by=self.owner)
        self.assertEqual(p.order, o)

    def test_cannot_order_someone_elses_document(self):
        with self.assertRaises(ValidationError):
            PrintOrder.objects.create(user=self.other, shop=self.shop, document=self.doc, price=self.price)

    def test_price_must_belong_to_shop(self):
        with self.assertRaises(ValidationError):
            PrintOrder.objects.create(user=self.student, shop=self.shop2, document=self.doc, price=self.price)
