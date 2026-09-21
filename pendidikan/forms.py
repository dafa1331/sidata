from django import forms
from .models import TingkatPendidikan

class TingkatPendidikanForm(forms.ModelForm):
    class Meta:
        model = TingkatPendidikan
        fields = ['kode', 'nama', 'urutan', 'is_active']
        widgets = {
            'kode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: S1, D3, SMA'}),
            'nama': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: Sarjana (S-1)'}),
            'urutan': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: 1, 2, 3'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }