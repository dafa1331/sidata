from jabatan.models import Jabatan

JENJANG_LIST = [
    'AHLI UTAMA', 'AHLI MADYA', 'AHLI MUDA', 'AHLI PERTAMA',
    'PENYELIA', 'MAHIR', 'TERAMPIL', 'PEMULA'
]

def get_jabatan_from_excel(jabatan_raw, jabatan_map):
    """
    Pintar mencocokkan jabatan dari Excel:
    1. Cek pencocokan langsung (exact match).
    2. Jika ada kata jenjang di belakangnya, cari Jabatan Generik yang memiliki RELASI JENJANG TERSEBUT.
    """
    if not jabatan_raw:
        return None
    
    clean_raw = jabatan_raw.strip().lower()
    
    if clean_raw in jabatan_map:
        return jabatan_map[clean_raw]
    
    raw_upper = jabatan_raw.strip().upper()
    for jnj in JENJANG_LIST:
        if raw_upper.endswith(jnj):
            nama_tanpa_jenjang = raw_upper[:-len(jnj)].strip().lower()
            
            jabatan_spesifik = Jabatan.objects.filter(
                nama_jabatan__iexact=nama_tanpa_jenjang,
                jenjang__nama__iexact=jnj,
                is_active=True
            ).select_related('jenis', 'jenjang').first()

            if jabatan_spesifik:
                return jabatan_spesifik
            
            if nama_tanpa_jenjang in jabatan_map:
                return jabatan_map[nama_tanpa_jenjang]
            break

    return None