from django import forms
from .models import Pangkat

class PangkatForm(forms.ModelForm):
    class Meta:
        model = Pangkat
        fields = ['golongan', 'nama_pangkat', 'urutan', 'is_active']
        widgets = {
            'golongan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'misal: III/a'}),
            'nama_pangkat': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'misal: Penata Muda'}),
            'urutan': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'misal: 9'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }