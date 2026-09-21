from django import forms
from .models import Jabatan, JenisJabatan, JenjangJabatan

class JabatanCreateForm(forms.ModelForm):
    jenjang_list = forms.ModelMultipleChoiceField(
        queryset=JenjangJabatan.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Jenjang Jabatan"
    )

    class Meta:
        model = Jabatan
        fields = ['jenis', 'nama_jabatan', 'eselon', 'is_active']
        widgets = {
            'jenis': forms.Select(attrs={'class': 'form-select'}),
            'nama_jabatan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: PENGAWAS PERIKANAN'}),
            'eselon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: III.a'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
# 2. FORM KHUSUS EDIT (DROPDOWN SINGLE JENJANG)
class JabatanUpdateForm(forms.ModelForm):
    class Meta:
        model = Jabatan
        fields = ['jenis', 'nama_jabatan', 'jenjang', 'eselon', 'is_active']
        widgets = {
            'jenis': forms.Select(attrs={'class': 'form-select'}),
            'nama_jabatan': forms.TextInput(attrs={'class': 'form-control'}),
            'jenjang': forms.Select(attrs={'class': 'form-select'}),  # DROPDOWN SINGLE
            'eselon': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ImportJabatanForm(forms.Form):
    file_excel = forms.FileField(
        label="Pilih File Excel / CSV Master Jabatan",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls, .csv'})
    )