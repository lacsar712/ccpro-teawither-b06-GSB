"""对账测试：首页四项必须能用对应列表（无筛全量 / ready 状态子集）数行复算，
且 HTMX 局部表与整页打开的行集合一致。
"""

import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Garden, Trough, WitherBatch
from .seed import ensure_seed_data

# 列表每行恰有一个「编辑」链接，用其主键标识行集合
_ROW_RE = re.compile(r'href="/(gardens|troughs|batches)/(\d+)/edit/"')


def row_ids(html, kind):
    return sorted(int(pk) for k, pk in _ROW_RE.findall(html) if k == kind)


class ReconcileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_seed_data()
        cls.user = get_user_model().objects.get(username="admin")

    def setUp(self):
        self.client.force_login(self.user)

    # -- 种子撑起非零 -------------------------------------------------

    def test_seed_supports_nonzero_stats(self):
        self.assertGreater(Garden.objects.count(), 0)
        self.assertGreater(Trough.objects.count(), 0)
        self.assertGreater(WitherBatch.objects.count(), 0)
        for value, _label in Trough.STATUS_CHOICES:
            self.assertGreater(
                Trough.objects.filter(status=value).count(),
                0,
                f"状态子集 {value} 为空",
            )
        for g in Garden.objects.all():
            self.assertGreater(
                WitherBatch.objects.filter(trough__garden=g).count(),
                0,
                f"茶园 {g} 无批次",
            )

    # -- 首页四项对账 --------------------------------------------------

    def test_home_counts_reconcile_with_lists(self):
        home = self.client.get(reverse("home"))
        ctx = home.context

        gardens_page = self.client.get(reverse("garden_list"))
        self.assertEqual(
            ctx["garden_count"], len(row_ids(gardens_page.content.decode(), "gardens"))
        )

        troughs_page = self.client.get(reverse("trough_list"))
        self.assertEqual(
            ctx["trough_count"], len(row_ids(troughs_page.content.decode(), "troughs"))
        )

        batches_page = self.client.get(reverse("batch_list"))
        self.assertEqual(
            ctx["batch_count"], len(row_ids(batches_page.content.decode(), "batches"))
        )

        ready_page = self.client.get(reverse("trough_list"), {"status": "ready"})
        self.assertEqual(
            ctx["ready_count"], len(row_ids(ready_page.content.decode(), "troughs"))
        )

        # 四项非零（种子撑起）
        for key in ("garden_count", "trough_count", "batch_count", "ready_count"):
            self.assertGreater(ctx[key], 0, key)

    def test_home_ignores_filter_params(self):
        plain = self.client.get(reverse("home"))
        with_params = self.client.get(reverse("home"), {"status": "ready", "garden": "1"})
        for key in ("garden_count", "trough_count", "batch_count", "ready_count"):
            self.assertEqual(plain.context[key], with_params.context[key], key)

    # -- HTMX 局部表与整页行集合一致 -----------------------------------

    def test_htmx_partial_matches_full_page(self):
        garden = Garden.objects.order_by("pk").first()
        cases = [
            ("garden_list", {}, "gardens"),
            ("trough_list", {}, "troughs"),
            ("trough_list", {"status": "ready"}, "troughs"),
            ("trough_list", {"status": "withering"}, "troughs"),
            ("trough_list", {"status": "loading"}, "troughs"),
            ("batch_list", {}, "batches"),
            ("batch_list", {"garden": str(garden.pk)}, "batches"),
        ]
        for name, params, kind in cases:
            with self.subTest(url=name, params=params):
                url = reverse(name)
                full = self.client.get(url, params)
                partial = self.client.get(url, params, HTTP_HX_REQUEST="true")
                self.assertEqual(full.status_code, 200)
                self.assertEqual(partial.status_code, 200)
                self.assertEqual(
                    row_ids(full.content.decode(), kind),
                    row_ids(partial.content.decode(), kind),
                )

    # -- 筛选行为 ------------------------------------------------------

    def test_trough_status_filter(self):
        resp = self.client.get(reverse("trough_list"), {"status": "ready"})
        expect = sorted(
            Trough.objects.filter(status=Trough.STATUS_READY).values_list("pk", flat=True)
        )
        self.assertEqual(row_ids(resp.content.decode(), "troughs"), expect)
        self.assertContains(resp, 'name="status"')

    def test_trough_status_filter_invalid_falls_back_to_full(self):
        resp = self.client.get(reverse("trough_list"), {"status": "bogus"})
        self.assertEqual(
            len(row_ids(resp.content.decode(), "troughs")), Trough.objects.count()
        )

    def test_batch_garden_filter(self):
        garden = Garden.objects.order_by("pk").first()
        resp = self.client.get(reverse("batch_list"), {"garden": str(garden.pk)})
        expect = sorted(
            WitherBatch.objects.filter(trough__garden=garden).values_list("pk", flat=True)
        )
        self.assertEqual(row_ids(resp.content.decode(), "batches"), expect)
        self.assertContains(resp, 'name="garden"')

    def test_batch_garden_filter_invalid_falls_back_to_full(self):
        resp = self.client.get(reverse("batch_list"), {"garden": "99999"})
        self.assertEqual(
            len(row_ids(resp.content.decode(), "batches")), WitherBatch.objects.count()
        )
