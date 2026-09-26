import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.gardens.models import Garden, Trough, WitherBatch
from apps.gardens.seed import ensure_seed_data


def _tbody_rows(html):
    """提取 <tbody>…</tbody> 内 <tr…> 的数量。"""
    body = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    if not body:
        return 0
    return len(re.findall(r"<tr[\s>]", body.group(1)))


def _row_keys(html, key_pattern):
    """提取每行中可对账的稳定标识（编辑链接里的 pk）。"""
    body = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    if not body:
        return set()
    return set(re.findall(key_pattern, body.group(1)))


class ReconciliationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_seed_data()
        cls.user = get_user_model().objects.get(username="admin")

    def setUp(self):
        self.client.force_login(self.user)

    # ---- 种子非零 ----

    def test_seed_is_nonzero_in_every_dimension(self):
        self.assertGreater(Garden.objects.count(), 0)
        self.assertGreater(Trough.objects.count(), 0)
        self.assertGreater(WitherBatch.objects.count(), 0)
        self.assertGreater(
            Trough.objects.filter(status=Trough.STATUS_READY).count(), 0
        )

    # ---- 首页四项 = 列表行数（无额外手工条件）----

    def test_home_stats_match_unfiltered_list_rows(self):
        home = self.client.get(reverse("home")).content.decode()

        def stat(label):
            m = re.search(
                r'<div class="num">(\d+)</div><div class="label">%s</div>' % label,
                home,
            )
            self.assertIsNotNone(m, f"首页缺少指标 {label}")
            return int(m.group(1))

        home_gardens = stat("茶园")
        home_troughs = stat("萎凋槽")
        home_batches = stat("萎凋批次")
        home_ready = stat("可下槽")

        # 无筛全量列表
        garden_rows = _tbody_rows(
            self.client.get(reverse("garden_list")).content.decode()
        )
        trough_rows = _tbody_rows(
            self.client.get(reverse("trough_list")).content.decode()
        )
        batch_rows = _tbody_rows(
            self.client.get(reverse("batch_list")).content.decode()
        )
        # 状态子集：可下槽
        ready_rows = _tbody_rows(
            self.client.get(
                reverse("trough_list"), {"status": "ready"}
            ).content.decode()
        )

        self.assertEqual(home_gardens, garden_rows)
        self.assertEqual(home_troughs, trough_rows)
        self.assertEqual(home_batches, batch_rows)
        self.assertEqual(home_ready, ready_rows)
        # 状态子集必须是真子集，否则筛选举足轻重
        self.assertLess(ready_rows, trough_rows)

    # ---- 首页不随筛选条件变化 ----

    def test_home_is_unaffected_by_filter_query_params(self):
        def stat_block(html):
            # 只比对统计数字区块；导航栏含每请求 CSRF token，不能整页比对。
            m = re.search(r'<div class="stats">(.*?)</div>\s*<p', html, re.S)
            return re.sub(r"\s+", "", m.group(1))

        before = self.client.get(reverse("home")).content.decode()
        after = self.client.get(
            reverse("home"), {"status": "ready", "garden": "1"}
        ).content.decode()
        self.assertEqual(stat_block(before), stat_block(after))

    # ---- HTMX 局部行集合 == 整页行集合，覆盖每种筛选组合 ----

    def test_htmx_partial_rows_equal_full_page_troughs(self):
        edit_pk = reverse("trough_edit", args=[0]).replace("0", "PK")
        pattern = re.escape(edit_pk).replace("PK", r"(\d+)")
        for qs in [
            {},
            {"status": "loading"},
            {"status": "withering"},
            {"status": "ready"},
            {"status": "BOGUS"},  # 非法值回落全量
        ]:
            full = self.client.get(reverse("trough_list"), qs).content.decode()
            partial = self.client.get(
                reverse("trough_list"), qs, HTTP_HX_REQUEST="true"
            ).content.decode()
            self.assertEqual(
                _row_keys(full, pattern),
                _row_keys(partial, pattern),
                f"槽列表 HTMX/整页行集不一致: {qs}",
            )

    def test_htmx_partial_rows_equal_full_page_batches(self):
        edit_pk = reverse("batch_edit", args=[0]).replace("0", "PK")
        pattern = re.escape(edit_pk).replace("PK", r"(\d+)")
        garden_ids = list(Garden.objects.values_list("pk", flat=True))
        cases = [{}] + [{"garden": gid} for gid in garden_ids]
        cases.append({"garden": 999999})  # 不存在的茶园 → 空行集
        for qs in cases:
            full = self.client.get(reverse("batch_list"), qs).content.decode()
            partial = self.client.get(
                reverse("batch_list"), qs, HTTP_HX_REQUEST="true"
            ).content.decode()
            self.assertEqual(
                _row_keys(full, pattern),
                _row_keys(partial, pattern),
                f"批次列表 HTMX/整页行集不一致: {qs}",
            )

    # ---- 按茶园筛选真的过滤 ----

    def test_batch_garden_filter_subset(self):
        g = Garden.objects.first()
        full = _tbody_rows(self.client.get(reverse("batch_list")).content.decode())
        subset = _tbody_rows(
            self.client.get(reverse("batch_list"), {"garden": g.pk}).content.decode()
        )
        expected = WitherBatch.objects.filter(trough__garden=g).count()
        self.assertEqual(subset, expected)
        self.assertLessEqual(subset, full)
