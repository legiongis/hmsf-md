from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from .models import Scout, ScoutProfile


class ScoutForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    last_name = forms.CharField(
        max_length=30,
        required=True,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    middle_initial = forms.CharField(
        max_length=1,
        required=True,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    zip_code = forms.CharField(
        max_length=5,
        required=True,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    email = forms.EmailField(
        max_length=200,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class':'form-control', 'required':'true'}),
        label="Enter Password")    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class':'form-control', 'required':'true'}),
        label="Re-enter Password")
    class Meta:
        model = Scout
        fields = ('first_name', 'middle_initial', 'last_name', 'zip_code', 'email', 'password1', 'password2')
    
    def clean(self):
        """disallow new accounts with the same e-mail as existing accounts."""
        cleaned_data = super(ScoutForm, self).clean()
        if "email" in cleaned_data:
            if User.objects.filter(email=cleaned_data["email"]).count() > 0:
                self.add_error(
                    "email",
                    forms.ValidationError(
                        mark_safe(_(
                            "This email address has already been registered with the system. \
                            <a href='/password_reset/'>Cilck here</a> to reset your password."
                        )),
                        code="unique",
                    ),
                )


class ScoutProfileForm(forms.ModelForm):
    SITE_INTEREST_CHOICES = (
        ('Prehistoric', 'Prehistoric'),
        ('Historic', 'Historic'),
        ('Cemeteries', 'Cemeteries'),
        ('Underwater', 'Underwater'),
        ('Other', 'Other'),)
    class Meta:
        model = ScoutProfile
        fields = ('street_address', 'city', 'state', 'zip_code', 'phone', 'background', 'relevant_experience', 'interest_reason', 'site_interest_type', 'region_choices')
        widgets = {
            'street_address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'background': forms.Textarea(attrs={'class': 'form-control'}),
            'relevant_experience': forms.Textarea(attrs={'class': 'form-control'}),
            'interest_reason': forms.Textarea(attrs={'class': 'form-control'}),
            'site_interest_type': forms.TextInput(attrs={'class': 'form-control'}),
            'region_choices': forms.CheckboxSelectMultiple(),
        }
