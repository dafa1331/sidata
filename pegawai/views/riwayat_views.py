import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from jabatan.models import Jabatan
from unit_kerja.models import UnitKerja
from pangkat.models import Pangkat
from pendidikan.models import TingkatPendidikan

from pegawai.models import Pegawai, RiwayatKepegawaian, RiwayatJabatan, RiwayatPangkat, RiwayatPendidikan
from pegawai.forms import (
    RiwayatKepegawaianForm, RiwayatJabatanForm, ImportSKJabatanMassalForm, 
    ImportRiwayatJabatanForm, RiwayatPangkatForm, ImportRiwayatPangkatForm, 
    RiwayatPendidikanForm, ImportRiwayatPendidikanForm
)
from .helpers import get_jabatan_from_excel

# --- RIWAYAT KEPEGAWAIAN ---
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


# --- RIWAYAT JABATAN ---
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

                riwayat_objects, missing_logs = [], []

                with transaction.atomic():
                    for index, row in df.iterrows():
                        nip = str(row.get('nip', '')).strip()
                        nama_jabatan_excel = str(row.get('nama_jabatan', '')).strip()
                        unit_kerja_excel = str(row.get('unit_kerja', '')).strip().lower()

                        pegawai = pegawai_map.get(nip)
                        jabatan_obj = get_jabatan_from_excel(nama_jabatan_excel, jabatan_map)
                        unit_kerja_obj = unit_kerja_map.get(unit_kerja_excel)

                        if not pegawai or not jabatan_obj or not unit_kerja_obj:
                            missing_logs.append(f"Baris {index+2}: Data NIP/Jabatan/Unit Kerja tidak ditemukan")
                            continue

                        if jabatan_obj.jenis and jabatan_obj.jenis.nama.strip().lower() == 'struktural':
                            pair = (jabatan_obj.id, unit_kerja_obj.id)
                            if pair in occupied_struktural:
                                missing_logs.append(f"Baris {index+2}: Jabatan Struktural '{jabatan_obj.nama_jabatan}' TERKUNCI")
                                continue
                            occupied_struktural.add(pair)

                        riwayat_objects.append(
                            RiwayatJabatan(
                                pegawai=pegawai, jabatan=jabatan_obj, unit_kerja=unit_kerja_obj,
                                tmt_jabatan=tmt_jabatan, nomor_sk=nomor_sk, tanggal_sk=tanggal_sk,
                                pejabat_penetap=pejabat_penetap, file_sk=file_sk,
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

                riwayat_objects, missing_logs = [], []

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

                        if not nip or not pegawai or not jabatan_obj or not unit_kerja_obj or pd.isnull(tmt_parsed):
                            missing_logs.append(f"Baris {index+2}: Format data tidak valid")
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
                                missing_logs.append(f"Baris {index+2}: Jabatan Struktural '{jabatan_obj.nama_jabatan}' TERKUNCI")
                                continue
                            occupied_struktural.add(pair)

                        riwayat_objects.append(
                            RiwayatJabatan(
                                pegawai=pegawai, jabatan=jabatan_obj, unit_kerja=unit_kerja_obj,
                                status_pelantikan=status_pelantikan, tmt_jabatan=tmt_parsed.strftime('%Y-%m-%d'),
                                nomor_sk=nomor_sk, tanggal_sk=tanggal_sk_parsed.strftime('%Y-%m-%d') if pd.notnull(tanggal_sk_parsed) else tmt_parsed.strftime('%Y-%m-%d'),
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


# --- API AJAX & TOGGLE GELAR ---
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
    pendidikan = get_object_or_404(RiwayatPendidikan, pk=pk)
    pendidikan.tampilkan_gelar = not pendidikan.tampilkan_gelar
    pendidikan.save(update_fields=['tampilkan_gelar'])
    return JsonResponse({
        'status': 'success',
        'tampilkan_gelar': pendidikan.tampilkan_gelar,
        'nama_dengan_gelar': pendidikan.pegawai.nama_dengan_gelar,
        'message': 'Status tampilan gelar berhasil diperbarui.'
    })


# --- RIWAYAT PANGKAT ---
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

                nip_list = [str(nip).strip() for nip in df['nip'] if str(nip).strip()]
                pegawai_map = {p.nip: p for p in Pegawai.objects.filter(nip__in=nip_list)}

                pangkat_qs = Pangkat.objects.filter(is_active=True)
                pangkat_map = {p.golongan.strip().lower(): p for p in pangkat_qs}

                riwayat_objects, missing_logs = [], []

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

                        if not pegawai or not pangkat_obj or pd.isnull(tmt_parsed) or pd.isnull(tanggal_sk_parsed):
                            missing_logs.append(f"Baris {index+2}: Data Pangkat/SK tidak valid")
                            continue

                        riwayat_objects.append(
                            RiwayatPangkat(
                                pegawai=pegawai, pangkat=pangkat_obj, jenis_kp=jenis_kp,
                                tmt_pangkat=tmt_parsed.strftime('%Y-%m-%d'), nomor_sk=nomor_sk,
                                tanggal_sk=tanggal_sk_parsed.strftime('%Y-%m-%d'), pejabat_penetap=pejabat_penetap
                            )
                        )

                    if riwayat_objects:
                        RiwayatPangkat.objects.bulk_create(riwayat_objects)

                messages.success(request, f'Berhasil mengimpor {len(riwayat_objects)} data riwayat pangkat!')
                return redirect('pegawai_list')

            except Exception as e:
                messages.error(request, f'Gagal memproses file: {str(e)}')
    else:
        form = ImportRiwayatPangkatForm()
    return render(request, 'pegawai/riwayat_pangkat_import.html', {'form': form, 'title': 'Import Riwayat Pangkat Massal'})


# --- RIWAYAT PENDIDIKAN ---
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

                riwayat_objects, missing_logs = [], []

                with transaction.atomic():
                    for index, row in df.iterrows():
                        nip = str(row.get('nip', '')).strip()
                        kode_tingkat = str(row.get('tingkat', '')).strip().upper()
                        if not nip:
                            continue

                        tanggal_parsed = pd.to_datetime(str(row.get('tanggal_ijazah', '')).strip(), errors='coerce')
                        pegawai = pegawai_map.get(nip)
                        tingkat_obj = tingkat_map.get(kode_tingkat)

                        if not pegawai or not tingkat_obj or pd.isnull(tanggal_parsed):
                            missing_logs.append(f"Baris {index+2}: Data Pendidikan tidak valid")
                            continue

                        is_pertama_raw = str(row.get('is_pendidikan_pertama', '')).strip().upper()
                        is_pertama = is_pertama_raw in ['1', 'TRUE', 'YA', 'YES']

                        riwayat_objects.append(
                            RiwayatPendidikan(
                                pegawai=pegawai, tingkat=tingkat_obj,
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

                messages.success(request, f'Berhasil mengimpor {len(riwayat_objects)} data riwayat pendidikan!')
                return redirect('pegawai_list')

            except Exception as e:
                messages.error(request, f'Gagal memproses file: {str(e)}')
    else:
        form = ImportRiwayatPendidikanForm()
    return render(request, 'pegawai/riwayat_pendidikan_import.html', {'form': form, 'title': 'Import Riwayat Pendidikan Massal'})