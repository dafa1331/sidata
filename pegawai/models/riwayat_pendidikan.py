from django.db import models
from pendidikan.models import TingkatPendidikan

class RiwayatPendidikan(models.Model):
    pegawai = models.ForeignKey(
        'Pegawai', 
        on_delete=models.CASCADE, 
        related_name='riwayat_pendidikan'
    )
    tingkat = models.ForeignKey(
        TingkatPendidikan, 
        on_delete=models.PROTECT, 
        related_name='riwayat_pegawai',
        verbose_name="Tingkat / Jenjang Pendidikan"
    )
    
    nama_sekolah = models.CharField(max_length=200, verbose_name="Nama Sekolah / Universitas")
    jurusan = models.CharField(max_length=150, blank=True, null=True, verbose_name="Jurusan / Program Studi")
    
    gelar_depan = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Gelar Depan",
        help_text="Contoh: Dr., Drs., Ir."
    )
    gelar_belakang = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Gelar Belakang",
        help_text="Contoh: S.Kom., M.T., Ph.D."
    )

    tampilkan_gelar = models.BooleanField(
        default=True,
        verbose_name="Tampilkan Gelar di Nama Resmi",
        help_text="Centang jika gelar dari riwayat pendidikan ini diizinkan untuk dicantumkan di nama pegawai."
    )

    nomor_ijazah = models.CharField(max_length=100, verbose_name="Nomor Ijazah")
    tanggal_ijazah = models.DateField(verbose_name="Tanggal Ijazah / Lulus")
    tahun_lulus = models.PositiveIntegerField(verbose_name="Tahun Lulus")
    
    is_pendidikan_pertama = models.BooleanField(
        default=False, 
        help_text="Centang jika pendidikan ini digunakan saat pengangkatan awal CPNS/PPPK"
    )
    file_ijazah = models.FileField(upload_to='ijazah/', blank=True, null=True, verbose_name="File Ijazah (PDF)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "riwayat_pendidikan"
        ordering = ['-tingkat__urutan', '-tahun_lulus']

    def __str__(self):
        gelar_info = f" ({self.gelar_belakang})" if self.gelar_belakang else ""
        return f"{self.pegawai.nama_lengkap} - {self.tingkat.kode}{gelar_info} ({self.tahun_lulus})"

    @property
    def nama_lengkap_dengan_gelar(self):
        """Format otomatis nama pegawai dengan gelar dari riwayat pendidikan ini"""
        nama = self.pegawai.nama_lengkap
        if self.gelar_depan:
            nama = f"{self.gelar_depan.strip()} {nama}"
        if self.gelar_belakang:
            nama = f"{nama}, {self.gelar_belakang.strip()}"
        return nama