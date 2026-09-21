from datetime import date
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.urls import reverse

from pegawai.models import Pegawai, RiwayatJabatan, RiwayatKepegawaian

@login_required
def proyeksi_pensiun_view(request):
    tahun_selected = request.GET.get('tahun')
    bulan_selected = request.GET.get('bulan')
    
    batas_tgl_lahir = date.today() - relativedelta(years=50)
    
    pegawai_aktif = Pegawai.objects.filter(
        status_keaktifan='AKTIF',
        tanggal_lahir__lte=batas_tgl_lahir
    ).prefetch_related(
        Prefetch(
            'riwayat_jabatan',
            queryset=RiwayatJabatan.objects.select_related('jabatan__jenis', 'jabatan__jenjang', 'unit_kerja').order_by('-tmt_jabatan'),
            to_attr='prefetched_jabatan_list'
        )
    )

    proyeksi_list = []
    agregasi_tahun = {}

    for p in pegawai_aktif:
        jabatan_terakhir = p.prefetched_jabatan_list[0] if p.prefetched_jabatan_list else None
        
        usia_bup = 58
        if jabatan_terakhir and jabatan_terakhir.jabatan:
            obj_j = jabatan_terakhir.jabatan
            nama_j = obj_j.nama_jabatan.lower() if obj_j.nama_jabatan else ''
            jenis = (obj_j.jenis.nama if obj_j.jenis else '').lower()
            jenjang = (obj_j.jenjang.nama if obj_j.jenjang else '').lower()
            eselon = (obj_j.eselon if hasattr(obj_j, 'eselon') and obj_j.eselon else '').lower()

            if 'utama' in jenjang or 'eselon i' in jenis or 'i.a' in eselon or 'i.b' in eselon:
                usia_bup = 65
            elif 'guru' in nama_j or 'guru' in jenis or 'madya' in jenjang or 'ii.a' in eselon or 'ii.b' in eselon or 'eselon ii' in jenis:
                usia_bup = 60

        if p.tanggal_lahir:
            ultah_bup = p.tanggal_lahir + relativedelta(years=usia_bup)
            tmt_p = ultah_bup if ultah_bup.day == 1 else (ultah_bup + relativedelta(months=1)).replace(day=1)
        else:
            tmt_p = None

        if tmt_p:
            thn = tmt_p.year
            bln = tmt_p.month
            agregasi_tahun[thn] = agregasi_tahun.get(thn, 0) + 1

            proyeksi_list.append({
                'pegawai': p,
                'tmt_pensiun': tmt_p,
                'tahun': thn,
                'bulan': bln,
                'usia_bup': usia_bup,
                'jabatan': jabatan_terakhir,
                'is_ready': tmt_p <= date.today()
            })

    rekap_tahun = sorted([{'tahun': k, 'jumlah': v} for k, v in agregasi_tahun.items()], key=lambda x: x['tahun'])

    detail_proyeksi = proyeksi_list
    if tahun_selected:
        detail_proyeksi = [x for x in detail_proyeksi if str(x['tahun']) == str(tahun_selected)]
        if bulan_selected:
            detail_proyeksi = [x for x in detail_proyeksi if str(x['bulan']) == str(bulan_selected)]

    detail_proyeksi = sorted(detail_proyeksi, key=lambda x: x['tmt_pensiun'])

    context = {
        'title': 'Proyeksi Pensiun Pegawai',
        'rekap_tahun': rekap_tahun,
        'detail_proyeksi': detail_proyeksi,
        'tahun_selected': tahun_selected,
        'bulan_selected': bulan_selected,
    }
    return render(request, 'pegawai/proyeksi_pensiun.html', context)


@login_required
def eksekusi_pensiun_action(request, pegawai_id):
    if request.method == 'POST':
        pegawai = get_object_or_404(Pegawai, pk=pegawai_id)
        page_number = request.POST.get('page', '1')
        
        nomor_sk = request.POST.get('nomor_sk', '').strip()
        tanggal_sk = request.POST.get('tanggal_sk', '').strip()
        pejabat_penetap = request.POST.get('pejabat_penetap', '').strip()

        redirect_url = f"{reverse('pegawai:proyeksi_pensiun')}?page={page_number}"

        if not nomor_sk or not tanggal_sk:
            messages.error(request, 'Nomor SK dan Tanggal SK wajib diisi!')
            return redirect(redirect_url)

        try:
            with transaction.atomic():
                tmt_pensiun_val = pegawai.tmt_pensiun or date.today()
                
                RiwayatKepegawaian.objects.create(
                    pegawai=pegawai,
                    jenis_transaksi='PENSIUN',
                    tmt=tmt_pensiun_val,
                    nomor_sk=nomor_sk,
                    tanggal_sk=tanggal_sk,
                    keterangan=f"Penetapan Pensiun BUP. Pejabat Penetap: {pejabat_penetap or '-'}"
                )

            messages.success(request, f'Berhasil memproses pensiun untuk {pegawai.nama_dengan_gelar}. Status telah diperbarui menjadi PENSIUN.')
            return redirect(redirect_url)

        except Exception as e:
            messages.error(request, f'Gagal memproses pensiun: {str(e)}')
            return redirect(redirect_url)

    return redirect('pegawai:proyeksi_pensiun')