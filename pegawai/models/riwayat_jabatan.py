from django.db import models
from jabatan.models import Jabatan
from unit_kerja.models import UnitKerja

class RiwayatJabatan(models.Model):
    STATUS_PELANTIKAN_CHOICES = [
        ('DILANTIK', 'Definitif / Sudah Dilantik (Jabatan Fungsional/Struktural)'),
        ('BELUM_DILANTIK', 'CPNS / Tugas Pelaksana (Belum Dilantik JF)'),
    ]

    pegawai = models.ForeignKey(
        'Pegawai', 
        on_delete=models.CASCADE, 
        related_name='riwayat_jabatan'
    )
    jabatan = models.ForeignKey(
        Jabatan, 
        on_delete=models.PROTECT, 
        related_name='riwayat_pegawai',
        verbose_name="Jabatan"
    )
    unit_kerja = models.ForeignKey(
        UnitKerja, 
        on_delete=models.PROTECT, 
        related_name='riwayat_pegawai',
        verbose_name="Unit Kerja"
    )
    
    status_pelantikan = models.CharField(
        max_length=20,
        choices=STATUS_PELANTIKAN_CHOICES,
        default='DILANTIK',
        verbose_name="Status Pelantikan / Pengangkatan",
        help_text="Pilih 'CPNS / Tugas Pelaksana' jika CPNS belum diambil sumpah/dilantik ke dalam Jabatan Fungsional."
    )

    tmt_jabatan = models.DateField(verbose_name="TMT Jabatan")
    nomor_sk = models.CharField(max_length=100, verbose_name="Nomor SK")
    tanggal_sk = models.DateField(verbose_name="Tanggal SK")
    pejabat_penetap = models.CharField(max_length=150, blank=True, null=True, verbose_name="Pejabat Penetap")
    
    file_sk = models.FileField(upload_to='sk_jabatan/', blank=True, null=True, verbose_name="File SK PDF")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "riwayat_jabatan"
        ordering = ['-tmt_jabatan']

    def __str__(self):
        status = " (Tugas Pelaksana)" if self.status_pelantikan == 'BELUM_DILANTIK' else ""
        return f"{self.pegawai.nama_lengkap} - {self.jabatan}{status} ({self.tmt_jabatan})"

    @property
    def is_pelaksana_cpns(self):
        return self.status_pelantikan == 'BELUM_DILANTIK'