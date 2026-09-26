"""视图。

对账约定（与 README「首页四项对账」一致）：首页展示的四项总数必须能分别用
对应列表在「无额外手工条件」下数出的行数复算：

- 茶园总数 = 茶园列表无筛行数            -> garden_list_queryset().count()
- 槽总数   = 槽列表无筛行数              -> trough_list_queryset().count()
- 批次总数 = 批次列表无筛行数            -> batch_list_queryset().count()
- 可下槽数 = 槽列表 ?status=ready 行数   -> trough_list_queryset().filter(status="ready").count()

因此首页与列表共用下面三个 ``*_list_queryset()`` 函数，筛选只在其返回的
queryset 上追加条件，绝不另写 SQL/另定口径。HTMX 局部请求与整页请求都经过
同一个 ``get_queryset()``，同参数下行集合必然相同。
"""

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

from .forms import GardenForm, TroughForm, WitherBatchForm
from .models import Garden, Trough, WitherBatch


def _wants_htmx(request):
    return request.headers.get("HX-Request") == "true"


# ---- 首页与列表共用的全量 queryset（对账的唯一口径） ----


def garden_list_queryset():
    """茶园列表无筛全量；首页「茶园总数」即其行数。"""
    return Garden.objects.all()


def trough_list_queryset():
    """槽列表无筛全量；首页「槽总数」即其行数，「可下槽数」即其 ready 子集行数。"""
    return Trough.objects.select_related("garden").all()


def batch_list_queryset():
    """批次列表无筛全量；首页「批次总数」即其行数。"""
    return WitherBatch.objects.select_related("trough", "trough__garden").all()


@login_required
def home(request):
    troughs = trough_list_queryset()
    context = {
        "garden_count": garden_list_queryset().count(),
        "trough_count": troughs.count(),
        "batch_count": batch_list_queryset().count(),
        # 可下槽数 = 槽列表 status=ready 子集行数（状态筛提供该子集）
        "ready_count": troughs.filter(status=Trough.STATUS_READY).count(),
        "withering_count": troughs.filter(
            status=Trough.STATUS_WITHERING
        ).count(),
        "loading_count": troughs.filter(status=Trough.STATUS_LOADING).count(),
    }
    return render(request, "home.html", context)


# ---- Garden ----


class GardenListView(LoginRequiredMixin, ListView):
    model = Garden
    template_name = "gardens/list.html"
    context_object_name = "gardens"

    def get_queryset(self):
        return garden_list_queryset()

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        if _wants_htmx(request):
            html = render_to_string(
                "gardens/_table.html",
                {"gardens": self.object_list},
                request=request,
            )
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)


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


class TroughListView(LoginRequiredMixin, ListView):
    model = Trough
    template_name = "troughs/list.html"
    context_object_name = "troughs"

    #: 合法状态白名单；其它/缺失参数一律视为无筛全量
    STATUS_VALUES = {value for value, _label in Trough.STATUS_CHOICES}

    def get_queryset(self):
        qs = trough_list_queryset()
        self.status_filter = self.request.GET.get("status", "")
        if self.status_filter in self.STATUS_VALUES:
            qs = qs.filter(status=self.status_filter)
        else:
            # 非法或空值不参与过滤，保证对账时永远能回到无筛全量
            self.status_filter = ""
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.status_filter
        context["status_choices"] = Trough.STATUS_CHOICES
        return context

    def get(self, request, *args, **kwargs):
        # HTMX 与整页都取同一个 get_queryset()，仅渲染外壳与否不同，行集合一致
        self.object_list = self.get_queryset()
        if _wants_htmx(request):
            html = render_to_string(
                "troughs/_table.html",
                {"troughs": self.object_list},
                request=request,
            )
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)


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


class BatchListView(LoginRequiredMixin, ListView):
    model = WitherBatch
    template_name = "batches/list.html"
    context_object_name = "batches"

    def get_queryset(self):
        qs = batch_list_queryset()
        garden_id = self.request.GET.get("garden", "")
        # 仅接受真实存在的茶园主键；其它/缺失参数一律视为无筛全量
        if garden_id.isdigit() and Garden.objects.filter(pk=int(garden_id)).exists():
            self.garden_filter = garden_id
            qs = qs.filter(trough__garden_id=int(garden_id))
        else:
            self.garden_filter = ""
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["garden_filter"] = self.garden_filter
        context["gardens"] = garden_list_queryset()
        return context

    def get(self, request, *args, **kwargs):
        # HTMX 与整页都取同一个 get_queryset()，仅渲染外壳与否不同，行集合一致
        self.object_list = self.get_queryset()
        if _wants_htmx(request):
            html = render_to_string(
                "batches/_table.html",
                {"batches": self.object_list},
                request=request,
            )
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)


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
