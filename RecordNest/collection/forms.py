from django import forms
from .models import RecordList

class RecordListForm(forms.ModelForm):
    class Meta:
        model = RecordList
        fields = ['name', 'description', 'cover_image', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

