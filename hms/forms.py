from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from .models import Scout, ScoutProfile
from fpan.models import Region


class ScoutForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    last_name = forms.CharField(
        max_length=30,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    middle_initial = forms.CharField(
        max_length=1,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    email = forms.EmailField(
        max_length=200,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'}))
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class':'form-control', 'required':'true'}),
        help_text='Required',
        label="Enter Password"
    )    
    password2 = forms.CharField(
        help_text='Required',
        widget=forms.PasswordInput(attrs={'class':'form-control', 'required':'true'}),
        label="Re-enter Password"
    )
    region_choices = forms.ModelMultipleChoiceField(
        label="In which regions can you monitor sites?",
        queryset=Region.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        help_text='You can change this preference anytime after signing up, '\
            'but you must you pick at least one region before an archaeological site can be '\
            'assigned to you for monitoring.',
    )
    zip_code = forms.CharField(
        label="Your zip code",
        max_length=5,
        help_text='Required',
        widget=forms.TextInput(attrs={'class':'form-control', 'required':'true'})
    )
    background = forms.CharField(
        label="Please let us know a little about your education and occupation",
        required=False,
        help_text="Optional",
        widget=forms.Textarea(
            attrs={'class': 'form-control','rows': 1, 'cols': 40, 'style': 'height: 3em;'}
        ),
    )
    relevant_experience = forms.CharField(
        label="Please let us know about any relevant experience",
        required=False,
        help_text="Optional",
        widget=forms.Textarea(
            attrs={'class': 'form-control','rows': 1, 'cols': 40, 'style': 'height: 3em;'}
        ),
    )
    interest_reason = forms.CharField(
        label="Why are you interested in becoming a Heritage Monitoring Scout?",
        label_suffix="",
        required=False,
        help_text="Optional",
        widget=forms.Textarea(
            attrs={'class': 'form-control','rows': 1, 'cols': 40, 'style': 'height: 3em;'}
        ),
    )
    SITE_INTEREST_CHOICES = (
        ('Prehistoric', 'Prehistoric'),
        ('Historic', 'Historic'),
        ('Cemeteries', 'Cemeteries'),
        ('Underwater', 'Underwater'),
        ('Other', 'Other'),)

    site_interest_type = forms.MultipleChoiceField(
        required=False,
        choices=SITE_INTEREST_CHOICES,
        help_text="Knowing this helps us decide which sites to assign to you, "\
            "but it is optional and you can change it anytime after signing up.",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-list-multiselect"}),
    )

    class Meta:
        model = Scout
        fields = (
            'first_name', 'middle_initial', 'last_name', 'email', 'password1', 'password2', 
            'region_choices', 'zip_code',
            'background', 'relevant_experience', 'interest_reason', 'site_interest_type',
        )
    
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
