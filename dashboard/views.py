from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.core.paginator import Paginator

from pegawai.models import Pegawai
from unit_kerja.models import UnitKerja

@login_required
def dashboard_view(request):
    opd_id = request.GET.get('opd', '').strip()
    
    # 1. AMBIL OPD INDUK SAJA (parent_id IS NULL)
    opd_induk_qs = UnitKerja.objects.filter(parent__isnull=True)
    
    # Base Queryset Pegawai
    pegawai_qs = Pegawai.objects.all()
    
    # 2. JIKA DIPILIH FILTER OPD INDUK:
    # Filter pegawai yang berada di OPD Induk tsb ATAU di sub-unit/bidang bawahannya
    if opd_id:
        pegawai_qs = pegawai_qs.filter(
            Q(riwayat_jabatan__unit_kerja_id=opd_id) | 
            Q(riwayat_jabatan__unit_kerja__parent_id=opd_id)
        ).distinct()

    # KARTU RINGKASAN PEGAWAI
    stat_ringkasan = pegawai_qs.aggregate(
        total_asn=Count('id', distinct=True),
        pns=Count('id', filter=Q(riwayat_kepegawaian__jenis_transaksi__in=['PNS', 'CPNS']), distinct=True),
        pppk=Count('id', filter=Q(riwayat_kepegawaian__jenis_transaksi='PPPK'), distinct=True),
        pppk_pw=Count('id', filter=Q(riwayat_kepegawaian__jenis_transaksi='PPPKPW'), distinct=True),
        total_l=Count('id', filter=Q(jenis_kelamin='L'), distinct=True),
        total_p=Count('id', filter=Q(jenis_kelamin='P'), distinct=True),
    )

    # STATISTIK JABATAN (STRUKTURAL, FUNGSIONAL, PELAKSANA) + L/P
    stat_jabatan = pegawai_qs.aggregate(
        struktural_l=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__icontains='Struktural', jenis_kelamin='L'), distinct=True),
        struktural_p=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__icontains='Struktural', jenis_kelamin='P'), distinct=True),
        fungsional_l=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__icontains='Fungsional', jenis_kelamin='L'), distinct=True),
        fungsional_p=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__icontains='Fungsional', jenis_kelamin='P'), distinct=True),
        pelaksana_l=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__icontains='Pelaksana', jenis_kelamin='L'), distinct=True),
        pelaksana_p=Count('id', filter=Q(riwayat_jabatan__jabatan__jenis__nama__icontains='Pelaksana', jenis_kelamin='P'), distinct=True),
    )

    # STATISTIK GOLONGAN (GOL I - IV)
    stat_golongan = pegawai_qs.aggregate(
        gol_1=Count('id', filter=Q(riwayat_pangkat__pangkat__golongan__startswith='I/'), distinct=True),
        gol_2=Count('id', filter=Q(riwayat_pangkat__pangkat__golongan__startswith='II/'), distinct=True),
        gol_3=Count('id', filter=Q(riwayat_pangkat__pangkat__golongan__startswith='III/'), distinct=True),
        gol_4=Count('id', filter=Q(riwayat_pangkat__pangkat__golongan__startswith='IV/'), distinct=True),
    )

    # 3. TABEL REKAPITULASI HANYA UNTUK OPD INDUK (+ MENGHITUNG PEGAWAI DARI SUB-UNIT)
    opd_list = opd_induk_qs.annotate(
        total_pns=Count(
            'riwayat_pegawai__pegawai', 
            filter=Q(riwayat_pegawai__pegawai__riwayat_kepegawaian__jenis_transaksi__in=['PNS', 'CPNS']), 
            distinct=True
        ) + Count(
            'sub_units__riwayat_pegawai__pegawai', 
            filter=Q(sub_units__riwayat_pegawai__pegawai__riwayat_kepegawaian__jenis_transaksi__in=['PNS', 'CPNS']), 
            distinct=True
        ),
        total_pppk=Count(
            'riwayat_pegawai__pegawai', 
            filter=Q(riwayat_pegawai__pegawai__riwayat_kepegawaian__jenis_transaksi='PPPK'), 
            distinct=True
        ) + Count(
            'sub_units__riwayat_pegawai__pegawai', 
            filter=Q(sub_units__riwayat_pegawai__pegawai__riwayat_kepegawaian__jenis_transaksi='PPPK'), 
            distinct=True
        ),
        total_pppk_pw=Count(
            'riwayat_pegawai__pegawai', 
            filter=Q(riwayat_pegawai__pegawai__riwayat_kepegawaian__jenis_transaksi='PPPKPW'), 
            distinct=True
        ) + Count(
            'sub_units__riwayat_pegawai__pegawai', 
            filter=Q(sub_units__riwayat_pegawai__pegawai__riwayat_kepegawaian__jenis_transaksi='PPPKPW'), 
            distinct=True
        ),
        total_pegawai=Count('riwayat_pegawai__pegawai', distinct=True) + Count('sub_units__riwayat_pegawai__pegawai', distinct=True)
    ).order_by('-total_pegawai')

    if opd_id:
        opd_list = opd_list.filter(id=opd_id)

    paginator = Paginator(opd_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Dropdown Filter hanya menampilkan OPD Induk
    all_opd = opd_induk_qs.order_by('nama')

    context = {
        'stat_ringkasan': stat_ringkasan,
        'stat_jabatan': stat_jabatan,
        'stat_golongan': stat_golongan,
        'page_obj': page_obj,
        'all_opd': all_opd,
        'selected_opd': opd_id,
        'title': 'Dashboard Statistik ASN'
    }
    return render(request, 'dashboard/index.html', context)