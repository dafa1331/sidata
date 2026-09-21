from django.db import models

class Pangkat(models.Model):
    golongan = models.CharField(max_length=10, unique=True, help_text="Contoh: III/a, IV/b")
    nama_pangkat = models.CharField(max_length=100, help_text="Contoh: Penata Muda, Pembina Utama")
    urutan = models.PositiveIntegerField(default=1, help_text="Untuk pengurutan hirarki pangkat (1=I/a, dst)")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['urutan']
        verbose_name_plural = "Master Pangkat"

    def __str__(self):
        return f"{self.nama_pangkat} ({self.golongan})"