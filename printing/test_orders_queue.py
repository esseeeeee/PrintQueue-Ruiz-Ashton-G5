from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Document, Payment, PrintOrder, PrintPrice, PrintShop

PW = "Pass12345!x"


class OrderQueueBase(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("stud", "s@x.com", PW, role="STUDENT")
        self.other = User.objects.create_user("stud2", "s2@x.com", PW, role="STUDENT")
        self.owner = User.objects.create_user("own", "o@x.com", PW, role="SHOP_OWNER")
        self.owner2 = User.objects.create_user("own2", "o2@x.com", PW, role="SHOP_OWNER")
        self.shop = PrintShop.objects.create(owner=self.owner, name="Copy Corner", location="L")
        self.shop2 = PrintShop.objects.create(owner=self.owner2, name="Other", location="L")
        self.bw = PrintPrice.objects.create(shop=self.shop, paper_size="A4", color_option="Black & White", price_per_page=Decimal("2.00"))
        self.color = PrintPrice.objects.create(shop=self.shop, paper_size="A4", color_option="Full Color", price_per_page=Decimal("5.00"))
        self.doc = Document.objects.create(user=self.student, file="documents/a.pdf", page_count=10, file_name="a.pdf")

    def login(self, name):
        self.client.logout()
        self.client.login(username=name, password=PW)

    def order(self, **kw):
        return PrintOrder.objects.create(
            user=self.student, shop=self.shop, document=self.doc, price=kw.pop("price", self.bw), **kw)


class StudentOrderTests(OrderQueueBase):
    def setUp(self):
        super().setUp()
        self.login("stud")

    def test_create_order_computes_total_on_server(self):
        response = self.client.post(reverse("printing:order_create"), {"document": self.doc.pk, "price": self.bw.pk})
        order = PrintOrder.objects.get()
        self.assertRedirects(response, reverse("printing:order_detail", args=[order.pk]))
        self.assertEqual((order.user, order.shop, order.status, order.total_amount),
                         (self.student, self.shop, "PENDING", Decimal("20.00")))

    def test_cannot_order_someone_elses_document_or_closed_shop(self):
        self.login("stud2")
        self.client.post(reverse("printing:order_create"), {"document": self.doc.pk, "price": self.bw.pk})
        self.assertEqual(PrintOrder.objects.count(), 0)
        self.login("stud")
        self.shop.is_active = False; self.shop.save()
        self.client.post(reverse("printing:order_create"), {"document": self.doc.pk, "price": self.bw.pk})
        self.assertEqual(PrintOrder.objects.count(), 0)

    def test_edit_pending_recalculates_total(self):
        order = self.order()
        self.client.post(reverse("printing:order_edit", args=[order.pk]), {"document": self.doc.pk, "price": self.color.pk})
        order.refresh_from_db()
        self.assertEqual((order.price, order.total_amount), (self.color, Decimal("50.00")))

    def test_cannot_edit_or_cancel_after_printing_started(self):
        order = self.order(); order.status = "PRINTING"; order.save()
        self.client.post(reverse("printing:order_edit", args=[order.pk]), {"document": self.doc.pk, "price": self.color.pk})
        self.client.post(reverse("printing:order_cancel", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual((order.status, order.price), ("PRINTING", self.bw))

    def test_cancel_then_delete(self):
        order = self.order()
        self.client.post(reverse("printing:order_cancel", args=[order.pk]))
        order.refresh_from_db(); self.assertEqual(order.status, "CANCELLED")
        self.client.post(reverse("printing:order_delete", args=[order.pk]))
        self.assertFalse(PrintOrder.objects.filter(pk=order.pk).exists())
        self.assertTrue(Document.objects.filter(pk=self.doc.pk).exists())

    def test_completed_order_cannot_be_deleted(self):
        order = self.order(); order.status = "COMPLETED"; order.save()
        self.client.post(reverse("printing:order_delete", args=[order.pk]))
        self.assertTrue(PrintOrder.objects.filter(pk=order.pk).exists())

    def test_students_only_see_their_own_orders(self):
        order = self.order()
        self.assertContains(self.client.get(reverse("printing:order_list")), "a.pdf")
        self.login("stud2")
        self.assertNotContains(self.client.get(reverse("printing:order_list")), "a.pdf")
        self.assertEqual(self.client.get(reverse("printing:order_detail", args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("printing:order_cancel", args=[order.pk])).status_code, 404)

    def test_filter_by_status(self):
        self.order(); done = self.order(); done.status = "COMPLETED"; done.save()
        response = self.client.get(reverse("printing:order_list"), {"status": "COMPLETED"})
        self.assertEqual(len(response.context["page_obj"].object_list), 1)

    def test_shop_owner_blocked_from_student_order_pages(self):
        self.login("own")
        self.assertEqual(self.client.get(reverse("printing:order_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("printing:order_create")).status_code, 403)


class ShopQueueTests(OrderQueueBase):
    def setUp(self):
        super().setUp()
        self.login("own")

    def test_owner_sees_only_own_shop_orders(self):
        mine = self.order()
        other_price = PrintPrice.objects.create(shop=self.shop2, paper_size="A4", color_option="Full Color", price_per_page=3)
        theirs = PrintOrder.objects.create(user=self.student, shop=self.shop2, document=self.doc, price=other_price)
        response = self.client.get(reverse("printing:shop_order_list"))
        self.assertEqual([o.pk for o in response.context["page_obj"]], [mine.pk])
        self.assertEqual(self.client.get(reverse("printing:shop_order_detail", args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("printing:shop_order_status", args=[theirs.pk]), {"status": "PRINTING"}).status_code, 404)

    def test_status_workflow(self):
        order = self.order()
        url = reverse("printing:shop_order_status", args=[order.pk])
        self.client.post(url, {"status": "READY FOR PICKUP"})   # skipping a step is rejected
        order.refresh_from_db(); self.assertEqual(order.status, "PENDING")
        self.client.post(url, {"status": "PRINTING"})
        self.client.post(url, {"status": "READY FOR PICKUP"})
        self.client.post(url, {"status": "COMPLETED"})           # only via payment
        order.refresh_from_db(); self.assertEqual(order.status, "READY FOR PICKUP")
        self.client.post(url, {"status": "BOGUS"})
        order.refresh_from_db(); self.assertEqual(order.status, "READY FOR PICKUP")

    def test_cash_payment_completes_order(self):
        order = self.order(); order.status = "READY FOR PICKUP"; order.save()
        url = reverse("printing:shop_order_payment", args=[order.pk])
        self.client.post(url, {"amount_paid": "10.00"})  # less than the 20.00 total
        self.assertEqual(Payment.objects.count(), 0)
        self.client.post(url, {"amount_paid": "20.00"})
        order.refresh_from_db()
        self.assertEqual(order.status, "COMPLETED")
        self.assertEqual(order.payment.collected_by, self.owner)

    def test_payment_rejected_unless_ready(self):
        order = self.order()
        self.client.post(reverse("printing:shop_order_payment", args=[order.pk]), {"amount_paid": "20"})
        self.assertEqual(Payment.objects.count(), 0)

    def test_owner_downloads_file_only_for_own_shop_orders(self):
        order = self.order()
        url = reverse("printing:document_download", args=[self.doc.pk])
        self.assertNotEqual(self.client.get(url).status_code, 403)
        self.login("own2")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(order.shop.owner, self.owner)

    def test_student_blocked_from_queue(self):
        self.login("stud")
        self.assertEqual(self.client.get(reverse("printing:shop_order_list")).status_code, 403)
