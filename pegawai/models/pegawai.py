from django.db import models
from dateutil.relativedelta import relativedelta
from datetime import date

class Pegawai(models.Model):
    JENIS_KELAMIN = [
        ("L", "Laki-laki"),
        ("P", "Perempuan"),
    ]

    AGAMA = [
        ("ISLAM", "Islam"),
        ("KRISTEN", "Kristen"),
        ("KATOLIK", "Katolik"),
        ("HINDU", "Hindu"),
        ("BUDDHA", "Buddha"),
        ("KHONGHUCU", "Khonghucu"),
    ]

    STATUS_KEAKTIFAN = [
        ('AKTIF', 'Aktif'),
        ('PENSIUN', 'Pensiun'),
        ('MUTASI_KELUAR', 'Mutasi Keluar'),
        ('CLTN', 'Cuti Di Luar Tanggungan Negara'),
        ('TUGAS_BELAJAR', 'Tugas Belajar'),
        ('PPPK_PW', 'PPPK Paruh Waktu'),
    ]

    nip = models.CharField(
        max_length=18,
        unique=True,
        db_index=True,
    )

    nama_lengkap = models.CharField(
        max_length=150,
    )

    tempat_lahir = models.CharField(
        max_length=100,
    )

    tanggal_lahir = models.DateField()

    jenis_kelamin = models.CharField(
        max_length=1,
        choices=JENIS_KELAMIN,
    )

    agama = models.CharField(
        max_length=20,
        choices=AGAMA,
        default="ISLAM",
    )

    status_keaktifan = models.CharField(
        max_length=20,
        choices=STATUS_KEAKTIFAN,
        default="AKTIF",
        db_index=True,
    )

    alamat = models.TextField(
        blank=True,
    )

    nomor_hp = models.CharField(
        max_length=20,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.nip} - {self.nama_lengkap}"

    # =======================================================
    # PROPERTI RINGKASAN TERAKHIR
    # =======================================================
    @property
    def jabatan_terakhir(self):
        return self.riwayat_jabatan.select_related('jabatan', 'unit_kerja').order_by('-tmt_jabatan').first()

    @property
    def pangkat_terakhir(self):
        return self.riwayat_pangkat.select_related('pangkat').order_by('-tmt_pangkat').first()

    @property
    def pendidikan_terakhir(self):
        return self.riwayat_pendidikan.select_related('tingkat').order_by('-tingkat__urutan', '-tahun_lulus').first()

    @property
    def nama_dengan_gelar(self):
        """
        Menggabungkan SEMUA gelar depan dan belakang dari 
        riwayat pendidikan yang dicentang tampilkan_gelar=True.
        """
        list_pendidikan = self.riwayat_pendidikan.filter(
            tampilkan_gelar=True
        ).select_related('tingkat').order_by('tingkat__urutan', 'tahun_lulus')

        gelar_depan_list = []
        gelar_belakang_list = []

        for p in list_pendidikan:
            if p.gelar_depan and p.gelar_depan.strip():
                gd = p.gelar_depan.strip()
                if gd not in gelar_depan_list:
                    gelar_depan_list.append(gd)

            if p.gelar_belakang and p.gelar_belakang.strip():
                gb = p.gelar_belakang.strip()
                if gb not in gelar_belakang_list:
                    gelar_belakang_list.append(gb)

        nama = self.nama_lengkap.strip()

        if gelar_depan_list:
            prefix = " ".join(gelar_depan_list)
            nama = f"{prefix} {nama}"

        if gelar_belakang_list:
            suffix = ", ".join(gelar_belakang_list)
            nama = f"{nama}, {suffix}"

        return nama

    # =======================================================
    # PROPERTI KALKULASI PENSIUN / BUP
    # =======================================================
    @property
    def usia_bup(self):
        """Menentukan usia BUP berdasarkan aturan khusus instansi"""
        j_terakhir = self.jabatan_terakhir
        if not j_terakhir or not j_terakhir.jabatan:
            return 58  # Default Pelaksana/Umum

        nama_jabatan = j_terakhir.jabatan.nama_jabatan.lower() if j_terakhir.jabatan.nama_jabatan else ''
        jenis = (j_terakhir.jabatan.jenis.nama if j_terakhir.jabatan.jenis else '').lower()
        jenjang = (j_terakhir.jabatan.jenjang.nama if j_terakhir.jabatan.jenjang else '').lower()
        eselon = (j_terakhir.jabatan.eselon if hasattr(j_terakhir.jabatan, 'eselon') and j_terakhir.jabatan.eselon else '').lower()

        # 1. BUP 65 TAHUN: Fungsional Ahli Utama / Eselon I
        if 'utama' in jenjang or 'eselon i' in jenis or 'i.a' in eselon or 'i.b' in eselon:
            return 65

        # 2. BUP 60 TAHUN: Guru Fungsional, Ahli Madya, & Struktural II.a/II.b
        is_guru = 'guru' in nama_jabatan or 'guru' in jenis
        is_ahli_madya = 'madya' in jenjang
        is_eselon_2 = 'ii.a' in eselon or 'ii.b' in eselon or 'eselon ii' in jenis

        if is_guru or is_ahli_madya or is_eselon_2:
            return 60

        # 3. DEFAULT BUP 58 TAHUN: Pelaksana, Fungsional Pertama, Muda, & Jabatan Lainnya
        return 58

    @property
    def tmt_pensiun(self):
        """Hitung TMT Pensiun: Tanggal 1 Bulan Berikutnya setelah Ultah BUP"""
        if not self.tanggal_lahir:
            return None
        
        ultah_bup = self.tanggal_lahir + relativedelta(years=self.usia_bup)
        
        if ultah_bup.day == 1:
            return ultah_bup
        
        return (ultah_bup + relativedelta(months=1)).replace(day=1)

    @property
    def is_siap_pensiun(self):
        """Penanda apakah pegawai sudah memasuki TMT Pensiun (TMT <= Hari Ini)"""
        if self.tmt_pensiun:
            return self.tmt_pensiun <= date.today() and self.status_keaktifan == 'AKTIF'
        return False

    class Meta:
        db_table = "pegawai"
        ordering = ["nama_lengkap"]