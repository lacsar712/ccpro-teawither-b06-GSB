from django import forms

from .models import Garden, Trough, WitherBatch


class GardenForm(forms.ModelForm):
    class Meta:
        model = Garden
        fields = ["name", "altitudeBand", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "altitudeBand": forms.TextInput(attrs={"class": "input"}),
            "notes": forms.Textarea(attrs={"class": "input", "rows": 3}),
        }


class TroughForm(forms.ModelForm):
    class Meta:
        model = Trough
        fields = ["garden", "troughCode", "cultivar", "loadKg", "status"]
        widgets = {
            "garden": forms.Select(attrs={"class": "input"}),
            "troughCode": forms.TextInput(attrs={"class": "input"}),
            "cultivar": forms.TextInput(attrs={"class": "input"}),
            "loadKg": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "status": forms.Select(attrs={"class": "input"}),
        }


class TroughStatusFilterForm(forms.Form):
    """萎凋槽列表按状态筛选；空值/ALL = 无筛全量。"""

    STATUS_ALL = ""
    status = forms.ChoiceField(
        label="状态",
        required=False,
        choices=(
            (STATUS_ALL, "全部状态"),
            (Trough.STATUS_LOADING, "装叶中"),
            (Trough.STATUS_WITHERING, "萎凋中"),
            (Trough.STATUS_READY, "可下槽"),
        ),
        widget=forms.Select(attrs={"class": "input filter-input"}),
    )

    def clean_status(self):
        # 非法值一律回落为“全部”，避免非法筛选条件静默改变行集。
        status = self.cleaned_data.get("status") or self.STATUS_ALL
        valid = {Trough.STATUS_LOADING, Trough.STATUS_WITHERING, Trough.STATUS_READY}
        if status not in valid:
            return self.STATUS_ALL
        return status


class BatchGardenFilterForm(forms.Form):
    """萎凋批次列表按茶园筛选；空值/ALL = 无筛全量。"""

    GARDEN_ALL = ""
    garden = forms.ModelChoiceField(
        label="茶园",
        required=False,
        queryset=Garden.objects.all(),
        empty_label="全部茶园",
        widget=forms.Select(attrs={"class": "input filter-input"}),
    )

    def garden_id(self):
        if not self.is_valid():
            return None
        garden = self.cleaned_data.get("garden")
        return garden.pk if garden else None


class WitherBatchForm(forms.ModelForm):
    class Meta:
        model = WitherBatch
        fields = [
            "trough",
            "startedAt",
            "targetMoisture",
            "actualMoisture",
            "rollGrade",
        ]
        widgets = {
            "trough": forms.Select(attrs={"class": "input"}),
            "startedAt": forms.DateTimeInput(
                attrs={"class": "input", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "targetMoisture": forms.NumberInput(
                attrs={"class": "input", "step": "0.01"}
            ),
            "actualMoisture": forms.NumberInput(
                attrs={"class": "input", "step": "0.01"}
            ),
            "rollGrade": forms.TextInput(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["startedAt"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ]
        if self.instance and self.instance.pk and self.instance.startedAt:
            from django.utils import timezone

            local = timezone.localtime(self.instance.startedAt)
            self.initial["startedAt"] = local.strftime("%Y-%m-%dT%H:%M")
