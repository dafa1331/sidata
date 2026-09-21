from django.db import models
from pangkat.models import Pangkat

class RiwayatPangkat(models.Model):
    JENIS_KP = [
        ('REGULER', 'Kenaikan Pangkat Reguler'),
        ('JABATAN', 'Kenaikan Pangkat Pilihan / Jabatan'),
        ('PENGABDIAN', 'Kenaikan Pangkat Pengabdian'),
        ('ANUMERTA', 'Kenaikan Pangkat Anumerta'),
        ('IJAZAH', 'Penyesuaian Ijazah'),
        ('AWAL', 'Pengangkatan Awal / CPNS / PPPK'),
    ]

    pegawai = models.ForeignKey(
        'Pegawai', 
        on_delete=models.CASCADE, 
        related_name='riwayat_pangkat'
    )
    pangkat = models.ForeignKey(
        Pangkat, 
        on_delete=models.PROTECT, 
        related_name='riwayat_pegawai',
        verbose_name="Pangkat / Golongan"
    )
    jenis_kp = models.CharField(
        max_length=30, 
        choices=JENIS_KP, 
        default='REGULER',
        verbose_name="Jenis Kenaikan Pangkat"
    )
    
    tmt_pangkat = models.DateField(verbose_name="TMT Pangkat")
    nomor_sk = models.CharField(max_length=100, verbose_name="Nomor SK")
    tanggal_sk = models.DateField(verbose_name="Tanggal SK")
    pejabat_penetap = models.CharField(max_length=150, blank=True, null=True, verbose_name="Pejabat Penetap")
    
    file_sk = models.FileField(upload_to='sk_pangkat/', blank=True, null=True, verbose_name="File SK PDF")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "riwayat_pangkat"
        ordering = ['-tmt_pangkat']

    def __str__(self):
        return f"{self.pegawai.nama_lengkap} - {self.pangkat} ({self.tmt_pangkat})"