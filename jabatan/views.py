import pandas as pd
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Jabatan, JenisJabatan, JenjangJabatan
from .forms import JabatanCreateForm, JabatanUpdateForm, ImportJabatanForm

@login_required
def jabatan_list(request):
    jabatan = Jabatan.objects.select_related('jenis', 'jenjang').all()
    return render(request, 'jabatan/index.html', {'jabatan_list': jabatan})

@login_required
def jabatan_create(request):
    if request.method == 'POST':
        form = JabatanCreateForm(request.POST)
        if form.is_valid():
            jenis = form.cleaned_data['jenis']
            nama_jabatan = form.cleaned_data['nama_jabatan']
            list_jenjang = form.cleaned_data['jenjang_list']
            eselon = form.cleaned_data['eselon']
            is_active = form.cleaned_data['is_active']

            if jenis and 'fungsional' in jenis.nama.lower() and list_jenjang:
                jabatan_objects = []
                for jnj in list_jenjang:
                    jabatan_objects.append(
                        Jabatan(
                            jenis=jenis,
                            nama_jabatan=nama_jabatan,
                            jenjang=jnj,
                            eselon=None,
                            is_active=is_active
                        )
                    )
                Jabatan.objects.bulk_create(jabatan_objects)
                messages.success(request, f"Berhasil menambahkan {len(jabatan_objects)} jenjang jabatan.")
            else:
                jabatan = form.save(commit=False)
                jabatan.jenjang = None
                jabatan.save()
                messages.success(request, f"Berhasil menambahkan jabatan '{nama_jabatan}'.")

            return redirect('jabatan_list')
    else:
        form = JabatanCreateForm()

    # PASTIKAN 'is_create': True DIKIRIM DI SINI
    return render(request, 'jabatan/form.html', {
        'form': form, 
        'title': 'Tambah Master Jabatan', 
        'is_create': True
    })

