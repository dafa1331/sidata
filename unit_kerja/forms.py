from django import forms
from .models import UnitKerja

class UnitKerjaForm(forms.ModelForm):
    class Meta:
        model = UnitKerja
        fields = ['kode', 'nama', 'jenis', 'parent', 'is_active']
        widgets = {
            'kode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'misal: 1.01.01'}),
            'nama': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan nama unit kerja'}),
            'jenis': forms.Select(attrs={'class': 'form-select'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Menampilkan label parent secara lengkap di dropdown agar mudah dipilih
        self.fields['parent'].label_from_instance = lambda obj: obj.get_full_hierarchy()

class ImportUnitKerjaForm(forms.Form):
    file_excel = forms.FileField(
        label="Pilih File Excel / CSV Unit Kerja",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls, .csv'})
    )