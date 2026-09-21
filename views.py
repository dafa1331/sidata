import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Prefetch, Min
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from datetime import date
from dateutil.relativedelta import relativedelta

from .decorators import role_required

# Import Model Master External
from jabatan.models import Jabatan
from unit_kerja.models import UnitKerja
from pangkat.models import Pangkat
from pendidikan.models import TingkatPendidikan

# Import Model & Form Internal App Pegawai
from .models import Pegawai, RiwayatKepegawaian, RiwayatJabatan, RiwayatPangkat, RiwayatPendidikan
from .forms import (
    PegawaiCreateForm, 
    PegawaiForm, 
    RiwayatKepegawaianForm, 
    ImportPegawaiForm,
    RiwayatJabatanForm, 
    ImportSKJabatanMassalForm,
    ImportRiwayatJabatanForm,
    RiwayatPangkatForm, 
    ImportRiwayatPangkatForm,
    RiwayatPendidikanForm, 
    ImportRiwayatPendidikanForm,
    EntryJabatanForm, 
    EntryPangkatForm, 
    EntryPendidikanForm
)


# ==========================================
# HELPER PENCACAH/PARSER JABATAN FUNGSIONAL
# ==========================================

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
    
    # 1. Jika pencocokan langsung ada (misal di Master ditulis lengkap)
    if clean_raw in jabatan_map:
        return jabatan_map[clean_raw]
    
    # 2. Cek apakah ada Jenjang Fungsional di bagian belakang
    raw_upper = jabatan_raw.strip().upper()
    for jnj in JENJANG_LIST:
        if raw_upper.endswith(jnj):
            nama_tanpa_jenjang = raw_upper[:-len(jnj)].strip().lower()
            
            # Cari di QuerySet Jabatan yang namanya cocok DAN jenjangnya cocok dengan "jnj"
            jabatan_spesifik = Jabatan.objects.filter(
                nama_jabatan__iexact=nama_tanpa_jenjang,
                jenjang__nama__iexact=jnj,
                is_active=True
            ).select_related('jenis', 'jenjang').first()

            if jabatan_spesifik:
                return jabatan_spesifik
            
            # Fallback jika master jabatan tidak memisah jenjang dalam objek berbeda
            if nama_tanpa_jenjang in jabatan_map:
                return jabatan_map[nama_tanpa_jenjang]
            break

    return None


# ==========================================
# 1. READ & PEGAWAI CRUD
# ==========================================

from django.db.models import F

