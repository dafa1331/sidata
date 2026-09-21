from datetime import date
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.db.models import Count, Q, OuterRef, Subquery
from xhtml2pdf import pisa
from dateutil.relativedelta import relativedelta
from django.core.paginator import Paginator

from pegawai.models import Pegawai, RiwayatKepegawaian


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="Laporan_Kepegawaian_OPD.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Gagal membuat dokumen PDF', status=500)
    return response


def get_pegawai_dengan_transaksi_terakhir():
    """Subquery untuk mengambil jenis_transaksi terbaru per pegawai."""
    transaksi_terakhir = RiwayatKepegawaian.objects.filter(
        pegawai=OuterRef('pk')
    ).order_by('-tmt', '-created_at').values('jenis_transaksi')[:1]

    return Pegawai.objects.annotate(
        transaksi_terakhir=Subquery(transaksi_terakhir)
    )


def apply_status_pegawai_filter(pegawai_qs, status_pegawai):
    """Filter pegawai berdasarkan kategori PNS, PPPK, atau PPPK_PW."""
    if status_pegawai == 'PNS':
        return pegawai_qs.filter(
            status_keaktifan='AKTIF',
            transaksi_terakhir__in=['PNS', 'CPNS']
        )
    elif status_pegawai == 'PPPK':
        return pegawai_qs.filter(
            status_keaktifan='AKTIF',
            transaksi_terakhir='PPPK'
        )
    elif status_pegawai == 'PPPK_PW':
        return pegawai_qs.filter(
            Q(status_keaktifan='PPPK_PW') | Q(transaksi_terakhir='PPPK_PW')
        )
    return pegawai_qs.filter(status_keaktifan__in=['AKTIF', 'PPPK_PW'])


def get_statistik_kepegawaian(pegawai_aktif):
    """Helper statistik pegawai yang terbebas dari duplikasi join."""
    today = date.today()

    # 1. REKAP STATUS & GENDER
    stat_pegawai = pegawai_aktif.aggregate(
        total_pns=Count('id', filter=Q(status_keaktifan='AKTIF', transaksi_terakhir__in=['PNS', 'CPNS']), distinct=True),
        pns_l=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='L', transaksi_terakhir__in=['PNS', 'CPNS']), distinct=True),
        pns_p=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='P', transaksi_terakhir__in=['PNS', 'CPNS']), distinct=True),
        
        total_pppk=Count('id', filter=Q(status_keaktifan='AKTIF', transaksi_terakhir='PPPK'), distinct=True),
        pppk_l=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='L', transaksi_terakhir='PPPK'), distinct=True),
        pppk_p=Count('id', filter=Q(status_keaktifan='AKTIF', jenis_kelamin='P', transaksi_terakhir='PPPK'), distinct=True),
        
        total_pppkpw=Count('id', filter=Q(status_keaktifan='PPPK_PW') | Q(transaksi_terakhir='PPPK_PW'), distinct=True),
        pppkpw_l=Count('id', filter=(Q(status_keaktifan='PPPK_PW') | Q(transaksi_terakhir='PPPK_PW')) & Q(jenis_kelamin='L'), distinct=True),
        pppkpw_p=Count('id', filter=(Q(status_keaktifan='PPPK_PW') | Q(transaksi_terakhir='PPPK_PW')) & Q(jenis_kelamin='P'), distinct=True),
    )

    # 2. REKAP JABATAN
    stat_jabatan = pegawai_aktif.aggregate(
        struktural=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__iexact='struktural'), distinct=True),
        fungsional=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__iexact='fungsional'), distinct=True),
        pelaksana=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__iexact='pelaksana'), distinct=True),
    )

    # 3. REKAP RENTANG USIA
    stat_usia = {'u25': 0, 'u25_34': 0, 'u35_44': 0, 'u45_54': 0, 'u55': 0}
    for p in pegawai_aktif:
        if p.tanggal_lahir:
            usia = relativedelta(today, p.tanggal_lahir).years
            if usia < 25:
                stat_usia['u25'] += 1
            elif 25 <= usia <= 34:
                stat_usia['u25_34'] += 1
            elif 35 <= usia <= 44:
                stat_usia['u35_44'] += 1
            elif 45 <= usia <= 54:
                stat_usia['u45_54'] += 1
            else:
                stat_usia['u55'] += 1

    # 4. REKAP GOLONGAN
    rekap_golongan = pegawai_aktif.values('riwayat_pangkat__pangkat__golongan').annotate(
        jumlah=Count('id', distinct=True)
    ).order_by('-riwayat_pangkat__pangkat__golongan')

    # 5. REKAP PENDIDIKAN
    rekap_pendidikan = pegawai_aktif.values('riwayat_pendidikan__tingkat__kode').annotate(
        jumlah=Count('id', distinct=True)
    ).order_by('riwayat_pendidikan__tingkat__urutan')

    return stat_pegawai, stat_jabatan, stat_usia, rekap_golongan, rekap_pendidikan


