from django import forms
from .models import RecordList

class RecordListForm(forms.ModelForm):
    class Meta:
        model = RecordList
        fields = ['name', 'description', 'cover_image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre de la lista'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Descripción de la lista',
                'rows': 4
            }),
            'cover_image': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }
