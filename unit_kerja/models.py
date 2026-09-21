from django.db import models

class UnitKerja(models.Model):
    # PILIHAN JENIS UNIT KERJA
    JENIS_CHOICES = (
        ('PEMDA', 'PEMERINTAH DAERAH'),
        ('DINAS', 'Dinas'),
        ('BADAN', 'Badan'),
        ('SETDA', 'Sekretariat Daerah'),
        ('SEKRETARIAT', 'Sekretariat Dinas/Badan'),
        ('BAGIAN', 'Bagian'),
        ('SUBBAG', 'Subbagian'),
        ('BIDANG', 'Bidang'),
        ('SUBBID', 'Subbidang'),
        ('UPTD', 'UPTD / UPT'),
        ('KECAMATAN', 'Kecamatan'),
        ('KELURAHAN', 'Kelurahan'),
        ('LAINNYA', 'Lainnya'),
    )

    nama = models.CharField(max_length=150, db_index=True)
    kode = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text="Kode Unit Kerja/Kode SOTK")
    
    # FIELD BARU: JENIS UNIT KERJA (Aman untuk data lama)
    jenis = models.CharField(
        max_length=30, 
        choices=JENIS_CHOICES, 
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Jenis Unit Kerja"
    )

    # Self-referencing FK untuk Struktur Hirarki Parent-Child
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True, 
        related_name='sub_units',
        verbose_name="Induk Unit Kerja"
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['nama']
        verbose_name_plural = "Master Unit Kerja"

    def __str__(self):
        # Menampilkan hirarki parent jika ada (misal: BKPSDM > Sekretariat)
        if self.parent:
            return f"{self.parent} > {self.nama}"
        return self.nama

    def get_full_hierarchy(self):
        """Mengembalikan list urutan dari Induk tertinggi hingga Unit Kerja ini"""
        full_path = [self.nama]
        k = self.parent
        while k is not None:
            full_path.append(k.nama)
            k = k.parent
        # return " > ".join(reversed(full_path))
        return " > ".join(full_path)

    def get_top_parent(self):
        """Mengembalikan objek Induk Tertinggi (Top-Level OPD) jika ada"""
        if not self.parent:
            return None
        k = self.parent
        while k.parent is not None:
            k = k.parent
        return k