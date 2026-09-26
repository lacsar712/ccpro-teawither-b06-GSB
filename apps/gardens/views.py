from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from .forms import (
    BatchGardenFilterForm,
    GardenForm,
    TroughForm,
    TroughStatusFilterForm,
    WitherBatchForm,
)
from .models import Garden, Trough, WitherBatch


def _wants_htmx(request):
    return request.headers.get("HX-Request") == "true"


# ---------------------------------------------------------------------------
# 对账用行集：首页统计与列表页必须共用同一组 ORM 行集函数，
# 禁止首页另写 SQL / 聚合，杜绝“差 1”。
# 无额外手工条件时：
#   garden_rows()          → 茶园列表全部行
#   trough_rows()          → 槽列表全部行
#   trough_rows(status=x)  → 槽列表按状态筛选后的子集行
#   batch_rows()           → 批次列表全部行
#   batch_rows(garden_id=) → 批次列表按茶园筛选后的子集行
# ---------------------------------------------------------------------------


def garden_rows():
    return Garden.objects.all()


def trough_rows(status=None):
    qs = Trough.objects.select_related("garden").all()
    if status in (
        Trough.STATUS_LOADING,
        Trough.STATUS_WITHERING,
        Trough.STATUS_READY,
    ):
        qs = qs.filter(status=status)
    return qs


def batch_rows(garden_id=None):
    qs = WitherBatch.objects.select_related("trough", "trough__garden").all()
    if garden_id:
        qs = qs.filter(trough__garden_id=garden_id)
    return qs


@login_required
def home(request):
    # 首页本身不随列表筛选条件变化；四项主统计直接取无筛行集的行数，
    # 其中“可下槽数”取状态子集行集的行数。
    context = {
        "garden_count": garden_rows().count(),
        "trough_count": trough_rows().count(),
        "batch_count": batch_rows().count(),
        "ready_count": trough_rows(status=Trough.STATUS_READY).count(),
        "withering_count": trough_rows(status=Trough.STATUS_WITHERING).count(),
        "loading_count": trough_rows(status=Trough.STATUS_LOADING).count(),
    }
    return render(request, "home.html", context)


class HtmxTableMixin:
    """整页与 HTMX 局部共用同一个 self.object_list：
    局部模板只渲染 get_queryset() 的结果，行集必然与整页一致。"""

    partial_template_name = ""

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        if _wants_htmx(request):
            return HttpResponse(
                render_to_string(
                    self.partial_template_name,
                    {self.context_object_name: self.object_list},
                    request=request,
                )
            )
        return super().get(request, *args, **kwargs)


# ---- Garden ----


class GardenListView(HtmxTableMixin, LoginRequiredMixin, ListView):
    model = Garden
    template_name = "gardens/list.html"
    context_object_name = "gardens"
    partial_template_name = "gardens/_table.html"

    def get_queryset(self):
        return garden_rows()


class GardenCreateView(LoginRequiredMixin, CreateView):
    model = Garden
    form_class = GardenForm
    template_name = "gardens/form.html"
    success_url = reverse_lazy("garden_list")

    def form_valid(self, form):
        messages.success(self.request, "茶园已创建")
        response = super().form_valid(form)
        if _wants_htmx(self.request):
            return redirect("garden_list")
        return response


class GardenUpdateView(LoginRequiredMixin, UpdateView):
    model = Garden
    form_class = GardenForm
    template_name = "gardens/form.html"
    success_url = reverse_lazy("garden_list")

    def form_valid(self, form):
        messages.success(self.request, "茶园已更新")
        return super().form_valid(form)


class GardenDeleteView(LoginRequiredMixin, DeleteView):
    model = Garden
    template_name = "gardens/confirm_delete.html"
    success_url = reverse_lazy("garden_list")

    def form_valid(self, form):
        messages.success(self.request, "茶园已删除")
        return super().form_valid(form)


# ---- Trough ----


class TroughListView(HtmxTableMixin, LoginRequiredMixin, ListView):
    model = Trough
    template_name = "troughs/list.html"
    context_object_name = "troughs"
    partial_template_name = "troughs/_table.html"

    def get_queryset(self):
        self.filter_form = TroughStatusFilterForm(self.request.GET)
        status = None
        if self.filter_form.is_valid():
            status = self.filter_form.cleaned_data["status"] or None
        return trough_rows(status=status)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        return context


class TroughCreateView(LoginRequiredMixin, CreateView):
    model = Trough
    form_class = TroughForm
    template_name = "troughs/form.html"
    success_url = reverse_lazy("trough_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋槽已创建")
        return super().form_valid(form)


class TroughUpdateView(LoginRequiredMixin, UpdateView):
    model = Trough
    form_class = TroughForm
    template_name = "troughs/form.html"
    success_url = reverse_lazy("trough_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋槽已更新")
        return super().form_valid(form)


class TroughDeleteView(LoginRequiredMixin, DeleteView):
    model = Trough
    template_name = "troughs/confirm_delete.html"
    success_url = reverse_lazy("trough_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋槽已删除")
        return super().form_valid(form)


# ---- WitherBatch ----


class BatchListView(HtmxTableMixin, LoginRequiredMixin, ListView):
    model = WitherBatch
    template_name = "batches/list.html"
    context_object_name = "batches"
    partial_template_name = "batches/_table.html"

    def get_queryset(self):
        self.filter_form = BatchGardenFilterForm(self.request.GET)
        return batch_rows(garden_id=self.filter_form.garden_id())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        return context


class BatchCreateView(LoginRequiredMixin, CreateView):
    model = WitherBatch
    form_class = WitherBatchForm
    template_name = "batches/form.html"
    success_url = reverse_lazy("batch_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋批次已创建")
        return super().form_valid(form)


class BatchUpdateView(LoginRequiredMixin, UpdateView):
    model = WitherBatch
    form_class = WitherBatchForm
    template_name = "batches/form.html"
    success_url = reverse_lazy("batch_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋批次已更新")
        return super().form_valid(form)


class BatchDeleteView(LoginRequiredMixin, DeleteView):
    model = WitherBatch
    template_name = "batches/confirm_delete.html"
    success_url = reverse_lazy("batch_list")

    def form_valid(self, form):
        messages.success(self.request, "萎凋批次已删除")
        return super().form_valid(form)
