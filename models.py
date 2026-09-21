from django.db import models
# Import Model Master
from unit_kerja.models import UnitKerja
from jabatan.models import Jabatan
from pangkat.models import Pangkat
from pendidikan.models import TingkatPendidikan
from dateutil.relativedelta import relativedelta
from datetime import date

# Create your models here.

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
        Contoh Hasil: Dr. Nama Lengkap, S.Kom., M.M.
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
    # PROPERTI KALKULASI PENSIUN / BUP (DIPINDAHKAN KE PEGAWAI)
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

        # 2. BUP 60 TAHUN: 
        # - Guru Fungsional
        # - Fungsional Ahli Madya
        # - Struktural Eselon II.a dan II.b
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


class RiwayatKepegawaian(models.Model):

    JENIS_TRANSAKSI = [
        ('CPNS', 'Pengangkatan CPNS'),
        ('PNS', 'Pengangkatan PNS'),
        ('PPPK', 'Pengangkatan PPPK'),
        ('PPPK_PW', 'Pengangkatan PPPK Paruh Waktu'),
        ('MUTASI_MASUK', 'Mutasi Masuk'),
        ('MUTASI_KELUAR', 'Mutasi Keluar'),
        ('PENSIUN', 'Pensiun'),
        ('CLTN', 'Cuti Di Luar Tanggungan Negara'),
        ('TUGAS_BELAJAR', 'Tugas Belajar'),
        ('REAKTIF', 'Aktif Kembali'),
    ]

    pegawai = models.ForeignKey(
        Pegawai,
        on_delete=models.CASCADE,
        related_name="riwayat_kepegawaian",
    )

    jenis_transaksi = models.CharField(
        max_length=30,
        choices=JENIS_TRANSAKSI,
    )

    tmt = models.DateField(
        verbose_name="TMT SK",
    )

    nomor_sk = models.CharField(
        max_length=100,
    )

    tanggal_sk = models.DateField()

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

    def __str__(self):
        return f"{self.pegawai.nama_lengkap} - {self.get_jenis_transaksi_display()} ({self.tmt})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        latest = self.pegawai.riwayat_kepegawaian.order_by("-tmt").first()
        if latest:
            mapping_status = {
                "CPNS": "AKTIF",
                "PNS": "AKTIF",
                "PPPK": "AKTIF",
                "PPPK_PW": "PPPK_PW",
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

    class Meta:
        db_table = "riwayat_kepegawaian"
        ordering = ["-tmt"]


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