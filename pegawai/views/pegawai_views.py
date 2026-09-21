import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Min
from django.core.paginator import Paginator

from jabatan.models import Jabatan
from pegawai.models import Pegawai, RiwayatKepegawaian
from pegawai.forms import PegawaiCreateForm, PegawaiForm, ImportPegawaiForm

@login_required
def pegawai_list(request):
    query = request.GET.get('q', '').strip()
    jk_filter = request.GET.get('jk', '').strip()
    status_filter = request.GET.get('status', '').strip()
    jabatan_filter = request.GET.get('jabatan', '').strip()
    
    pegawai = Pegawai.objects.prefetch_related(
        'riwayat_jabatan__jabatan__jenis',
        'riwayat_jabatan__jabatan__jenjang',
        'riwayat_jabatan__unit_kerja',
        'riwayat_pangkat__pangkat',
        'riwayat_pendidikan__tingkat'
    ).all().order_by('-created_at')

    if query:
        pegawai = pegawai.filter(
            Q(nip__icontains=query) | 
            Q(nama_lengkap__icontains=query) |
            Q(email__icontains=query)
        )
    if jk_filter in ['L', 'P']:
        pegawai = pegawai.filter(jenis_kelamin=jk_filter)
    if status_filter:
        pegawai = pegawai.filter(status_keaktifan=status_filter)
        
    if jabatan_filter == 'BELUM_ADA':
        pegawai = pegawai.filter(riwayat_jabatan__isnull=True)
    elif jabatan_filter:
        if jabatan_filter.isdigit():
            pegawai = pegawai.filter(riwayat_jabatan__jabatan_id=int(jabatan_filter)).distinct()
        else:
            pegawai = pegawai.filter(riwayat_jabatan__jabatan__nama_jabatan__iexact=jabatan_filter).distinct()

    jabatan_list = Jabatan.objects.filter(is_active=True).values(
        'nama_jabatan',
        'jenjang__nama'
    ).annotate(
        id_terwakili=Min('id')
    ).order_by('nama_jabatan', 'jenjang__nama')

    paginator = Paginator(pegawai, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pegawai/index.html', {
        'pegawai_list': page_obj,
        'jabatan_list': jabatan_list,
        'query': query,
        'jk_filter': jk_filter,
        'status_filter': status_filter,
        'jabatan_filter': jabatan_filter,
    })


@login_required
def pegawai_create(request):
    if request.method == 'POST':
        form = PegawaiCreateForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                pegawai = form.save(commit=False)
                pegawai.status_keaktifan = 'AKTIF'
                pegawai.save()

                RiwayatKepegawaian.objects.create(
                    pegawai=pegawai,
                    jenis_transaksi=form.cleaned_data['jenis_transaksi'],
                    tmt=form.cleaned_data['tmt_sk'],
                    nomor_sk=form.cleaned_data['nomor_sk'],
                    tanggal_sk=form.cleaned_data['tanggal_sk'],
                    file_sk=form.cleaned_data['file_sk'],
                    keterangan="Pendaftaran awal pegawai ke dalam sistem."
                )

            messages.success(request, f'Data pegawai {pegawai.nama_lengkap} berhasil ditambahkan!')
            return redirect('pegawai_detail', pk=pegawai.pk)
    else:
        form = PegawaiCreateForm()
        
    return render(request, 'pegawai/form.html', {'form': form, 'title': 'Tambah Data Pegawai', 'is_create': True})


@login_required
def pegawai_update(request, pk):
    pegawai = get_object_or_404(Pegawai, pk=pk)
    if request.method == 'POST':
        form = PegawaiForm(request.POST, instance=pegawai)
        if form.is_valid():
            form.save()
            messages.success(request, 'Identitas pegawai berhasil diperbarui.')
            return redirect('pegawai_detail', pk=pegawai.pk)
    else:
        form = PegawaiForm(instance=pegawai)
        
    return render(request, 'pegawai/form.html', {'form': form, 'title': 'Edit Data Pegawai', 'is_create': False})


@login_required
def pegawai_delete(request, pk):
    pegawai = get_object_or_404(Pegawai, pk=pk)
    if request.method == 'POST':
        nama = pegawai.nama_lengkap
        nip = pegawai.nip
        pegawai.delete()
        messages.success(request, f'Data pegawai {nama} (NIP: {nip}) berhasil dihapus.')
    return redirect('pegawai_list')


@login_required
def pegawai_detail(request, pk):
    pegawai = get_object_or_404(Pegawai, pk=pk)
    riwayat_kepegawaian_list = pegawai.riwayat_kepegawaian.all()
    riwayat_jabatan_list = pegawai.riwayat_jabatan.select_related('jabatan', 'jabatan__jenis', 'jabatan__jenjang', 'unit_kerja').all()
    riwayat_pangkat_list = pegawai.riwayat_pangkat.select_related('pangkat').all()
    riwayat_pendidikan_list = pegawai.riwayat_pendidikan.select_related('tingkat').all()

    active_tab = request.GET.get('tab', 'kepegawaian')
    
    return render(request, 'pegawai/detail.html', {
        'pegawai': pegawai,
        'riwayat_kepegawaian_list': riwayat_kepegawaian_list,
        'riwayat_jabatan_list': riwayat_jabatan_list,
        'riwayat_pangkat_list': riwayat_pangkat_list,
        'riwayat_pendidikan_list': riwayat_pendidikan_list,
        'active_tab': active_tab,
    })


