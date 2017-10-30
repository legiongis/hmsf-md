from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from fpan.models.scout import Scout

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    middle_initial = forms.CharField(max_length=2, required=True, help_text='Required')
    class Meta:
        model = User
        fields = ('first_name', 'middle_initial', 'last_name', 'email', 'password')

class ScoutProfileForm(forms.ModelForm):
    class Meta:
        model = Scout
        fields = ('street_address', 'city', 'state', 'zip_code', 'phone', 'background', 'relevant_experience', 'interest_reason', 'site_interest_type', 'region_choices', 'ethics_agreement')

class ScoutSignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='Required')
    last_name = forms.CharField(max_length=30, required=True, help_text='Required')
    middle_initial = forms.CharField(max_length=2, required=True, help_text='Required')
    email = forms.EmailField(max_length=200, help_text='Required')
    class Meta:
        model = User
        fields = ('first_name', 'middle_initial', 'last_name', 'email', 'password1', 'password2')
