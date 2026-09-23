from datetime import date
from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.db.models import Count, Q, OuterRef, Subquery
from django.db.models.functions import ExtractYear

from pegawai.models import (
    Pegawai, 
    RiwayatKepegawaian, 
    RiwayatJabatan, 
    RiwayatPendidikan,
    RiwayatPangkat
)
from unit_kerja.models import UnitKerja


def get_past_date(today, years):
    """Fungsi pembantu menghitung tanggal X tahun lalu aman dari Leap Year"""
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


def index(request):
    opd_id = request.GET.get('opd', '')
    status_filter = request.GET.get('status', '').strip()
    today = date.today()
    
    # 1. Subquery SK Kepegawaian terbaru (Mendukung tmt_selesai untuk PPPK)
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

    # 4. Subquery Riwayat Pangkat / Golongan Terbaru
    pangkat_terakhir = RiwayatPangkat.objects.filter(
        pegawai=OuterRef('pk')
    ).order_by('-tmt_pangkat', '-created_at')

    # Query Base Pegawai Aktif
    pegawai_qs = Pegawai.objects.filter(
        status_keaktifan__in=['AKTIF', 'PPPK_PW']
    ).annotate(
        jenis_transaksi_terakhir=Subquery(kontrak_terakhir.values('jenis_transaksi')[:1]),
        tmt_sk=Subquery(kontrak_terakhir.values('tmt')[:1]),
        tmt_selesai_terakhir=Subquery(kontrak_terakhir.values('tmt_selesai')[:1]),
        jenis_jabatan_terakhir=Subquery(jabatan_terakhir.values('jabatan__jenis__nama')[:1]),
        unit_kerja_id_terakhir=Subquery(jabatan_terakhir.values('unit_kerja_id')[:1]),
        pendidikan_terakhir_nama=Subquery(pendidikan_terakhir.values('tingkat__nama')[:1]),
        golongan_terakhir=Subquery(pangkat_terakhir.values('pangkat__nama_pangkat')[:1]),
    )

    # Filter OPD (Mendukung Unit Kerja Induk & Sub-Unitnya)
    if opd_id and opd_id.isdigit():
        opd_ids = list(
            UnitKerja.objects.filter(
                Q(id=opd_id) | Q(parent_id=opd_id)
            ).values_list('id', flat=True)
        )
        pegawai_qs = pegawai_qs.filter(unit_kerja_id_terakhir__in=opd_ids)

    # Filter Status Kepegawaian (PNS / PPPK / PPPK_PW)
    if status_filter == 'PNS':
        pegawai_qs = pegawai_qs.filter(
            status_keaktifan='AKTIF'
        ).exclude(jenis_transaksi_terakhir__icontains='PPPK')
    elif status_filter == 'PPPK':
        pegawai_qs = pegawai_qs.filter(
            status_keaktifan='AKTIF', 
            jenis_transaksi_terakhir__icontains='PPPK'
        ).exclude(
            Q(jenis_transaksi_terakhir__icontains='PW') | Q(status_keaktifan='PPPK_PW')
        )
    elif status_filter == 'PPPK_PW':
        pegawai_qs = pegawai_qs.filter(
            Q(status_keaktifan='PPPK_PW') | Q(jenis_transaksi_terakhir__icontains='PW')
        )

    # Total Pegawai Aktif
    total_pegawai = pegawai_qs.distinct().count()

    # STATISTIK UTAMA (CARDS KPI)
    stat_pegawai = pegawai_qs.aggregate(
        total_pns=Count('id', filter=Q(status_keaktifan='AKTIF') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        pns_l=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='L') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        pns_p=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='P') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        
        total_pppk=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_transaksi_terakhir__icontains='PPPK') & ~Q(jenis_transaksi_terakhir__icontains='PW') & ~Q(status_keaktifan='PPPK_PW')),
        pppk_l=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='L', jenis_transaksi_terakhir__icontains='PPPK') & ~Q(jenis_transaksi_terakhir__icontains='PW') & ~Q(status_keaktifan='PPPK_PW')),
        pppk_p=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='P', jenis_transaksi_terakhir__icontains='PPPK') & ~Q(jenis_transaksi_terakhir__icontains='PW') & ~Q(status_keaktifan='PPPK_PW')),
        
        total_pppk_pw=Count('id', filter=Q(status_keaktifan='PPPK_PW') | Q(jenis_transaksi_terakhir__icontains='PW')),
        pppk_pw_l=Count('id', filter=(Q(status_keaktifan='PPPK_PW') | Q(jenis_transaksi_terakhir__icontains='PW')) & Q(jenis_kelamin='L')),
        pppk_pw_p=Count('id', filter=(Q(status_keaktifan='PPPK_PW') | Q(jenis_transaksi_terakhir__icontains='PW')) & Q(jenis_kelamin='P')),
    )

    # STATISTIK KOMPOSISI JABATAN
    stat_jabatan = pegawai_qs.aggregate(
        struktural=Count('id', filter=Q(jenis_jabatan_terakhir__icontains='Struktural')),
        fungsional=Count('id', filter=Q(jenis_jabatan_terakhir__icontains='Fungsional')),
        pelaksana=Count('id', filter=Q(jenis_jabatan_terakhir__icontains='Pelaksana')),
    )

    # STATISTIK RENTANG USIA PEGAWAI
    date_25 = get_past_date(today, 25)
    date_35 = get_past_date(today, 35)
    date_45 = get_past_date(today, 45)
    date_55 = get_past_date(today, 55)

    stat_usia = {
        'u25': pegawai_qs.filter(tanggal_lahir__gt=date_25).count(),
        'u25_34': pegawai_qs.filter(tanggal_lahir__lte=date_25, tanggal_lahir__gt=date_35).count(),
        'u35_44': pegawai_qs.filter(tanggal_lahir__lte=date_35, tanggal_lahir__gt=date_45).count(),
        'u45_54': pegawai_qs.filter(tanggal_lahir__lte=date_45, tanggal_lahir__gt=date_55).count(),
        'u55': pegawai_qs.filter(tanggal_lahir__lte=date_55).count(),
    }

    # PROYEKSI PENSIUN (PNS) & HABIS KONTRAK (PPPK/PW) 5 TAHUN KE DEPAN
    tahun_now = today.year
    list_tahun_proyeksi = list(range(tahun_now, tahun_now + 5))
    chart_pensiun_data = []
    chart_kontrak_data = []
    rekap_proyeksi = []

    # Filter terpisah PNS vs PPPK/PW
    pns_qs = pegawai_qs.filter(status_keaktifan='AKTIF').exclude(jenis_transaksi_terakhir__icontains='PPPK')
    pppk_qs = pegawai_qs.filter(Q(status_keaktifan='PPPK_PW') | Q(jenis_transaksi_terakhir__icontains='PPPK'))

    total_proyeksi_pensiun = 0
    total_proyeksi_kontrak = 0

    for thn in list_tahun_proyeksi:
        # Pensiun PNS: Estimasi BUP 58 Tahun (Tahun Lahir + 58 = Tahun Proyeksi)
        pensiun_cnt = pns_qs.filter(tanggal_lahir__year=thn - 58).count()
        # Habis Kontrak PPPK: Berdasarkan ExtractYear dari tmt_selesai_terakhir
        kontrak_cnt = pppk_qs.filter(tmt_selesai_terakhir__year=thn).count()

        chart_pensiun_data.append(pensiun_cnt)
        chart_kontrak_data.append(kontrak_cnt)

        total_proyeksi_pensiun += pensiun_cnt
        total_proyeksi_kontrak += kontrak_cnt

        rekap_proyeksi.append({
            'tahun': thn,
            'pensiun_pns': pensiun_cnt,
            'habis_kontrak_pppk': kontrak_cnt,
            'total': pensiun_cnt + kontrak_cnt
        })

    # GRAFIK TREN KENAIKAN PNS PER TAHUN
    pns_trend = RiwayatKepegawaian.objects.filter(jenis_transaksi='PNS')
    if opd_id and opd_id.isdigit():
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
        pppk=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_transaksi_terakhir__icontains='PPPK') & ~Q(jenis_transaksi_terakhir__icontains='PW') & ~Q(status_keaktifan='PPPK_PW')),
        pppk_pw=Count('id', filter=Q(status_keaktifan='PPPK_PW') | Q(jenis_transaksi_terakhir__icontains='PW')),
        total=Count('id')
    )

    # REKAPITULASI DETAIL (PENDIDIKAN)
    rekap_pendidikan = pegawai_qs.values('pendidikan_terakhir_nama').annotate(
        pns=Count('id', filter=Q(status_keaktifan='AKTIF') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        pppk=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_transaksi_terakhir__icontains='PPPK') & ~Q(jenis_transaksi_terakhir__icontains='PW') & ~Q(status_keaktifan='PPPK_PW')),
        pppk_pw=Count('id', filter=Q(status_keaktifan='PPPK_PW') | Q(jenis_transaksi_terakhir__icontains='PW')),
        total=Count('id')
    ).order_by('-total')

    # REKAPITULASI DETAIL & CHART (GOLONGAN / PANGKAT)
    rekap_golongan = pegawai_qs.values('golongan_terakhir').annotate(
        pns=Count('id', filter=Q(status_keaktifan='AKTIF') & ~Q(jenis_transaksi_terakhir__icontains='PPPK')),
        pppk=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_transaksi_terakhir__icontains='PPPK') & ~Q(jenis_transaksi_terakhir__icontains='PW') & ~Q(status_keaktifan='PPPK_PW')),
        pppk_pw=Count('id', filter=Q(status_keaktifan='PPPK_PW') | Q(jenis_transaksi_terakhir__icontains='PW')),
        total=Count('id')
    ).order_by('-golongan_terakhir')

    chart_golongan_labels = [item['golongan_terakhir'] or 'Tanpa Golongan' for item in rekap_golongan]
    chart_golongan_data = [item['total'] for item in rekap_golongan]

    # List OPD untuk Dropdown Filter
    list_opd = UnitKerja.objects.filter(
        is_active=True
    ).filter(
        Q(parent__isnull=True) | Q(jenis='UPTD')
    ).order_by('nama')

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
        'rekap_golongan': rekap_golongan,
        'chart_golongan_labels': chart_golongan_labels,
        'chart_golongan_data': chart_golongan_data,
        'list_tahun_proyeksi': list_tahun_proyeksi,
        'chart_pensiun_data': chart_pensiun_data,
        'chart_kontrak_data': chart_kontrak_data,
        'total_proyeksi_pensiun': total_proyeksi_pensiun,
        'total_proyeksi_kontrak': total_proyeksi_kontrak,
        'rekap_proyeksi': rekap_proyeksi,
        'list_opd': list_opd,
        'opd_selected': int(opd_id) if opd_id.isdigit() else '',
        'status_selected': status_filter,
        'today': today,
    }
    return render(request, 'landing/index.html', context)