@login_required
def pegawai_import(request):
    if request.method == 'POST':
        form = ImportPegawaiForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file_excel']
            filename = uploaded_file.name

            try:
                df = pd.read_csv(uploaded_file, dtype=str) if filename.endswith('.csv') else pd.read_excel(uploaded_file, dtype=str)
                df = df.fillna('')
                df.columns = df.columns.str.strip().str.lower()

                success_count, riwayat_count = 0, 0

                with transaction.atomic():
                    for index, row in df.iterrows():
                        nip = str(row.get('nip', '')).strip()
                        if not nip:
                            continue

                        # Parse Tanggal Lahir
                        tanggal_lahir_raw = str(row.get('tanggal_lahir', '')).strip()
                        tanggal_lahir = pd.to_datetime(tanggal_lahir_raw, errors='coerce')
                        tanggal_lahir_str = tanggal_lahir.strftime('%Y-%m-%d') if pd.notnull(tanggal_lahir) else '1990-01-01'
                        
                        # Jenis Transaksi & Mapping Status
                        jenis_transaksi = str(row.get('jenis_transaksi', 'PPPK')).strip().upper()
                        mapping_status = {
                            'CPNS': 'AKTIF', 
                            'PNS': 'AKTIF', 
                            'PPPK': 'AKTIF', 
                            'PERPANJANGAN_PPPK': 'AKTIF',
                            'PPPK_PW': 'PPPK_PW',
                            'PERPANJANGAN_PPPK_PW': 'PPPK_PW',
                            'MUTASI_MASUK': 'AKTIF', 
                            'REAKTIF': 'AKTIF', 
                            'MUTASI_KELUAR': 'MUTASI_KELUAR', 
                            'PENSIUN': 'PENSIUN', 
                            'CLTN': 'CLTN', 
                            'TUGAS_BELAJAR': 'TUGAS_BELAJAR',
                        }
                        status_keaktifan = mapping_status.get(jenis_transaksi, 'AKTIF')

                        # Update / Create Profil Pegawai
                        pegawai, created = Pegawai.objects.update_or_create(
                            nip=nip,
                            defaults={
                                'nama_lengkap': str(row.get('nama_lengkap', '')).strip(),
                                'tempat_lahir': str(row.get('tempat_lahir', '')).strip(),
                                'tanggal_lahir': tanggal_lahir_str,
                                'jenis_kelamin': str(row.get('jenis_kelamin', 'L')).strip().upper(),
                                'agama': str(row.get('agama', 'ISLAM')).strip().upper(),
                                'status_keaktifan': status_keaktifan,
                                'alamat': str(row.get('alamat', '')).strip(),
                                'nomor_hp': str(row.get('nomor_hp', '')).strip(),
                                'email': str(row.get('email', '')).strip(),
                            }
                        )

                        # Parse Parameter SK / Kontrak
                        nomor_sk = str(row.get('nomor_sk', '')).strip()
                        tmt_raw = str(row.get('tmt', '')).strip()
                        tmt_selesai_raw = str(row.get('tmt_selesai', '')).strip() # Kolom Akhir Kontrak
                        tanggal_sk_raw = str(row.get('tanggal_sk', '')).strip()

                        tmt_parsed = pd.to_datetime(tmt_raw, errors='coerce')
                        tmt_selesai_parsed = pd.to_datetime(tmt_selesai_raw, errors='coerce')
                        tanggal_sk_parsed = pd.to_datetime(tanggal_sk_raw, errors='coerce')

                        if nomor_sk and pd.notnull(tmt_parsed) and pd.notnull(tanggal_sk_parsed):
                            tmt_str = tmt_parsed.strftime('%Y-%m-%d')
                            tmt_selesai_str = tmt_selesai_parsed.strftime('%Y-%m-%d') if pd.notnull(tmt_selesai_parsed) else None

                            # Cari berdasarkan kombinasi Pegawai + Jenis Transaksi + TMT Mulai
                            # agar riwayat perpanjangan baru tersimpan tanpa menimpa riwayat lama
                            riwayat, _ = RiwayatKepegawaian.objects.update_or_create(
                                pegawai=pegawai,
                                jenis_transaksi=jenis_transaksi,
                                tmt=tmt_str,
                                defaults={
                                    'nomor_sk': nomor_sk,
                                    'tanggal_sk': tanggal_sk_parsed.strftime('%Y-%m-%d'),
                                    'tmt_selesai': tmt_selesai_str,
                                    'keterangan': str(row.get('keterangan', 'Import Data Kepegawaian')).strip()
                                }
                            )
                            # Panggil save() eksplisit agar memicu update status_keaktifan di model Pegawai
                            riwayat.save()
                            riwayat_count += 1
                            
                        success_count += 1

                messages.success(request, f'Berhasil mengimpor {success_count} data pegawai dan {riwayat_count} riwayat SK/Kontrak!')
                return redirect('pegawai_list')

            except Exception as e:
                messages.error(request, f'Gagal memproses file import: {str(e)}')
    else:
        form = ImportPegawaiForm()

    return render(request, 'pegawai/import.html', {'form': form, 'title': 'Import Data Pegawai & SK Pengangkatan'})