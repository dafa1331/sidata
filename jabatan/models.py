from django.db import models

class JenisJabatan(models.Model):
    # Struktural, Pelaksana, Fungsional
    nama = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nama


class JenjangJabatan(models.Model):
    # Ahli Pertama, Ahli Muda, Terampil, Mahir, dll.
    nama = models.CharField(max_length=50, unique=True)
    tingkat = models.IntegerField(default=1, help_text="Urutan hirarki jenjang")

    class Meta:
        ordering = ['tingkat']

    def __str__(self):
        return self.nama


class Jabatan(models.Model):
    jenis = models.ForeignKey(JenisJabatan, on_delete=models.PROTECT, related_name='daftar_jabatan')
    nama_jabatan = models.CharField(max_length=150, db_index=True)
    jenjang = models.ForeignKey(JenjangJabatan, on_delete=models.SET_NULL, blank=True, null=True)
    eselon = models.CharField(max_length=10, blank=True, null=True, help_text="Khusus Struktural (e.g. II.a, III.a)")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['jenis', 'nama_jabatan']

    def __str__(self):
        if self.jenjang:
            return f"{self.nama_jabatan} {self.jenjang.nama}"
        return self.nama_jabatan