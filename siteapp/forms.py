from django import forms
from django.forms import ModelForm

from .models import Portfolio, Project
from itsystems.models import SystemInstance
from itsystems.models import HostInstance

class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ['portfolio']
        portfolio = forms.ChoiceField(choices = [])

        user1 = forms.ChoiceField(choices = [])

    def __init__(self, user, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.fields['portfolio'].choices = [(x.pk, x.title) for x in Portfolio.get_all_readable_by(user).order_by('title')]

class PortfolioForm(ModelForm):

    class Meta:
        model = Portfolio
        fields = ['title', 'description']
        

class SystemInstanceForm(ModelForm):

    class Meta:
        model = SystemInstance
        fields = ['name', 'sdlc_stage']
        labels = {
            'name': ('Name'),
            'sdlc_stage': ('Software Development Life Cycle (SDLC) Stage'),
        }

class HostInstanceForm(ModelForm):

    class Meta:
        model = HostInstance
        fields = ['name', 'host_type', 'os', 'system_instance']
        labels = {
            'name': ('Name'),
            'host_type': ('Host Type'),
            'os': ('Operating System'),
            'system_instance': ('System Instance'),
        }


class PortfolioSignupForm(ModelForm):

    class Meta:
        model = Portfolio
        fields = ['title']

        labels = {
            "title": "Your personal portfolio will be:",
        }
        help_texts = {
            "title": "Only lowercase letters, digits, and dashes.",
        }
        widgets = {
            "description": forms.HiddenInput(),
            "title": forms.TextInput(attrs={"placeholder": "username"})
        }