from django.db.models import Q, Prefetch, Min  # Pastikan Min sudah di-import

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

    # 1. FILTER CARI TEXT (NIP, NAMA, EMAIL)
    if query:
        pegawai = pegawai.filter(
            Q(nip__icontains=query) | 
            Q(nama_lengkap__icontains=query) |
            Q(email__icontains=query)
        )
        
    # 2. FILTER JENIS KELAMIN
    if jk_filter in ['L', 'P']:
        pegawai = pegawai.filter(jenis_kelamin=jk_filter)
        
    # 3. FILTER STATUS KEAKTIFAN
    if status_filter:
        pegawai = pegawai.filter(status_keaktifan=status_filter)
        
    # 4. FILTER JABATAN
    if jabatan_filter == 'BELUM_ADA':
        # Pegawai yang belum memiliki riwayat jabatan
        pegawai = pegawai.filter(riwayat_jabatan__isnull=True)
    elif jabatan_filter:
        if jabatan_filter.isdigit():
            pegawai = pegawai.filter(riwayat_jabatan__jabatan_id=int(jabatan_filter)).distinct()
        else:
            pegawai = pegawai.filter(riwayat_jabatan__jabatan__nama_jabatan__iexact=jabatan_filter).distinct()

    # 5. DEDUPLIKASI DROPDOWN JABATAN (Menggunakan Min 'id')
    jabatan_list = Jabatan.objects.filter(is_active=True).values(
        'nama_jabatan',
        'jenjang__nama'
    ).annotate(
        id_terwakili=Min('id')  # <-- MENGGUNAKAN Min LANGSUNG
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


# ==========================================
# 2. RIWAYAT KEPEGAWAIAN CRUD & IMPORT
# ==========================================

@login_required
def riwayat_kepegawaian_create(request, pegawai_id):
    pegawai = get_object_or_404(Pegawai, pk=pegawai_id)
    if request.method == 'POST':
        form = RiwayatKepegawaianForm(request.POST, request.FILES)
        if form.is_valid():
            riwayat = form.save(commit=False)
            riwayat.pegawai = pegawai
            riwayat.save()
            messages.success(request, 'Riwayat kepegawaian berhasil ditambahkan.')
            return redirect('pegawai_detail', pk=pegawai.pk)
    else:
        form = RiwayatKepegawaianForm()
        
    return render(request, 'pegawai/riwayat_kepegawaian_form.html', {'form': form, 'pegawai': pegawai, 'title': f'Tambah Riwayat Kepegawaian - {pegawai.nama_lengkap}'})


@login_required
def riwayat_kepegawaian_update(request, pk):
    riwayat = get_object_or_404(RiwayatKepegawaian, pk=pk)
    pegawai = riwayat.pegawai
    if request.method == 'POST':
        form = RiwayatKepegawaianForm(request.POST, request.FILES, instance=riwayat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data riwayat kepegawaian berhasil diperbarui.')
            return redirect('pegawai_detail', pk=pegawai.pk)
    else:
        form = RiwayatKepegawaianForm(instance=riwayat)
        
    return render(request, 'pegawai/riwayat_kepegawaian_form.html', {'form': form, 'pegawai': pegawai, 'title': f'Edit Riwayat Kepegawaian - {pegawai.nama_lengkap}'})


@login_required
def riwayat_kepegawaian_delete(request, pk):
    riwayat = get_object_or_404(RiwayatKepegawaian, pk=pk)
    pegawai = riwayat.pegawai
    if request.method == 'POST':
        riwayat.delete()
        latest = pegawai.riwayat_kepegawaian.order_by('-tmt').first()
        if latest:
            mapping_status = {
                'CPNS': 'AKTIF', 'PNS': 'AKTIF', 'PPPK': 'AKTIF', 'MUTASI_MASUK': 'AKTIF', 'REAKTIF': 'AKTIF',
                'MUTASI_KELUAR': 'MUTASI_KELUAR', 'PENSIUN': 'PENSIUN', 'CLTN': 'CLTN', 'TUGAS_BELAJAR': 'TUGAS_BELAJAR',
            }
            pegawai.status_keaktifan = mapping_status.get(latest.jenis_transaksi, 'AKTIF')
        else:
            pegawai.status_keaktifan = 'AKTIF'
        pegawai.save(update_fields=['status_keaktifan'])
        messages.success(request, 'Riwayat kepegawaian berhasil dihapus.')
        
    return redirect('pegawai_detail', pk=pegawai.pk)


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

                        tanggal_lahir_raw = str(row.get('tanggal_lahir', '')).strip()
                        tanggal_lahir = pd.to_datetime(tanggal_lahir_raw, errors='coerce')
                        tanggal_lahir_str = tanggal_lahir.strftime('%Y-%m-%d') if pd.notnull(tanggal_lahir) else '1990-01-01'
                        
                        jenis_transaksi = str(row.get('jenis_transaksi', 'PPPK')).strip().upper()
                        mapping_status = {
                            'CPNS': 'AKTIF', 'PNS': 'AKTIF', 'PPPK': 'AKTIF', 'PPPK_PW': 'PPPK_PW',
                            'MUTASI_MASUK': 'AKTIF', 'REAKTIF': 'AKTIF', 'MUTASI_KELUAR': 'MUTASI_KELUAR', 
                            'PENSIUN': 'PENSIUN', 'CLTN': 'CLTN', 'TUGAS_BELAJAR': 'TUGAS_BELAJAR',
                        }
                        status_keaktifan = mapping_status.get(jenis_transaksi, 'AKTIF')

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

                        nomor_sk = str(row.get('nomor_sk', '')).strip()
                        tmt_raw = str(row.get('tmt', '')).strip()
                        tanggal_sk_raw = str(row.get('tanggal_sk', '')).strip()

                        tmt_parsed = pd.to_datetime(tmt_raw, errors='coerce')
                        tanggal_sk_parsed = pd.to_datetime(tanggal_sk_raw, errors='coerce')

                        if nomor_sk and pd.notnull(tmt_parsed) and pd.notnull(tanggal_sk_parsed):
                            RiwayatKepegawaian.objects.update_or_create(
                                pegawai=pegawai,
                                nomor_sk=nomor_sk,
                                defaults={
                                    'jenis_transaksi': jenis_transaksi,
                                    'tmt': tmt_parsed.strftime('%Y-%m-%d'),
                                    'tanggal_sk': tanggal_sk_parsed.strftime('%Y-%m-%d'),
                                    'keterangan': str(row.get('keterangan', 'Import Pegawai Massal')).strip()
                                }
                            )
                            riwayat_count += 1
                        success_count += 1

                messages.success(request, f'Berhasil mengimpor {success_count} data pegawai dan {riwayat_count} riwayat SK!')
                return redirect('pegawai_list')

            except Exception as e:
                messages.error(request, f'Gagal memproses file import: {str(e)}')
    else:
        form = ImportPegawaiForm()

    return render(request, 'pegawai/import.html', {'form': form, 'title': 'Import Data Pegawai & SK Pengangkatan'})


# ==========================================
# 3. RIWAYAT JABATAN INDIVIDU & MASSAL (+ PENGUNCIAN STRUKTURAL)
# ==========================================

@login_required
def riwayat_jabatan_create(request, pegawai_id):
    pegawai = get_object_or_404(Pegawai, pk=pegawai_id)
    if request.method == 'POST':
        form = RiwayatJabatanForm(request.POST, request.FILES)
        if form.is_valid():
            riwayat = form.save(commit=False)
            riwayat.pegawai = pegawai
            riwayat.save()
            messages.success(request, 'Riwayat jabatan berhasil ditambahkan.')
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=jabatan")
    else:
        form = RiwayatJabatanForm()
        
    return render(request, 'pegawai/riwayat_jabatan_form.html', {'form': form, 'pegawai': pegawai, 'title': f'Tambah Riwayat Jabatan - {pegawai.nama_lengkap}'})


@login_required
def riwayat_jabatan_update(request, pk):
    riwayat = get_object_or_404(RiwayatJabatan, pk=pk)
    pegawai = riwayat.pegawai
    if request.method == 'POST':
        form = RiwayatJabatanForm(request.POST, request.FILES, instance=riwayat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Riwayat jabatan berhasil diperbarui.')
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=jabatan")
    else:
        form = RiwayatJabatanForm(instance=riwayat)
        
    return render(request, 'pegawai/riwayat_jabatan_form.html', {'form': form, 'pegawai': pegawai, 'title': f'Edit Riwayat Jabatan - {pegawai.nama_lengkap}'})


@login_required
def riwayat_jabatan_delete(request, pk):
    riwayat = get_object_or_404(RiwayatJabatan, pk=pk)
    pegawai = riwayat.pegawai
    if request.method == 'POST':
        riwayat.delete()
        messages.success(request, 'Riwayat jabatan berhasil dihapus.')
    return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=jabatan")


# PELANTIKAN MASSAL (SMART JABATAN + PENGUNCIAN STRUKTURAL)
@login_required
def pelantikan_massal(request):
    if request.method == 'POST':
        form = ImportSKJabatanMassalForm(request.POST, request.FILES)
        if form.is_valid():
            nomor_sk = form.cleaned_data['nomor_sk']
            tanggal_sk = form.cleaned_data['tanggal_sk']
            tmt_jabatan = form.cleaned_data['tmt_jabatan']
            pejabat_penetap = form.cleaned_data['pejabat_penetap']
            file_sk = form.cleaned_data['file_sk']
            uploaded_excel = request.FILES['file_excel']

            try:
                df = pd.read_csv(uploaded_excel, dtype=str) if uploaded_excel.name.endswith('.csv') else pd.read_excel(uploaded_excel, dtype=str)
                df = df.fillna('')
                df.columns = df.columns.str.strip().str.lower()

                nip_list = [str(nip).strip() for nip in df['nip'] if str(nip).strip()]
                pegawai_map = {p.nip: p for p in Pegawai.objects.filter(nip__in=nip_list)}

                jabatan_qs = Jabatan.objects.select_related('jenis').filter(is_active=True)
                jabatan_map = {j.nama_jabatan.strip().lower(): j for j in jabatan_qs}

                unit_kerja_qs = UnitKerja.objects.all()
                unit_kerja_map = {str(getattr(uk, 'nama_unit_kerja', getattr(uk, 'nama', str(uk)))).strip().lower(): uk for uk in unit_kerja_qs}

                occupied_struktural = set(
                    RiwayatJabatan.objects.filter(
                        jabatan__jenis__nama__iexact='struktural',
                        pegawai__status_keaktifan='AKTIF'
                    ).values_list('jabatan_id', 'unit_kerja_id')
                )

                riwayat_objects = []
                missing_logs = []

                with transaction.atomic():
                    for index, row in df.iterrows():
                        nip = str(row.get('nip', '')).strip()
                        nama_jabatan_excel = str(row.get('nama_jabatan', '')).strip()
                        unit_kerja_excel = str(row.get('unit_kerja', '')).strip().lower()

                        pegawai = pegawai_map.get(nip)
                        jabatan_obj = get_jabatan_from_excel(nama_jabatan_excel, jabatan_map)
                        unit_kerja_obj = unit_kerja_map.get(unit_kerja_excel)

                        if not pegawai:
                            missing_logs.append(f"Baris {index+2}: NIP '{nip}' tidak terdaftar")
                            continue
                        if not jabatan_obj:
                            missing_logs.append(f"Baris {index+2}: Jabatan '{nama_jabatan_excel}' tidak ditemukan di Master")
                            continue
                        if not unit_kerja_obj:
                            missing_logs.append(f"Baris {index+2}: Unit Kerja '{row.get('unit_kerja')}' tidak ada di Master")
                            continue

                        # EVALUASI PENGUNCIAN JABATAN STRUKTURAL
                        if jabatan_obj.jenis and jabatan_obj.jenis.nama.strip().lower() == 'struktural':
                            pair = (jabatan_obj.id, unit_kerja_obj.id)
                            if pair in occupied_struktural:
                                missing_logs.append(
                                    f"Baris {index+2}: Jabatan Struktural '{jabatan_obj.nama_jabatan}' pada '{unit_kerja_obj.nama}' TERKUNCI"
                                )
                                continue
                            occupied_struktural.add(pair)

                        riwayat_objects.append(
                            RiwayatJabatan(
                                pegawai=pegawai,
                                jabatan=jabatan_obj,
                                unit_kerja=unit_kerja_obj,
                                tmt_jabatan=tmt_jabatan,
                                nomor_sk=nomor_sk,
                                tanggal_sk=tanggal_sk,
                                pejabat_penetap=pejabat_penetap,
                                file_sk=file_sk,
                            )
                        )

                    if riwayat_objects:
                        RiwayatJabatan.objects.bulk_create(riwayat_objects)

                pesan = f'Berhasil memproses pelantikan massal untuk {len(riwayat_objects)} pegawai!'
                if missing_logs:
                    messages.warning(request, f"{pesan} Beberapa baris diabaikan: {', '.join(missing_logs[:3])}")
                else:
                    messages.success(request, pesan)

                return redirect('pegawai_list')

            except Exception as e:
                messages.error(request, f'Gagal memproses pelantikan massal: {str(e)}')
    else:
        form = ImportSKJabatanMassalForm()

    return render(request, 'pegawai/pelantikan_massal.html', {'form': form, 'title': 'Input Pelantikan / Mutasi Jabatan Massal'})


# IMPORT RIWAYAT JABATAN EXISTING (SMART JABATAN + PENGUNCIAN STRUKTURAL)
@login_required
def riwayat_jabatan_import(request):
    if request.method == 'POST':
        form = ImportRiwayatJabatanForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_excel = request.FILES['file_excel']
            filename = uploaded_excel.name

            try:
                df = pd.read_csv(uploaded_excel, dtype=str) if filename.endswith('.csv') else pd.read_excel(uploaded_excel, dtype=str)
                df = df.fillna('')
                df.columns = df.columns.str.strip().str.lower()

                nip_list = [str(nip).strip() for nip in df['nip'] if str(nip).strip()]
                pegawai_map = {p.nip: p for p in Pegawai.objects.filter(nip__in=nip_list)}

                jabatan_qs = Jabatan.objects.select_related('jenis').filter(is_active=True)
                jabatan_map = {j.nama_jabatan.strip().lower(): j for j in jabatan_qs}

                unit_kerja_qs = UnitKerja.objects.all()
                unit_kerja_map = {str(getattr(uk, 'nama_unit_kerja', getattr(uk, 'nama', str(uk)))).strip().lower(): uk for uk in unit_kerja_qs}

                occupied_struktural = set(
                    RiwayatJabatan.objects.filter(
                        jabatan__jenis__nama__iexact='struktural',
                        pegawai__status_keaktifan='AKTIF'
                    ).values_list('jabatan_id', 'unit_kerja_id')
                )

                riwayat_objects = []
                missing_logs = []

                with transaction.atomic():
                    for index, row in df.iterrows():
                        nip = str(row.get('nip', '')).strip()
                        nama_jabatan_excel = str(row.get('nama_jabatan', '')).strip()
                        unit_kerja_excel = str(row.get('unit_kerja', '')).strip().lower()
                        
                        nomor_sk = str(row.get('nomor_sk', '')).strip() or '-'
                        pejabat_penetap = str(row.get('pejabat_penetap', '')).strip() or '-'

                        tmt_raw = str(row.get('tmt_jabatan', '')).strip()
                        tanggal_sk_raw = str(row.get('tanggal_sk', '')).strip() or tmt_raw

                        tmt_parsed = pd.to_datetime(tmt_raw, errors='coerce')
                        tanggal_sk_parsed = pd.to_datetime(tanggal_sk_raw, errors='coerce')

                        pegawai = pegawai_map.get(nip)
                        jabatan_obj = get_jabatan_from_excel(nama_jabatan_excel, jabatan_map)
                        unit_kerja_obj = unit_kerja_map.get(unit_kerja_excel)

                        if not nip:
                            continue
                        if not pegawai:
                            missing_logs.append(f"Baris {index+2}: NIP '{nip}' tidak ditemukan")
                            continue
                        if not jabatan_obj:
                            missing_logs.append(f"Baris {index+2}: Jabatan '{nama_jabatan_excel}' tidak ditemukan di Master")
                            continue
                        if not unit_kerja_obj:
                            missing_logs.append(f"Baris {index+2}: Unit Kerja '{row.get('unit_kerja')}' tidak ditemukan di Master")
                            continue
                        if pd.isnull(tmt_parsed):
                            missing_logs.append(f"Baris {index+2}: TMT Jabatan tidak boleh kosong / format salah")
                            continue

                        status_pelantikan_raw = str(row.get('status_pelantikan', '')).strip().upper()
                        jenis_jabatan_nama = jabatan_obj.jenis.nama.strip().lower() if jabatan_obj.jenis else ''

                        if 'pelaksana' in jenis_jabatan_nama or 'struktural' in jenis_jabatan_nama:
                            status_pelantikan = 'DILANTIK'
                        elif status_pelantikan_raw in ['BELUM_DILANTIK', 'BELUM DILANTIK', 'PELAKSANA', 'CPNS']:
                            status_pelantikan = 'BELUM_DILANTIK'
                        else:
                            status_pelantikan = 'DILANTIK'

                        if jenis_jabatan_nama == 'struktural':
                            pair = (jabatan_obj.id, unit_kerja_obj.id)
                            if pair in occupied_struktural:
                                missing_logs.append(
                                    f"Baris {index+2}: Jabatan Struktural '{jabatan_obj.nama_jabatan}' TERKUNCI"
                                )
                                continue
                            occupied_struktural.add(pair)

                        riwayat_objects.append(
                            RiwayatJabatan(
                                pegawai=pegawai,
                                jabatan=jabatan_obj,
                                unit_kerja=unit_kerja_obj,
                                status_pelantikan=status_pelantikan,
                                tmt_jabatan=tmt_parsed.strftime('%Y-%m-%d'),
                                nomor_sk=nomor_sk,
                                tanggal_sk=tanggal_sk_parsed.strftime('%Y-%m-%d') if pd.notnull(tanggal_sk_parsed) else tmt_parsed.strftime('%Y-%m-%d'),
                                pejabat_penetap=pejabat_penetap
                            )
                        )

                    if riwayat_objects:
                        RiwayatJabatan.objects.bulk_create(riwayat_objects)

                pesan = f'Berhasil mengimpor {len(riwayat_objects)} data riwayat jabatan!'
                if missing_logs:
                    messages.warning(request, f"{pesan} Beberapa baris terlewati: {', '.join(missing_logs[:3])}")
                else:
                    messages.success(request, pesan)

                return redirect('pegawai_list')

            except Exception as e:
                messages.error(request, f'Gagal mengimpor file: {str(e)}')
    else:
        form = ImportRiwayatJabatanForm()

    return render(request, 'pegawai/riwayat_jabatan_import.html', {'form': form, 'title': 'Import Riwayat Jabatan Existing'})


# ==========================================
# 4. API DETAIL JABATAN & TOGGLE GELAR
# ==========================================

@login_required
def get_detail_jabatan_api(request, jabatan_id):
    try:
        jabatan = Jabatan.objects.select_related('jenis', 'jenjang').get(pk=jabatan_id)
        data = {
            'jenis_nama': jabatan.jenis.nama if jabatan.jenis else '-',
            'jenjang_nama': jabatan.jenjang.nama if jabatan.jenjang else '-',
            'eselon': jabatan.eselon if jabatan.eselon else '-',
        }
        return JsonResponse({'success': True, 'data': data})
    except Jabatan.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Jabatan tidak ditemukan'}, status=404)


@login_required
@require_POST
def toggle_tampilkan_gelar(request, pk):
    """API endpoint untuk mengubah status tampilkan_gelar pada RiwayatPendidikan via AJAX"""
    pendidikan = get_object_or_404(RiwayatPendidikan, pk=pk)
    
    pendidikan.tampilkan_gelar = not pendidikan.tampilkan_gelar
    pendidikan.save(update_fields=['tampilkan_gelar'])
    
    nama_baru = pendidikan.pegawai.nama_dengan_gelar
    
    return JsonResponse({
        'status': 'success',
        'tampilkan_gelar': pendidikan.tampilkan_gelar,
        'nama_dengan_gelar': nama_baru,
        'message': 'Status tampilan gelar berhasil diperbarui.'
    })


# ==========================================
# 5. RIWAYAT PANGKAT CRUD & IMPORT
# ==========================================

@login_required
def riwayat_pangkat_create(request, pegawai_id):
    pegawai = get_object_or_404(Pegawai, pk=pegawai_id)
    if request.method == 'POST':
        form = RiwayatPangkatForm(request.POST, request.FILES)
        if form.is_valid():
            riwayat = form.save(commit=False)
            riwayat.pegawai = pegawai
            riwayat.save()
            messages.success(request, 'Riwayat pangkat berhasil ditambahkan.')
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=pangkat")
    else:
        form = RiwayatPangkatForm()
        
    return render(request, 'pegawai/riwayat_pangkat_form.html', {'form': form, 'pegawai': pegawai, 'title': f'Tambah Riwayat Pangkat - {pegawai.nama_lengkap}'})


@login_required
def riwayat_pangkat_update(request, pk):
    riwayat = get_object_or_404(RiwayatPangkat, pk=pk)
    pegawai = riwayat.pegawai
    if request.method == 'POST':
        form = RiwayatPangkatForm(request.POST, request.FILES, instance=riwayat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Riwayat pangkat berhasil diperbarui.')
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=pangkat")
    else:
        form = RiwayatPangkatForm(instance=riwayat)
        
    return render(request, 'pegawai/riwayat_pangkat_form.html', {'form': form, 'pegawai': pegawai, 'title': f'Edit Riwayat Pangkat - {pegawai.nama_lengkap}'})


@login_required
def riwayat_pangkat_delete(request, pk):
    riwayat = get_object_or_404(RiwayatPangkat, pk=pk)
    pegawai = riwayat.pegawai
    if request.method == 'POST':
        riwayat.delete()
        messages.success(request, 'Riwayat pangkat berhasil dihapus.')
    return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=pangkat")


@login_required
def riwayat_pangkat_import(request):
    if request.method == 'POST':
        form = ImportRiwayatPangkatForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_excel = request.FILES['file_excel']
            filename = uploaded_excel.name

            try:
                df = pd.read_csv(uploaded_excel, dtype=str) if filename.endswith('.csv') else pd.read_excel(uploaded_excel, dtype=str)
                df = df.fillna('')
                df.columns = df.columns.str.strip().str.lower()

                if df.empty:
                    messages.error(request, 'File Excel / CSV yang diunggah kosong.')
                    return redirect('riwayat_pangkat_import')

                nip_list = [str(nip).strip() for nip in df['nip'] if str(nip).strip()]
                pegawai_map = {p.nip: p for p in Pegawai.objects.filter(nip__in=nip_list)}

                pangkat_qs = Pangkat.objects.filter(is_active=True)
                pangkat_map = {p.golongan.strip().lower(): p for p in pangkat_qs}

                riwayat_objects = []
                missing_logs = []

                with transaction.atomic():
                    for index, row in df.iterrows():
                        nip = str(row.get('nip', '')).strip()
                        if not nip:
                            continue

                        golongan_excel = str(row.get('golongan', '')).strip().lower()
                        jenis_kp = str(row.get('jenis_kp', 'REGULER')).strip().upper()
                        nomor_sk = str(row.get('nomor_sk', '')).strip()
                        pejabat_penetap = str(row.get('pejabat_penetap', '')).strip()

                        tmt_parsed = pd.to_datetime(str(row.get('tmt_pangkat', '')).strip(), errors='coerce')
                        tanggal_sk_parsed = pd.to_datetime(str(row.get('tanggal_sk', '')).strip(), errors='coerce')

                        pegawai = pegawai_map.get(nip)
                        pangkat_obj = pangkat_map.get(golongan_excel)

                        if not pegawai:
                            missing_logs.append(f"Baris {index+2}: NIP '{nip}' tidak terdaftar")
                            continue
                        if not pangkat_obj:
                            missing_logs.append(f"Baris {index+2}: Golongan '{row.get('golongan')}' tidak ada di Master Pangkat")
                            continue
                        if pd.isnull(tmt_parsed) or pd.isnull(tanggal_sk_parsed):
                            missing_logs.append(f"Baris {index+2}: Tanggal TMT/SK tidak valid")
                            continue

                        riwayat_objects.append(
                            RiwayatPangkat(
                                pegawai=pegawai,
                                pangkat=pangkat_obj,
                                jenis_kp=jenis_kp,
                                tmt_pangkat=tmt_parsed.strftime('%Y-%m-%d'),
                                nomor_sk=nomor_sk,
                                tanggal_sk=tanggal_sk_parsed.strftime('%Y-%m-%d'),
                                pejabat_penetap=pejabat_penetap
                            )
                        )

                    if riwayat_objects:
                        RiwayatPangkat.objects.bulk_create(riwayat_objects)

                if riwayat_objects:
                    pesan = f'Berhasil mengimpor {len(riwayat_objects)} data riwayat pangkat!'
                    if missing_logs:
                        messages.warning(request, f"{pesan} Namun ada {len(missing_logs)} baris terlewati: {missing_logs[0]}")
                    else:
                        messages.success(request, pesan)
                else:
                    messages.error(request, "Tidak ada data yang berhasil diimpor.")

                return redirect('pegawai_list')

            except Exception as e:
                messages.error(request, f'Gagal memproses file: {str(e)}')
                return redirect('riwayat_pangkat_import')
    else:
        form = ImportRiwayatPangkatForm()

    return render(request, 'pegawai/riwayat_pangkat_import.html', {'form': form, 'title': 'Import Riwayat Pangkat Massal'})


# ==========================================
# 6. RIWAYAT PENDIDIKAN CRUD & IMPORT
# ==========================================

@login_required
def riwayat_pendidikan_create(request, pegawai_id):
    pegawai = get_object_or_404(Pegawai, pk=pegawai_id)
    if request.method == 'POST':
        form = RiwayatPendidikanForm(request.POST, request.FILES)
        if form.is_valid():
            riwayat = form.save(commit=False)
            riwayat.pegawai = pegawai
            riwayat.save()
            messages.success(request, 'Riwayat pendidikan berhasil ditambahkan.')
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=pendidikan")
    else:
        form = RiwayatPendidikanForm()
        
    return render(request, 'pegawai/riwayat_pendidikan_form.html', {'form': form, 'pegawai': pegawai, 'title': f'Tambah Riwayat Pendidikan - {pegawai.nama_lengkap}'})


@login_required
def riwayat_pendidikan_update(request, pk):
    riwayat = get_object_or_404(RiwayatPendidikan, pk=pk)
    pegawai = riwayat.pegawai
    if request.method == 'POST':
        form = RiwayatPendidikanForm(request.POST, request.FILES, instance=riwayat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Riwayat pendidikan berhasil diperbarui.')
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=pendidikan")
    else:
        form = RiwayatPendidikanForm(instance=riwayat)
        
    return render(request, 'pegawai/riwayat_pendidikan_form.html', {'form': form, 'pegawai': pegawai, 'title': f'Edit Riwayat Pendidikan - {pegawai.nama_lengkap}'})


@login_required
def riwayat_pendidikan_delete(request, pk):
    riwayat = get_object_or_404(RiwayatPendidikan, pk=pk)
    pegawai = riwayat.pegawai
    if request.method == 'POST':
        riwayat.delete()
        messages.success(request, 'Riwayat pendidikan berhasil dihapus.')
    return redirect(f"{reverse('pegawai_detail', kwargs={'pk': pegawai.pk})}?tab=pendidikan")


@login_required
def riwayat_pendidikan_import(request):
    if request.method == 'POST':
        form = ImportRiwayatPendidikanForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_excel = request.FILES['file_excel']
            filename = uploaded_excel.name

            try:
                df = pd.read_csv(uploaded_excel, dtype=str) if filename.endswith('.csv') else pd.read_excel(uploaded_excel, dtype=str)
                df = df.fillna('')
                df.columns = df.columns.str.strip().str.lower()

                nip_list = [str(nip).strip() for nip in df['nip'] if str(nip).strip()]
                pegawai_map = {p.nip: p for p in Pegawai.objects.filter(nip__in=nip_list)}

                tingkat_qs = TingkatPendidikan.objects.filter(is_active=True)
                tingkat_map = {t.kode.strip().upper(): t for t in tingkat_qs}

                riwayat_objects = []
                missing_logs = []

                with transaction.atomic():
                    for index, row in df.iterrows():
                        nip = str(row.get('nip', '')).strip()
                        kode_tingkat = str(row.get('tingkat', '')).strip().upper()
                        
                        if not nip:
                            continue

                        tanggal_parsed = pd.to_datetime(str(row.get('tanggal_ijazah', '')).strip(), errors='coerce')
                        pegawai = pegawai_map.get(nip)
                        tingkat_obj = tingkat_map.get(kode_tingkat)

                        if not pegawai:
                            missing_logs.append(f"Baris {index+2}: NIP '{nip}' tidak terdaftar")
                            continue
                        if not tingkat_obj:
                            missing_logs.append(f"Baris {index+2}: Tingkat '{kode_tingkat}' tidak ditemukan di Master")
                            continue
                        if pd.isnull(tanggal_parsed):
                            missing_logs.append(f"Baris {index+2}: Tanggal ijazah tidak valid")
                            continue

                        is_pertama_raw = str(row.get('is_pendidikan_pertama', '')).strip().upper()
                        is_pertama = is_pertama_raw in ['1', 'TRUE', 'YA', 'YES']

                        riwayat_objects.append(
                            RiwayatPendidikan(
                                pegawai=pegawai,
                                tingkat=tingkat_obj,
                                nama_sekolah=str(row.get('nama_sekolah', '')).strip(),
                                jurusan=str(row.get('jurusan', '')).strip(),
                                gelar_depan=str(row.get('gelar_depan', '')).strip() or None,
                                gelar_belakang=str(row.get('gelar_belakang', '')).strip() or None,
                                nomor_ijazah=str(row.get('nomor_ijazah', '')).strip(),
                                tanggal_ijazah=tanggal_parsed.strftime('%Y-%m-%d'),
                                tahun_lulus=int(row.get('tahun_lulus', 2000)),
                                is_pendidikan_pertama=is_pertama,
                            )
                        )

                    if riwayat_objects:
                        RiwayatPendidikan.objects.bulk_create(riwayat_objects)

                if riwayat_objects:
                    pesan = f'Berhasil mengimpor {len(riwayat_objects)} data riwayat pendidikan!'
                    if missing_logs:
                        messages.warning(request, f"{pesan} Namun ada {len(missing_logs)} baris terlewati: {missing_logs[0]}")
                    else:
                        messages.success(request, pesan)
                    return redirect('pegawai_list')
                else:
                    messages.error(request, "Gagal mengimpor data. Format kolom/data tidak sesuai.")
                    return redirect('riwayat_pendidikan_import')

            except Exception as e:
                messages.error(request, f'Gagal memproses file: {str(e)}')
                return redirect('riwayat_pendidikan_import')
    else:
        form = ImportRiwayatPendidikanForm()

    return render(request, 'pegawai/riwayat_pendidikan_import.html', {'form': form, 'title': 'Import Riwayat Pendidikan Massal'})


# ==========================================
# 7. ENTRY SIDEBAR VIEWS
# ==========================================

@login_required
@role_required('Admin Jabatan', 'Super Admin')
def riwayat_jabatan_entry(request):
    if request.method == 'POST':
        form = EntryJabatanForm(request.POST, request.FILES)
        if form.is_valid():
            riwayat = form.save()
            messages.success(request, f"Berhasil menyimpan SK Jabatan untuk {riwayat.pegawai.nama_lengkap}.")
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': riwayat.pegawai.pk})}?tab=jabatan")
    else:
        form = EntryJabatanForm()

    return render(request, 'pegawai/riwayat_entry_generic.html', {'form': form, 'title': 'Input SK Jabatan Pegawai', 'sub_title': 'Layanan Bidang Jabatan'})


@login_required
@role_required('Admin Pangkat', 'Super Admin')
def riwayat_pangkat_entry(request):
    if request.method == 'POST':
        form = EntryPangkatForm(request.POST, request.FILES)
        if form.is_valid():
            riwayat = form.save()
            messages.success(request, f"Berhasil menyimpan SK Pangkat untuk {riwayat.pegawai.nama_lengkap}.")
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': riwayat.pegawai.pk})}?tab=pangkat")
    else:
        form = EntryPangkatForm()

    return render(request, 'pegawai/riwayat_entry_generic.html', {'form': form, 'title': 'Input SK Pangkat Pegawai', 'sub_title': 'Layanan Bidang Pangkat'})


@login_required
@role_required('Admin Pendidikan', 'Super Admin')
def riwayat_pendidikan_entry(request):
    if request.method == 'POST':
        form = EntryPendidikanForm(request.POST, request.FILES)
        if form.is_valid():
            riwayat = form.save()
            messages.success(request, f"Berhasil menyimpan data Pendidikan untuk {riwayat.pegawai.nama_lengkap}.")
            return redirect(f"{reverse('pegawai_detail', kwargs={'pk': riwayat.pegawai.pk})}?tab=pendidikan")
    else:
        form = EntryPendidikanForm()

    return render(request, 'pegawai/riwayat_entry_generic.html', {'form': form, 'title': 'Input Data Pendidikan Pegawai', 'sub_title': 'Layanan Bidang Pendidikan'})


# ==========================================
# 8. FITUR PROYEKSI PENSIUN & EKSEKUSI SK
# ==========================================

@login_required
def proyeksi_pensiun_view(request):
    tahun_selected = request.GET.get('tahun')
    bulan_selected = request.GET.get('bulan')
    
    # Filter pegawai AKTIF berusia >= 50 tahun (mencegah N+1 Query & Infinite Loading)
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
        # Ambil jabatan terakhir langsung dari memory
        jabatan_terakhir = p.prefetched_jabatan_list[0] if p.prefetched_jabatan_list else None
        
        # --- ATURAN KALKULASI BUP ---
        usia_bup = 58  # Default
        if jabatan_terakhir and jabatan_terakhir.jabatan:
            obj_j = jabatan_terakhir.jabatan
            nama_j = obj_j.nama_jabatan.lower() if obj_j.nama_jabatan else ''
            jenis = (obj_j.jenis.nama if obj_j.jenis else '').lower()
            jenjang = (obj_j.jenjang.nama if obj_j.jenjang else '').lower()
            eselon = (obj_j.eselon if hasattr(obj_j, 'eselon') and obj_j.eselon else '').lower()

            # BUP 65
            if 'UTAMA' in jenjang or 'I.a' in eselon or 'I.b' in eselon:
                usia_bup = 65
            # BUP 60: Guru, Ahli Madya, & Struktural II.a/II.b
            elif 'guru' in nama_j or 'GURU' in jenis or 'ahli madya' in jenjang or 'ii.a' in eselon or 'ii.b' in eselon:
                usia_bup = 60

        # Hitung TMT Pensiun
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

    # Urutkan ringkasan tahun
    rekap_tahun = sorted([{'tahun': k, 'jumlah': v} for k, v in agregasi_tahun.items()], key=lambda x: x['tahun'])

    # Filter Tahun & Bulan jika dipilih
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
        
        # Tangkap nomor page dari form agar bisa kembali ke halaman yang sama
        page_number = request.POST.get('page', '1')
        
        nomor_sk = request.POST.get('nomor_sk', '').strip()
        tanggal_sk = request.POST.get('tanggal_sk', '').strip()
        pejabat_penetap = request.POST.get('pejabat_penetap', '').strip()

        # Redirect target dengan nomor page
        redirect_url = f"{reverse('pegawai:proyeksi_pensiun')}?page={page_number}"

        if not nomor_sk or not tanggal_sk:
            messages.error(request, 'Nomor SK dan Tanggal SK wajib diisi!')
            return redirect(redirect_url)

        try:
            with transaction.atomic():
                # 1. Catat transaksi di RiwayatKepegawaian
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