@login_required
def laporan_kepegawaian_view(request):
    tahun_selected = request.GET.get('tahun', '')
    bulan_selected = request.GET.get('bulan', '')
    jenis_filter = request.GET.get('jenis', '')
    status_pegawai = request.GET.get('status_pegawai', '')

    pegawai_aktif = get_pegawai_dengan_transaksi_terakhir()
    pegawai_aktif = apply_status_pegawai_filter(pegawai_aktif, status_pegawai)

    riwayat_list = RiwayatKepegawaian.objects.filter(pegawai__in=pegawai_aktif).select_related('pegawai').order_by('-tmt')
    
    if tahun_selected:
        riwayat_list = riwayat_list.filter(tmt__year=tahun_selected)
    if bulan_selected:
        riwayat_list = riwayat_list.filter(tmt__month=bulan_selected)
    if jenis_filter:
        riwayat_list = riwayat_list.filter(jenis_transaksi=jenis_filter)

    total_seluruh_pegawai = pegawai_aktif.distinct().count()

    paginator = Paginator(riwayat_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    stat_pegawai, stat_jabatan, stat_usia, rekap_golongan, rekap_pendidikan = get_statistik_kepegawaian(pegawai_aktif)

    tahun_now = date.today().year
    list_tahun = range(tahun_now - 5, tahun_now + 2)

    context = {
        'title': 'Laporan & Statistik Kepegawaian OPD',
        'riwayat_list': page_obj,
        'tahun_selected': tahun_selected,
        'bulan_selected': bulan_selected,
        'jenis_filter': jenis_filter,
        'status_pegawai': status_pegawai,
        'list_tahun': list_tahun,
        'total_seluruh_pegawai': total_seluruh_pegawai,
        'stat_pegawai': stat_pegawai,
        'stat_jabatan': stat_jabatan,
        'stat_usia': stat_usia,
        'rekap_golongan': rekap_golongan,
        'rekap_pendidikan': rekap_pendidikan,
    }
    return render(request, 'pegawai/laporan_index.html', context)


@login_required
def export_laporan_pdf(request):
    tahun_selected = request.GET.get('tahun', '')
    bulan_selected = request.GET.get('bulan', '')
    jenis_filter = request.GET.get('jenis', '')
    status_pegawai = request.GET.get('status_pegawai', '')

    pegawai_aktif = get_pegawai_dengan_transaksi_terakhir()
    pegawai_aktif = apply_status_pegawai_filter(pegawai_aktif, status_pegawai)

    riwayat_list = RiwayatKepegawaian.objects.filter(pegawai__in=pegawai_aktif).select_related('pegawai').order_by('-tmt')
    if tahun_selected: 
        riwayat_list = riwayat_list.filter(tmt__year=tahun_selected)
    if bulan_selected: 
        riwayat_list = riwayat_list.filter(tmt__month=bulan_selected)
    if jenis_filter: 
        riwayat_list = riwayat_list.filter(jenis_transaksi=jenis_filter)

    stat_pegawai, stat_jabatan, stat_usia, rekap_golongan, rekap_pendidikan = get_statistik_kepegawaian(pegawai_aktif)

    nama_bulan_map = {
        '1': 'Januari', '2': 'Februari', '3': 'Maret', '4': 'April',
        '5': 'Mei', '6': 'Juni', '7': 'Juli', '8': 'Agustus',
        '9': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
    }

    status_pegawai_label = {
        'PNS': 'PNS (Pegawai Negeri Sipil)',
        'PPPK': 'PPPK (Pegawai Pemerintah dengan Perjanjian Kerja)',
        'PPPK_PW': 'PPPK Paruh Waktu',
    }.get(status_pegawai, 'Semua Kategori Pegawai (PNS, PPPK, PPPK PW)')

    context = {
        'riwayat_list': riwayat_list,
        'tahun': tahun_selected or 'Semua Tahun',
        'bulan_nama': nama_bulan_map.get(bulan_selected, 'Semua Bulan'),
        'jenis_filter': jenis_filter or 'Semua Transaksi',
        'status_pegawai_label': status_pegawai_label,
        'status_pegawai': status_pegawai,
        'tgl_cetak': date.today().strftime('%d %B %Y'),
        'nama_opd': 'DINAS TUGAS DAN FUNGSI UTAMA',
        'nama_pimpinan': 'Dr. H. NAMA PIMPINAN, M.Si',
        'nip_pimpinan': '19750101 200003 1 001',
        'jabatan_pimpinan': 'Kepala Dinas',
        'total_seluruh_pegawai': pegawai_aktif.distinct().count(),
        'stat_pegawai': stat_pegawai,
        'stat_jabatan': stat_jabatan,
        'stat_usia': stat_usia,
        'rekap_golongan': rekap_golongan,
        'rekap_pendidikan': rekap_pendidikan,
    }

    return render_to_pdf('pegawai/pdf_laporan_dinas.html', context)