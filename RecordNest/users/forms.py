from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    name = forms.CharField(max_length=250, label="Nombre completo")
    birthday = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = CustomUser
        fields = ['username', 'name', 'email', 'birthday', 'password1', 'password2']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['name', 'email', 'birthday', 'bio']
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }
