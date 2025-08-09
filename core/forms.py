from allauth.account.forms import LoginForm, SignupForm
from django import forms

from core.models import AutoSubmissionSetting, Profile, Project
from core.utils import DivErrorList


class CustomSignUpForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_class = DivErrorList


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_class = DivErrorList


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()

    class Meta:
        model = Profile
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile.save()
        return profile


class ProjectScanForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["url"]


class AutoSubmissionSettingForm(forms.ModelForm):
    TIMEZONE_CHOICES = [
        ("UTC", "UTC"),
        ("America/New_York", "America/New_York"),
        ("America/Chicago", "America/Chicago"),
        ("America/Denver", "America/Denver"),
        ("America/Los_Angeles", "America/Los_Angeles"),
        ("Europe/London", "Europe/London"),
        ("Europe/Paris", "Europe/Paris"),
        ("Asia/Tokyo", "Asia/Tokyo"),
        ("Asia/Shanghai", "Asia/Shanghai"),
        ("Asia/Kolkata", "Asia/Kolkata"),
        ("Australia/Sydney", "Australia/Sydney"),
    ]
    preferred_timezone = forms.ChoiceField(choices=TIMEZONE_CHOICES, required=False)

    class Meta:
        model = AutoSubmissionSetting
        fields = [
            "endpoint_url",
            "body",
            "header",
            "posts_per_month",
            # "preferred_timezone",
            # "preferred_time",
        ]

    def clean_body(self):
        import json

        data = self.cleaned_data["body"]
        if isinstance(data, dict):
            return data
        try:
            return json.loads(data) if data else {}
        except Exception:
            raise