@login_required
def jabatan_update(request, pk):
    jabatan = get_object_or_404(Jabatan, pk=pk)
    if request.method == 'POST':
        form = JabatanUpdateForm(request.POST, instance=jabatan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Jabatan '{jabatan.nama_jabatan}' berhasil diperbarui.")
            return redirect('jabatan_list')
    else:
        form = JabatanUpdateForm(instance=jabatan)

    return render(request, 'jabatan/form.html', {'form': form, 'title': 'Edit Master Jabatan', 'is_create': False})

@login_required
def jabatan_update(request, pk):
    jabatan = get_object_or_404(Jabatan, pk=pk)
    if request.method == 'POST':
        form = JabatanUpdateForm(request.POST, instance=jabatan) # <-- GUNAKAN JabatanUpdateForm
        if form.is_valid():
            form.save()
            messages.success(request, f"Jabatan '{jabatan.nama_jabatan}' berhasil diperbarui.")
            return redirect('jabatan_list')
    else:
        form = JabatanUpdateForm(instance=jabatan) # <-- GUNAKAN JabatanUpdateForm

    return render(request, 'jabatan/form.html', {'form': form, 'title': 'Edit Master Jabatan', 'is_create': False})

@login_required
def jabatan_delete(request, pk):
    jabatan = get_object_or_404(Jabatan, pk=pk)
    if request.method == 'POST':
        try:
            jabatan.delete()
            messages.success(request, f'Master jabatan "{jabatan.nama_jabatan}" berhasil dihapus.')
        except ProtectedError:
            messages.error(request, f'Gagal menghapus! Jabatan "{jabatan.nama_jabatan}" masih digunakan oleh data pegawai.')
        return redirect('jabatan_list')
        
    return render(request, 'jabatan/delete_confirm.html', {'jabatan': jabatan})

@login_required
def jabatan_list(request):
    query = request.GET.get('q', '').strip()
    
    # Fetch data dengan select_related agar efisien
    jabatan = Jabatan.objects.select_related('jenis', 'jenjang').all()

    # Filter pencarian jika ada
    if query:
        jabatan = jabatan.filter(
            Q(nama_jabatan__icontains=query) |
            Q(jenis__nama__icontains=query) |
            Q(jenjang__nama__icontains=query) |
            Q(eselon__icontains=query)
        )

    # Paginasi (10 data per halaman)
    paginator = Paginator(jabatan, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'jabatan_list': page_obj,
        'query': query,
    }
    return render(request, 'jabatan/index.html', context)

@login_required
def jabatan_import(request):
    if request.method == 'POST':
        form = ImportJabatanForm(request.POST, request.FILES)
        
        if form.is_valid():
            file = request.FILES.get('file_excel')
            
            if not file:
                messages.error(request, "File tidak ditemukan. Silakan pilih berkas Excel / CSV.")
                return render(request, 'jabatan/import_form.html', {'form': form, 'title': 'Import Master Jabatan'})

            try:
                # 1. BACA FILE EXCEL / CSV
                filename = file.name.lower()
                if filename.endswith('.csv'):
                    df = pd.read_csv(file)
                elif filename.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file)
                else:
                    messages.error(request, "Format file tidak didukung! Harus berupa .xlsx, .xls, atau .csv.")
                    return render(request, 'jabatan/import_form.html', {'form': form, 'title': 'Import Master Jabatan'})

                # 2. BERSIHKAN & VALIDASI HEADER KOLOM
                df.columns = df.columns.astype(str).str.strip().str.lower()
                df = df.fillna('')

                # Validasi Kolom Wajib
                if 'nama_jabatan' not in df.columns or 'jenis' not in df.columns:
                    messages.error(
                        request, 
                        f"Gagal: Kolom 'nama_jabatan' dan 'jenis' wajib ada! Header terbaca: {list(df.columns)}"
                    )
                    return render(request, 'jabatan/import_form.html', {'form': form, 'title': 'Import Master Jabatan'})

                created_count = 0
                updated_count = 0
                errors = []

                # 3. PROSES SETIAP BARIS EXCEL
                for index, row in df.iterrows():
                    baris_ke = index + 2
                    nama_jabatan = str(row.get('nama_jabatan', '')).strip()
                    jenis_nama = str(row.get('jenis', '')).strip()
                    jenjang_nama = str(row.get('jenjang', '')).strip()
                    eselon = str(row.get('eselon', '')).strip() or None

                    if not nama_jabatan or not jenis_nama:
                        errors.append(f"Baris {baris_ke}: Nama jabatan atau Jenis Jabatan kosong, dilewati.")
                        continue

                    try:
                        # Find or Create Foreign Key: JenisJabatan
                        jenis_obj, _ = JenisJabatan.objects.get_or_create(nama=jenis_nama)

                        # Find or Create Foreign Key: JenjangJabatan (opsional)
                        jenjang_obj = None
                        if jenjang_nama:
                            jenjang_obj, _ = JenjangJabatan.objects.get_or_create(nama=jenjang_nama)

                        # Update or Create Jabatan
                        jabatan_obj, created = Jabatan.objects.update_or_create(
                            nama_jabatan=nama_jabatan,
                            jenis=jenis_obj,
                            jenjang=jenjang_obj,
                            defaults={
                                'eselon': eselon,
                                'is_active': True
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                    except Exception as err_row:
                        errors.append(f"Baris {baris_ke} ({nama_jabatan}): {str(err_row)}")

                # REKAP PESAN KESUKSESAN & WARNING
                if created_count > 0 or updated_count > 0:
                    msg = f"Import Berhasil! {created_count} jabatan baru dibuat, {updated_count} diperbarui."
                    messages.success(request, msg)

                if errors:
                    for err in errors[:5]:
                        messages.warning(request, err)
                    if len(errors) > 5:
                        messages.warning(request, f"...dan {len(errors) - 5} error lainnya.")

                return redirect('jabatan_list')

            except Exception as e:
                print("--- ERROR SYSTEM IMPORT JABATAN ---")
                traceback.print_exc()
                messages.error(request, f"Terjadi kesalahan teknis saat membaca file: {str(e)}")
        else:
            for field, err_list in form.errors.items():
                for err in err_list:
                    messages.error(request, f"Error Form ({field}): {err}")

    else:
        form = ImportJabatanForm()

    return render(request, 'jabatan/import_form.html', {'form': form, 'title': 'Import Master Jabatan'})