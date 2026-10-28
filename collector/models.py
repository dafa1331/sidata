import os
from django.db import models
from pegawai.models import Pegawai  # Impor model pegawai yang sudah ada di project Anda
from django.utils import timezone

class JenisDokumen(models.Model):
    nama_dokumen = models.CharField("Nama Dokumen Requirement", max_length=100)
    wajib = models.BooleanField(default=True)

    def __str__(self):
        return self.nama_dokumen


def upload_path_handler(instance, filename):
    """
    Menentukan direktori dan nama file upload berdasarkan:
    media/uploads/<NIP>/<tahun>/<nama_jenis_dokumen>.<ext>
    """
    pegawai = instance.pegawai
    nip = str(pegawai.nip).strip() if pegawai and pegawai.nip else "tanpa_nip"
    tahun = str(timezone.now().year)
    
    # Ambil ekstensi file asli (misal: pdf)
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    
    # Ambil nama jenis dokumen, lalu bersihkan dari karakter spasi/simbol agar aman untuk sistem file
    if instance.jenis_dokumen and instance.jenis_dokumen.nama_dokumen:
        nama_dok = instance.jenis_dokumen.nama_dokumen
    else:
        nama_dok = "dokumen"
        
    safe_nama_dok = "".join([c if c.isalnum() else "_" for c in nama_dok]).strip("_")
    
    # Gabungkan menjadi nama file baru (Contoh: SK_Pengangkatan.pdf)
    new_filename = f"{safe_nama_dok}.{ext}"
    
    # Format folder: uploads/NIP/Tahun/Nama_Dokumen.pdf
    return os.path.join('uploads', nip, tahun, new_filename)


class BerkasPPPK(models.Model):
    # Menghubungkan langsung ke tabel Pegawai yang sudah ada
    pegawai = models.ForeignKey(Pegawai, on_delete=models.CASCADE, related_name='berkas_pppk')
    jenis_dokumen = models.ForeignKey(JenisDokumen, on_delete=models.CASCADE)
    file = models.FileField(upload_to=upload_path_handler)
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('pegawai', 'jenis_dokumen')

    def __str__(self):
        return f"{self.pegawai.nip} - {self.jenis_dokumen.nama_dokumen}"