from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Garden, Trough, WitherBatch


def ensure_seed_data():
    """Idempotent seed: users + sample gardens/troughs/batches."""
    User = get_user_model()

    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@teawither.local", "123456")

    if not User.objects.filter(username="witherer").exists():
        User.objects.create_user("witherer", "witherer@teawither.local", "123456")

    if Garden.objects.exists():
        return

    g1 = Garden.objects.create(
        name="云雾岭一号园",
        altitudeBand="800-1000m",
        notes="向阳坡，晨雾较重",
    )
    g2 = Garden.objects.create(
        name="竹影台二号园",
        altitudeBand="600-800m",
        notes="背风缓坡",
    )
    g3 = Garden.objects.create(
        name="松风谷三号园",
        altitudeBand="1000-1200m",
        notes="高山园，夜温低",
    )

    t1 = Trough.objects.create(
        garden=g1,
        troughCode="A-01",
        cultivar="福鼎大白",
        loadKg=Decimal("120.50"),
        status=Trough.STATUS_WITHERING,
    )
    t2 = Trough.objects.create(
        garden=g1,
        troughCode="A-02",
        cultivar="铁观音",
        loadKg=Decimal("95.00"),
        status=Trough.STATUS_LOADING,
    )
    t3 = Trough.objects.create(
        garden=g2,
        troughCode="B-01",
        cultivar="黄金芽",
        loadKg=Decimal("88.25"),
        status=Trough.STATUS_WITHERING,
    )

    now = timezone.now()
    WitherBatch.objects.create(
        trough=t1,
        startedAt=now - timezone.timedelta(hours=18),
        targetMoisture=Decimal("38.00"),
        actualMoisture=Decimal("37.50"),
        rollGrade="一级",
    )
    WitherBatch.objects.create(
        trough=t2,
        startedAt=now - timezone.timedelta(hours=2),
        targetMoisture=Decimal("40.00"),
        actualMoisture=None,
        rollGrade="待评",
    )
    WitherBatch.objects.create(
        trough=t3,
        startedAt=now - timezone.timedelta(hours=30),
        targetMoisture=Decimal("36.00"),
        actualMoisture=Decimal("42.00"),
        rollGrade="二级",
    )

    # Ready trough with valid moisture
    t4 = Trough.objects.create(
        garden=g2,
        troughCode="B-02",
        cultivar="龙井43",
        loadKg=Decimal("110.00"),
        status=Trough.STATUS_WITHERING,
    )
    WitherBatch.objects.create(
        trough=t4,
        startedAt=now - timezone.timedelta(hours=24),
        targetMoisture=Decimal("35.00"),
        actualMoisture=Decimal("34.80"),
        rollGrade="特级",
    )
    t4.status = Trough.STATUS_READY
    t4.save()

    # 三号园：装叶中的新槽（尚无批次）+ 另一台已达可下槽条件的槽。
    t5 = Trough.objects.create(
        garden=g3,
        troughCode="C-01",
        cultivar="白茶五号",
        loadKg=Decimal("76.40"),
        status=Trough.STATUS_LOADING,
    )
    t6 = Trough.objects.create(
        garden=g3,
        troughCode="C-02",
        cultivar="政和大白",
        loadKg=Decimal("102.75"),
        status=Trough.STATUS_WITHERING,
    )
    WitherBatch.objects.create(
        trough=t6,
        startedAt=now - timezone.timedelta(hours=20),
        targetMoisture=Decimal("38.00"),
        actualMoisture=Decimal("39.20"),
        rollGrade="一级",
    )
    t6.status = Trough.STATUS_READY
    t6.save()

    # t5 仍在装叶：批次留空；再给 t1 补一条更早的历史批次，
    # 使批次总数(6)大于槽数，避免列表行数凑巧相等掩盖对账问题。
    WitherBatch.objects.create(
        trough=t1,
        startedAt=now - timezone.timedelta(days=3),
        targetMoisture=Decimal("39.00"),
        actualMoisture=Decimal("38.60"),
        rollGrade="二级",
    )
