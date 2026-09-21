from django import forms
from .models import (
    Pegawai, 
    RiwayatKepegawaian, 
    RiwayatJabatan, 
    RiwayatPangkat, 
    RiwayatPendidikan
)
from jabatan.models import Jabatan
from unit_kerja.models import UnitKerja
from pangkat.models import Pangkat
from pendidikan.models import TingkatPendidikan


class BootstrapFormMixin:
    """Mixin untuk menerapkan class Bootstrap & Select2 secara otomatis."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


# ==========================================
# 1. FORM PEGAWAI (EDIT & CREATE)
# ==========================================

class PegawaiForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Pegawai
        fields = [
            'nip', 'nama_lengkap', 'tempat_lahir', 'tanggal_lahir',
            'jenis_kelamin', 'agama', 'alamat', 'nomor_hp', 'email'
        ]
        widgets = {
            'nip': forms.TextInput(attrs={'placeholder': 'Masukkan NIP'}),
            'nama_lengkap': forms.TextInput(attrs={'placeholder': 'Masukkan Nama Lengkap'}),
            'tempat_lahir': forms.TextInput(attrs={'placeholder': 'Masukkan Tempat Lahir'}),
            'tanggal_lahir': forms.DateInput(attrs={'type': 'date'}),
            'alamat': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Masukkan Alamat'}),
            'nomor_hp': forms.TextInput(attrs={'placeholder': '08xxxxxxxxxx'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
        }


class PegawaiCreateForm(PegawaiForm):
    jenis_transaksi = forms.ChoiceField(
        choices=RiwayatKepegawaian.JENIS_TRANSAKSI,
        label="Jenis SK Pengangkatan Awal"
    )
    tmt_sk = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="TMT SK Pengangkatan Awal"
    )
    nomor_sk = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Masukkan Nomor SK'}),
        label="Nomor SK Pengangkatan Awal"
    )
    tanggal_sk = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Tanggal SK Pengangkatan Awal"
    )
    file_sk = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'accept': '.pdf'}),
        label="Upload Berkas SK (PDF)"
    )


# ==========================================
# 2. FORM RIWAYAT KEPEGAWAIAN
# ==========================================

class RiwayatKepegawaianForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RiwayatKepegawaian
        fields = ['jenis_transaksi', 'tmt', 'nomor_sk', 'tanggal_sk', 'keterangan', 'file_sk']
        widgets = {
            'tmt': forms.DateInput(attrs={'type': 'date'}),
            'tanggal_sk': forms.DateInput(attrs={'type': 'date'}),
            'nomor_sk': forms.TextInput(attrs={'placeholder': 'Masukkan Nomor SK'}),
            'keterangan': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Keterangan opsional'}),
            'file_sk': forms.FileInput(attrs={'accept': '.pdf'}),
        }


# ==========================================
# 3. FORM RIWAYAT INDIVIDU (VIA DETAIL PEGAWAI)
# ==========================================

class RiwayatJabatanForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RiwayatJabatan
        fields = ['jabatan', 'unit_kerja', 'status_pelantikan', 'tmt_jabatan', 'nomor_sk', 'tanggal_sk', 'pejabat_penetap', 'file_sk']
        widgets = {
            'status_pelantikan': forms.Select(attrs={'class': 'form-select'}),
            'jabatan': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_jabatan'}),
            'unit_kerja': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_unit_kerja'}),
            'tmt_jabatan': forms.DateInput(attrs={'type': 'date'}),
            'tanggal_sk': forms.DateInput(attrs={'type': 'date'}),
            'nomor_sk': forms.TextInput(attrs={'placeholder': 'Masukkan Nomor SK'}),
            'pejabat_penetap': forms.TextInput(attrs={'placeholder': 'Contoh: Bupati / Kepala BKPSDM'}),
            'file_sk': forms.FileInput(attrs={'accept': '.pdf'}),
        }

    # METHOD clean() SEJAJAR DENGAN class Meta (4 SPASI)
    def clean(self):
        cleaned_data = super().clean()
        jabatan = cleaned_data.get('jabatan')
        unit_kerja = cleaned_data.get('unit_kerja')

        if jabatan and unit_kerja:
            # Pengecekan Khusus Jabatan Struktural
            if jabatan.jenis and jabatan.jenis.nama.strip().lower() == 'struktural':
                
                # Kunci Pasangan Spesifik: JABATAN GENERIK + UNIT KERJA
                existing_query = RiwayatJabatan.objects.filter(
                    jabatan=jabatan,            # Misal: Kepala Dinas
                    unit_kerja=unit_kerja,      # Misal: Dinas Kesehatan
                    pegawai__status_keaktifan='AKTIF'
                ).select_related('pegawai', 'jabatan', 'unit_kerja')

                # Jika sedang update/edit, kecualikan record milik sendiri
                if self.instance and self.instance.pk:
                    existing_query = existing_query.exclude(pk=self.instance.pk)

                occupied = existing_query.first()
                if occupied:
                    nomor_sk_val = occupied.nomor_sk or '-'
                    tmt_val = occupied.tmt_jabatan.strftime('%Y-%m-%d') if occupied.tmt_jabatan else '-'
                    
                    # Mengirim format khusus ke JS Popup
                    pesan_error = (
                        f"[OCCUPIED]|"
                        f"{occupied.pegawai.nama_lengkap}|"
                        f"{occupied.pegawai.nip}|"
                        f"{jabatan.nama_jabatan}|"
                        f"{unit_kerja.nama}|"
                        f"{nomor_sk_val}|"
                        f"{tmt_val}"
                    )
                    raise forms.ValidationError(pesan_error)

        return cleaned_data

class RiwayatPangkatForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RiwayatPangkat
        fields = ['pangkat', 'jenis_kp', 'tmt_pangkat', 'nomor_sk', 'tanggal_sk', 'pejabat_penetap', 'file_sk']
        widgets = {
            'pangkat': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_pangkat'}),
            'tmt_pangkat': forms.DateInput(attrs={'type': 'date'}),
            'tanggal_sk': forms.DateInput(attrs={'type': 'date'}),
            'nomor_sk': forms.TextInput(attrs={'placeholder': 'Masukkan Nomor SK Pangkat'}),
            'pejabat_penetap': forms.TextInput(attrs={'placeholder': 'Contoh: Kepala BKPSDM / Bupati'}),
            'file_sk': forms.FileInput(attrs={'accept': '.pdf'}),
        }


class RiwayatPendidikanForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RiwayatPendidikan
        fields = [
            'tingkat', 'nama_sekolah', 'jurusan', 
            'gelar_depan', 'gelar_belakang',
            'nomor_ijazah', 'tanggal_ijazah', 'tahun_lulus', 
            'is_pendidikan_pertama', 'file_ijazah'
        ]
        widgets = {
            'tingkat': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_tingkat'}),
            'nama_sekolah': forms.TextInput(attrs={'placeholder': 'Contoh: Universitas Lampung / SMA N 1 Metro'}),
            'jurusan': forms.TextInput(attrs={'placeholder': 'Contoh: Ilmu Hukum / IPA'}),
            'nomor_ijazah': forms.TextInput(attrs={'placeholder': 'Masukkan Nomor Ijazah'}),
            'tanggal_ijazah': forms.DateInput(attrs={'type': 'date'}),
            'tahun_lulus': forms.NumberInput(attrs={'placeholder': 'Contoh: 2020'}),
            'gelar_depan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: Dr., Drs., Ir.'}),
            'gelar_belakang': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: S.Kom., M.T.'}),
            'file_ijazah': forms.FileInput(attrs={'accept': '.pdf'}),
        }


# ==========================================
# 4. FORM ENTRY DARI SUB-MENU SIDEBAR (PILIH PEGAWAI)
# ==========================================

class EntryJabatanForm(RiwayatJabatanForm):
    """Form Input SK Jabatan langsung dari Sidebar (Dilengkapi Pilih Pegawai)"""
    pegawai = forms.ModelChoiceField(
        queryset=Pegawai.objects.filter(status_keaktifan='AKTIF'),
        widget=forms.Select(attrs={'class': 'form-select select2', 'id': 'id_pegawai'}),
        label="Pilih Pegawai (Cari NIP / Nama)"
    )

    class Meta(RiwayatJabatanForm.Meta):
        fields = ['pegawai'] + RiwayatJabatanForm.Meta.fields


class EntryPangkatForm(RiwayatPangkatForm):
    pegawai = forms.ModelChoiceField(
        queryset=Pegawai.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select select2', 'id': 'id_pegawai'}),
        label="Pilih Pegawai (Cari NIP / Nama)"
    )

    class Meta(RiwayatPangkatForm.Meta):
        fields = ['pegawai'] + RiwayatPangkatForm.Meta.fields


class EntryPendidikanForm(RiwayatPendidikanForm):
    pegawai = forms.ModelChoiceField(
        queryset=Pegawai.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select select2', 'id': 'id_pegawai'}),
        label="Pilih Pegawai (Cari NIP / Nama)"
    )

    class Meta(RiwayatPendidikanForm.Meta):
        fields = ['pegawai'] + RiwayatPendidikanForm.Meta.fields


# ==========================================
# 5. FORM IMPORT EXCEL / CSV MASSAL
# ==========================================

class ImportPegawaiForm(BootstrapFormMixin, forms.Form):
    file_excel = forms.FileField(
        label="Pilih File Excel / CSV Data Pegawai",
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls, .csv'})
    )


class ImportSKJabatanMassalForm(BootstrapFormMixin, forms.Form):
    nomor_sk = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'placeholder': 'Contoh: 800.1.3/045/BKPSDM/2026'}),
        label="Nomor SK Pelantikan Massal"
    )
    tanggal_sk = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Tanggal SK"
    )
    tmt_jabatan = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="TMT Jabatan"
    )
    pejabat_penetap = forms.CharField(
        max_length=150, 
        widget=forms.TextInput(attrs={'placeholder': 'Contoh: Bupati Metro'}),
        label="Pejabat Penetap SK"
    )
    file_sk = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'accept': '.pdf'}),
        label="Upload Lampiran File SK PDF (SK Kolektif)"
    )
    file_excel = forms.FileField(
        label="Pilih File Excel / CSV Daftar Pejabat Dilantik",
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls, .csv'})
    )


class ImportRiwayatJabatanForm(BootstrapFormMixin, forms.Form):
    file_excel = forms.FileField(
        label="Pilih File Excel / CSV Data Riwayat Jabatan Existing",
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls, .csv'})
    )


class ImportRiwayatPangkatForm(BootstrapFormMixin, forms.Form):
    file_excel = forms.FileField(
        label="Pilih File Excel / CSV Data Riwayat Pangkat",
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls, .csv'})
    )


class ImportRiwayatPendidikanForm(BootstrapFormMixin, forms.Form):
    file_excel = forms.FileField(
        label="Pilih File Excel / CSV Data Riwayat Pendidikan",
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls, .csv'})
    )