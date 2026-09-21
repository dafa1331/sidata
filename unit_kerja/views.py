import pandas as pd
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, ProtectedError

from .models import UnitKerja
from .forms import UnitKerjaForm, ImportUnitKerjaForm


# 1. READ (List, Search & Filter Jenis)
@login_required
def unit_kerja_list(request):
    query = request.GET.get('q', '').strip()
    
    # Tambahkan order_by agar paginasi konsisten
    unit_list = UnitKerja.objects.select_related('parent').all().order_by('id')

    if query:
        unit_list = unit_list.filter(
            Q(nama__icontains=query) |
            Q(kode__icontains=query) |
            Q(jenis__icontains=query) |
            Q(parent__nama__icontains=query)
        )

    # Paginasi (10 data per halaman)
    paginator = Paginator(unit_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'unit_kerja/index.html', {
        'unit_list': page_obj,
        'query': query,
        'title': 'Master Unit Kerja'
    })


# 2. CREATE
@login_required
def unit_kerja_create(request):
    if request.method == 'POST':
        form = UnitKerjaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit kerja berhasil ditambahkan.')
            return redirect('unit_kerja_list')
    else:
        form = UnitKerjaForm()
    return render(request, 'unit_kerja/form.html', {'form': form, 'title': 'Tambah Unit Kerja'})


# 3. UPDATE
@login_required
def unit_kerja_update(request, pk):
    unit = get_object_or_404(UnitKerja, pk=pk)
    if request.method == 'POST':
        form = UnitKerjaForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit kerja berhasil diperbarui.')
            return redirect('unit_kerja_list')
    else:
        form = UnitKerjaForm(instance=unit)
    return render(request, 'unit_kerja/form.html', {'form': form, 'title': 'Edit Unit Kerja'})


# 4. DELETE
@login_required
def unit_kerja_delete(request, pk):
    unit = get_object_or_404(UnitKerja, pk=pk)
    if request.method == 'POST':
        try:
            unit.delete()
            messages.success(request, f'Unit kerja "{unit.nama}" berhasil dihapus.')
        except ProtectedError:
            messages.error(request, f'Gagal menghapus! Unit kerja "{unit.nama}" masih memiliki sub-unit atau digunakan oleh data pegawai.')
    
    return redirect('unit_kerja_list')


# 5. IMPORT EXCEL / CSV (SUPPORT KOLOM JENIS)
@login_required
def unit_kerja_import(request):
    if request.method == 'POST':
        form = ImportUnitKerjaForm(request.POST, request.FILES)
        
        if form.is_valid():
            file = request.FILES.get('file_excel')
            
            if not file:
                messages.error(request, "File tidak ditemukan. Silakan pilih berkas Excel / CSV.")
                return render(request, 'unit_kerja/import_form.html', {'form': form, 'title': 'Import Master Unit Kerja'})

            try:
                # 1. BACA FILE EXCEL / CSV
                filename = file.name.lower()
                if filename.endswith('.csv'):
                    df = pd.read_csv(file)
                elif filename.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file)
                else:
                    messages.error(request, "Format file tidak didukung! Harus berupa file .xlsx, .xls, atau .csv.")
                    return render(request, 'unit_kerja/import_form.html', {'form': form, 'title': 'Import Master Unit Kerja'})

                # 2. BERSIHKAN & VALIDASI HEADER KOLOM
                df.columns = df.columns.astype(str).str.strip().str.lower()
                df = df.fillna('')

                if 'nama' not in df.columns:
                    messages.error(
                        request, 
                        f"Gagal: Kolom wajib 'nama' tidak ditemukan di Excel! Header yang terbaca: {list(df.columns)}"
                    )
                    return render(request, 'unit_kerja/import_form.html', {'form': form, 'title': 'Import Master Unit Kerja'})

                created_count = 0
                updated_count = 0
                errors = []

                # LIST CHOICES VALID UNTUK JENIS UNIT KERJA
                valid_jenis = [choice[0] for choice in UnitKerja.JENIS_CHOICES]

                # PASS 1: Simpan / Update Unit Kerja & Jenis (Tanpa Parent Dulu)
                for index, row in df.iterrows():
                    baris_ke = index + 2  # Sesuaikan nomor baris Excel (Header = 1)
                    nama = str(row.get('nama', '')).strip()
                    kode = str(row.get('kode', '')).strip() or None
                    
                    # VALIDASI KOLOM JENIS
                    jenis_excel = str(row.get('jenis', '')).strip().upper() or None
                    jenis = jenis_excel if jenis_excel in valid_jenis else None

                    if not nama:
                        errors.append(f"Baris {baris_ke}: Nama unit kerja kosong, dilewati.")
                        continue

                    try:
                        if kode:
                            unit, created = UnitKerja.objects.update_or_create(
                                kode=kode,
                                defaults={
                                    'nama': nama,
                                    'jenis': jenis
                                }
                            )
                        else:
                            unit, created = UnitKerja.objects.get_or_create(
                                nama=nama,
                                defaults={
                                    'kode': None,
                                    'jenis': jenis
                                }
                            )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    except Exception as err_row:
                        errors.append(f"Baris {baris_ke} ({nama}): {str(err_row)}")

                # PASS 2: Hubungkan Hirarki Parent setelah Semua Node Tercipta
                parent_col = None
                if 'kode_parent' in df.columns:
                    parent_col = 'kode_parent'
                elif 'parent' in df.columns:
                    parent_col = 'parent'

                if parent_col:
                    for index, row in df.iterrows():
                        baris_ke = index + 2
                        kode = str(row.get('kode', '')).strip()
                        nama = str(row.get('nama', '')).strip()
                        parent_val = str(row.get(parent_col, '')).strip()

                        if not parent_val:
                            continue

                        child_unit = UnitKerja.objects.filter(kode=kode).first() if kode else UnitKerja.objects.filter(nama=nama).first()
                        parent_unit = UnitKerja.objects.filter(kode=parent_val).first() or UnitKerja.objects.filter(nama=parent_val).first()

                        if child_unit and parent_unit:
                            if child_unit.pk != parent_unit.pk:
                                child_unit.parent = parent_unit
                                child_unit.save()
                        elif not parent_unit:
                            errors.append(f"Baris {baris_ke}: Induk '{parent_val}' tidak ditemukan di database.")

                # REKAP PESAN KESUKSESAN & ERROR
                if created_count > 0 or updated_count > 0:
                    msg = f"Import Berhasil! {created_count} unit baru dibuat, {updated_count} diperbarui."
                    if errors:
                        msg += f" (Terdapat {len(errors)} catatan kecil)."
                    messages.success(request, msg)

                if errors:
                    for err in errors[:5]:
                        messages.warning(request, err)
                    if len(errors) > 5:
                        messages.warning(request, f"...dan {len(errors) - 5} error lainnya.")

                if created_count == 0 and updated_count == 0 and not errors:
                    messages.error(request, "File Excel dibaca, tetapi tidak ada data yang berhasil diproses.")

                return redirect('unit_kerja_list')

            except Exception as e:
                print("--- ERROR SYSTEM IMPORT UNIT KERJA ---")
                traceback.print_exc()
                messages.error(request, f"Terjadi kesalahan teknis saat membaca file: {str(e)}")
        else:
            for field, err_list in form.errors.items():
                for err in err_list:
                    messages.error(request, f"Error Form ({field}): {err}")

    else:
        form = ImportUnitKerjaForm()

    return render(request, 'unit_kerja/import_form.html', {'form': form, 'title': 'Import Master Unit Kerja'})