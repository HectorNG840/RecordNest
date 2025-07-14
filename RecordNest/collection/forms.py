from django import forms
from .models import RecordList

class RecordListForm(forms.ModelForm):
    class Meta:
        model = RecordList
        fields = ['name', 'description']
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
        }
