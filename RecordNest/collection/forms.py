from django import forms
from .models import RecordList

class RecordListForm(forms.ModelForm):
    class Meta:
        model = RecordList
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nombre de la lista'}),
            'description': forms.Textarea(attrs={'placeholder': 'Descripción de la lista'})
        }
