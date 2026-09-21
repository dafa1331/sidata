from datetime import date
from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery, Q
from django.core.paginator import Paginator

from pegawai.models import Pegawai, RiwayatKepegawaian


@login_required
def proyeksi_habis_kontrak_view(request):
    mode_filter = request.GET.get('mode', 'rentang') # 'rentang' atau 'periode'
    bulan_proyeksi = request.GET.get('bulan_rentang', '3')
    
    tahun_selected = request.GET.get('tahun', '')
    bulan_selected = request.GET.get('bulan', '')
    status_filter = request.GET.get('status_pegawai', '')
    search_query = request.GET.get('q', '').strip()

    today = date.today()

    # Subquery untuk mengambil detail SK/Kontrak TERAKHIR per pegawai
    kontrak_terakhir = RiwayatKepegawaian.objects.filter(
        pegawai=OuterRef('pk'),
        tmt_selesai__isnull=False
    ).order_by('-tmt', '-created_at')

    # Query Base Pegawai PPPK & PPPK PW Aktif
    pegawai_qs = Pegawai.objects.filter(
        status_keaktifan__in=['AKTIF', 'PPPK_PW']
    ).annotate(
        nomor_sk_terakhir=Subquery(kontrak_terakhir.values('nomor_sk')[:1]),
        tmt_mulai_terakhir=Subquery(kontrak_terakhir.values('tmt')[:1]),
        tmt_selesai_terakhir=Subquery(kontrak_terakhir.values('tmt_selesai')[:1]),
        jenis_transaksi_terakhir=Subquery(kontrak_terakhir.values('jenis_transaksi')[:1]),
    )

    # PERCABANGAN LOGIKA FILTER (Rentang vs Periode Spesifik)
    if mode_filter == 'periode' and (tahun_selected or bulan_selected):
        if tahun_selected:
            pegawai_qs = pegawai_qs.filter(tmt_selesai_terakhir__year=tahun_selected)
        if bulan_selected:
            pegawai_qs = pegawai_qs.filter(tmt_selesai_terakhir__month=bulan_selected)
    else:
        # Default: Filter berdasarkan Rentang Bulan Ke Depan
        bln_int = int(bulan_proyeksi) if bulan_proyeksi.isdigit() else 3
        batas_akhir = today + relativedelta(months=bln_int)
        pegawai_qs = pegawai_qs.filter(
            tmt_selesai_terakhir__gte=today,
            tmt_selesai_terakhir__lte=batas_akhir
        )

    # Filter Kategori Pegawai
    if status_filter == 'PPPK':
        pegawai_qs = pegawai_qs.filter(status_keaktifan='AKTIF')
    elif status_filter == 'PPPK_PW':
        pegawai_qs = pegawai_qs.filter(status_keaktifan='PPPK_PW')

    # Filter Pencarian Nama / NIP
    if search_query:
        pegawai_qs = pegawai_qs.filter(
            Q(nama_lengkap__icontains=search_query) | Q(nip__icontains=search_query)
        )

    pegawai_qs = pegawai_qs.order_by('tmt_selesai_terakhir')

    # Hitung Sisa Hari untuk Setiap Pegawai
    data_proyeksi = []
    for p in pegawai_qs:
        sisa_hari = (p.tmt_selesai_terakhir - today).days if p.tmt_selesai_terakhir else 0
        data_proyeksi.append({
            'pegawai': p,
            'nomor_sk': p.nomor_sk_terakhir,
            'tmt_mulai': p.tmt_mulai_terakhir,
            'tmt_selesai': p.tmt_selesai_terakhir,
            'jenis_transaksi': p.jenis_transaksi_terakhir,
            'sisa_hari': sisa_hari,
        })

    # List Tahun untuk Dropdown Filter (Tahun Ini - 1 s.d. Tahun Ini + 5)
    tahun_now = today.year
    list_tahun = range(tahun_now - 1, tahun_now + 6)

    # Pagination 10 data per halaman
    paginator = Paginator(data_proyeksi, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'Proyeksi PPPK Habis Kontrak',
        'proyeksi_list': page_obj,
        'mode_filter': mode_filter,
        'bulan_proyeksi': bulan_proyeksi,
        'tahun_selected': tahun_selected,
        'bulan_selected': bulan_selected,
        'status_filter': status_filter,
        'search_query': search_query,
        'list_tahun': list_tahun,
        'total_pegawai': len(data_proyeksi),
        'today': today,
    }
    return render(request, 'pegawai/proyeksi_habis_kontrak.html', context)