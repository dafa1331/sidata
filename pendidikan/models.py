from django.db import models

class TingkatPendidikan(models.Model):
    # SD, SMP, SMA, D-III, S1, S2, S3
    kode = models.CharField(max_length=10, unique=True, help_text="Contoh: S1, D3, SMA")
    nama = models.CharField(max_length=50, help_text="Contoh: Sarjana (S-1), Diploma III")
    urutan = models.PositiveIntegerField(default=1, help_text="Urutan hirarki pendidikan (1=SD, 7=S3)")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['urutan']
        verbose_name_plural = "Master Tingkat Pendidikan"

    def __str__(self):
        return f"{self.nama} ({self.kode})"