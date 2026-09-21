from django.db import models
from datetime import date

class RiwayatKepegawaian(models.Model):
    JENIS_TRANSAKSI = [
        ('CPNS', 'Pengangkatan CPNS'),
        ('PNS', 'Pengangkatan PNS'),
        ('PPPK', 'Pengangkatan PPPK Awal'),
        ('PERPANJANGAN_PPPK', 'Perpanjangan Kontrak PPPK'),
        ('PPPK_PW', 'Pengangkatan PPPK Paruh Waktu'),
        ('PERPANJANGAN_PPPK_PW', 'Perpanjangan Kontrak PPPK Paruh Waktu'),
        ('MUTASI_MASUK', 'Mutasi Masuk'),
        ('MUTASI_KELUAR', 'Mutasi Keluar'),
        ('PENSIUN', 'Pensiun / Putus Kontrak'),
        ('CLTN', 'Cuti Di Luar Tanggungan Negara'),
        ('TUGAS_BELAJAR', 'Tugas Belajar'),
        ('REAKTIF', 'Aktif Kembali'),
    ]

    pegawai = models.ForeignKey(
        'Pegawai',
        on_delete=models.CASCADE,
        related_name="riwayat_kepegawaian",
    )

    jenis_transaksi = models.CharField(
        max_length=30,
        choices=JENIS_TRANSAKSI,
    )

    tmt = models.DateField(
        verbose_name="TMT SK / Mulai Kontrak",
    )

    tmt_selesai = models.DateField(
        blank=True,
        null=True,
        verbose_name="TMT Selesai / Akhir Kontrak",
        help_text="Diisi khusus untuk PPPK / PPPK Paruh Waktu"
    )

    nomor_sk = models.CharField(
        max_length=100,
        verbose_name="Nomor SK / Perjanjian Kerja"
    )

    tanggal_sk = models.DateField(
        verbose_name="Tanggal SK / Perjanjian Kerja"
    )

    keterangan = models.TextField(
        blank=True,
        null=True,
    )

    file_sk = models.FileField(
        upload_to="sk_kepegawaian/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "riwayat_kepegawaian"
        ordering = ["-tmt"]

    def __str__(self):
        return f"{self.pegawai.nama_lengkap} - {self.get_jenis_transaksi_display()} ({self.tmt})"

    @property
    def sisa_hari_kontrak(self):
        """Menghitung sisa hari masa berlaku kontrak PPPK"""
        if self.tmt_selesai:
            delta = self.tmt_selesai - date.today()
            return delta.days
        return None

    @property
    def is_kontrak_aktif(self):
        """Mengecek apakah kontrak saat ini sedang berjalan"""
        if self.tmt_selesai:
            return self.tmt <= date.today() <= self.tmt_selesai
        return True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        latest = self.pegawai.riwayat_kepegawaian.order_by("-tmt").first()
        if latest:
            mapping_status = {
                "CPNS": "AKTIF",
                "PNS": "AKTIF",
                "PPPK": "AKTIF",
                "PERPANJANGAN_PPPK": "AKTIF",
                "PPPK_PW": "PPPK_PW",
                "PERPANJANGAN_PPPK_PW": "PPPK_PW",
                "MUTASI_MASUK": "AKTIF",
                "REAKTIF": "AKTIF",
                "MUTASI_KELUAR": "MUTASI_KELUAR",
                "PENSIUN": "PENSIUN",
                "CLTN": "CLTN",
                "TUGAS_BELAJAR": "TUGAS_BELAJAR",
            }
            new_status = mapping_status.get(latest.jenis_transaksi, "AKTIF")
            if self.pegawai.status_keaktifan != new_status:
                self.pegawai.status_keaktifan = new_status
                self.pegawai.save(update_fields=["status_keaktifan"])