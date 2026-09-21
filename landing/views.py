from datetime import date
from django.shortcuts import render
from django.db.models import Count, Q, OuterRef, Subquery
from django.db.models.functions import ExtractYear

from pegawai.models import (
    Pegawai, 
    RiwayatKepegawaian, 
    RiwayatJabatan, 
    RiwayatPendidikan
)
from unit_kerja.models import UnitKerja


def index(request):
    opd_id = request.GET.get('opd', '')
    
    # 1. Subquery SK Kepegawaian terbaru
    kontrak_terakhir = RiwayatKepegawaian.objects.filter(
        pegawai=OuterRef('pk')
    ).order_by('-tmt', '-created_at')

    # 2. Subquery Riwayat Jabatan & Unit Kerja (OPD) terbaru
    jabatan_terakhir = RiwayatJabatan.objects.filter(
        pegawai=OuterRef('pk')
    ).order_by('-tmt_jabatan', '-created_at')

    # 3. Subquery Pendidikan Terakhir
    pendidikan_terakhir = RiwayatPendidikan.objects.filter(
        pegawai=OuterRef('pk')
    ).order_by('-tahun_lulus', '-id')

    # Query Base Pegawai Aktif
    pegawai_qs = Pegawai.objects.filter(
        status_keaktifan__in=['AKTIF', 'PPPK_PW']
    ).annotate(
        jenis_transaksi_terakhir=Subquery(kontrak_terakhir.values('jenis_transaksi')[:1]),
        tmt_sk=Subquery(kontrak_terakhir.values('tmt')[:1]),
        jenis_jabatan_terakhir=Subquery(jabatan_terakhir.values('jabatan__jenis__nama')[:1]),
        unit_kerja_id_terakhir=Subquery(jabatan_terakhir.values('unit_kerja_id')[:1]),
        pendidikan_terakhir_nama=Subquery(pendidikan_terakhir.values('tingkat__nama')[:1]),
    )

    # Filter OPD (Mendukung Unit Kerja Induk & Sub-Unitnya)
    if opd_id and opd_id.isdigit():
        # Ambil ID unit kerja yang dipilih beserta ID anak-anaknya (parent = opd_id)
        opd_ids = list(
            UnitKerja.objects.filter(
                Q(id=opd_id) | Q(parent_id=opd_id)
            ).values_list('id', flat=True)
        )
        pegawai_qs = pegawai_qs.filter(unit_kerja_id_terakhir__in=opd_ids)

    # Total Pegawai Aktif
    total_pegawai = pegawai_qs.distinct().count()

    # STATISTIK UTAMA (CARDS)
    stat_pegawai = pegawai_qs.aggregate(
        total_pns=Count('id', filter=Q(status_keaktifan='AKTIF') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        pns_l=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='L') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        pns_p=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='P') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        
        total_pppk=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_transaksi_terakhir__icontains='PPPK')),
        pppk_l=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='L', jenis_transaksi_terakhir__icontains='PPPK')),
        pppk_p=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='P', jenis_transaksi_terakhir__icontains='PPPK')),
        
        total_pppkpw=Count('id', filter=Q(status_keaktifan='PPPK_PW')),
        pppkpw_l=Count('id', filter=Q(status_keaktifan='PPPK_PW', jenis_kelamin='L')),
        pppkpw_p=Count('id', filter=Q(status_keaktifan='PPPK_PW', jenis_kelamin='P')),
    )

    # STATISTIK JABATAN
    stat_jabatan = pegawai_qs.aggregate(
        struktural=Count('id', filter=Q(jenis_jabatan_terakhir__icontains='Struktural')),
        fungsional=Count('id', filter=Q(jenis_jabatan_terakhir__icontains='Fungsional')),
        pelaksana=Count('id', filter=Q(jenis_jabatan_terakhir__icontains='Pelaksana')),
    )

    # STATISTIK RENTANG USIA
    today = date.today()
    stat_usia = {
        'u25': pegawai_qs.filter(tanggal_lahir__gt=today.replace(year=today.year - 25)).count(),
        'u25_34': pegawai_qs.filter(
            tanggal_lahir__lte=today.replace(year=today.year - 25),
            tanggal_lahir__gt=today.replace(year=today.year - 35)
        ).count(),
        'u35_44': pegawai_qs.filter(
            tanggal_lahir__lte=today.replace(year=today.year - 35),
            tanggal_lahir__gt=today.replace(year=today.year - 45)
        ).count(),
        'u45_54': pegawai_qs.filter(
            tanggal_lahir__lte=today.replace(year=today.year - 45),
            tanggal_lahir__gt=today.replace(year=today.year - 55)
        ).count(),
        'u55': pegawai_qs.filter(tanggal_lahir__lte=today.replace(year=today.year - 55)).count(),
    }

    # GRAFIK TREN KENAIKAN PNS PER TAHUN
    pns_trend = RiwayatKepegawaian.objects.filter(jenis_transaksi='PNS')
    if opd_id and opd_id.isdigit():
        opd_ids = list(
            UnitKerja.objects.filter(
                Q(id=opd_id) | Q(parent_id=opd_id)
            ).values_list('id', flat=True)
        )
        pns_trend = pns_trend.filter(
            pegawai__riwayat_jabatan__unit_kerja_id__in=opd_ids
        ).distinct()

    pns_per_tahun = pns_trend.annotate(
        tahun=ExtractYear('tmt')
    ).values('tahun').annotate(
        jumlah=Count('id')
    ).order_by('tahun')

    chart_tahun = [item['tahun'] for item in pns_per_tahun if item['tahun']]
    chart_pns_count = [item['jumlah'] for item in pns_per_tahun if item['tahun']]

    # REKAPITULASI DETAIL (AGAMA)
    rekap_agama = pegawai_qs.values('agama').annotate(
        pns=Count('id', filter=Q(status_keaktifan='AKTIF') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        pppk=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_transaksi_terakhir__icontains='PPPK')),
        pppk_pw=Count('id', filter=Q(status_keaktifan='PPPK_PW')),
        total=Count('id')
    )

    # REKAPITULASI DETAIL (PENDIDIKAN)
    rekap_pendidikan = pegawai_qs.values('pendidikan_terakhir_nama').annotate(
        pns=Count('id', filter=Q(status_keaktifan='AKTIF') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        pppk=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_transaksi_terakhir__icontains='PPPK')),
        pppk_pw=Count('id', filter=Q(status_keaktifan='PPPK_PW')),
        total=Count('id')
    ).order_by('-total')

    # List OPD untuk Dropdown Filter
    list_opd = UnitKerja.objects.filter(is_active=True).order_by('nama')

    context = {
        'title': 'Portal Data & Statistik Kepegawaian',
        'total_pegawai': total_pegawai,
        'stat_pegawai': stat_pegawai,
        'stat_jabatan': stat_jabatan,
        'stat_usia': stat_usia,
        'chart_tahun': chart_tahun,
        'chart_pns_count': chart_pns_count,
        'rekap_agama': rekap_agama,
        'rekap_pendidikan': rekap_pendidikan,
        'list_opd': list_opd,
        'opd_selected': int(opd_id) if opd_id.isdigit() else '',
        'today': today,
    }
    return render(request, 'landing/index.html', context)