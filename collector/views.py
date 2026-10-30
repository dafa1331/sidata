import os
import zipfile
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
import openpyxl
from django.urls import reverse
from django.core.files.storage import default_storage
from django.core.paginator import Paginator # Pastikan sudah di-import

# Impor model Pegawai dari app pegawai
from pegawai.models import Pegawai
from .models import JenisDokumen, BerkasPPPK


def get_opd_pegawai(pegawai_obj):
    """
    Helper function untuk mengambil nama OPD / Unit Kerja 
    dari riwayat jabatan terbaru milik pegawai.
    """
    if hasattr(pegawai_obj, 'riwayat_jabatan_set'):
        riwayat = pegawai_obj.riwayat_jabatan_set.last()
        if riwayat and riwayat.unit_kerja_id:
            return getattr(riwayat.unit_kerja_id, 'nama', '-')
    return "-"


# ================= SISI PEGAWAI / PUBLIC PORTAL =================

def portal_upload(request):
    """
    Portal loginless untuk upload berkas PPPK berdasarkan NIP & Tanggal Lahir
    """
    step = 1
    pegawai = None
    uploaded_files = {}
    jenis_docs = JenisDokumen.objects.all()

    # Cek apakah pegawai sudah verifikasi (tersimpan di session)
    pegawai_id = request.session.get('portal_pegawai_id')
    if pegawai_id:
        try:
            pegawai = Pegawai.objects.get(pk=pegawai_id)
            step = 2
        except Pegawai.DoesNotExist:
            request.session.pop('portal_pegawai_id', None)

    if request.method == 'POST':
        # 1. Aksi Verifikasi Step 1
        if 'action_verify' in request.POST:
            nip = request.POST.get('nip', '').strip()
            tgl_lahir = request.POST.get('tanggal_lahir', '').strip()

            try:
                # Validasi NIP dan Tanggal Lahir
                pegawai = Pegawai.objects.get(nip=nip, tanggal_lahir=tgl_lahir)
                request.session['portal_pegawai_id'] = pegawai.id
                step = 2
                messages.success(request, f"Verifikasi berhasil. Selamat datang, {pegawai.nama_lengkap}!")
            except Pegawai.DoesNotExist:
                messages.error(request, "NIP atau Tanggal Lahir tidak ditemukan / tidak sesuai!")

        # 2. Aksi Logout / Ganti Pegawai
        elif 'action_logout' in request.POST:
            request.session.pop('portal_pegawai_id', None)
            return redirect('portal_upload')

        # 3. Aksi Upload Berkas di Step 2
        elif 'action_upload' in request.POST and pegawai:
            uploaded_count = 0
            for doc in jenis_docs:
                file_key = f'doc_{doc.id}'
                if file_key in request.FILES:
                    file_obj = request.FILES[file_key]
                    
                    # Simpan atau update berkas ke database menggunakan update_or_create
                    berkas, created = BerkasPPPK.objects.update_or_create(
                        pegawai=pegawai,
                        jenis_dokumen=doc,
                        defaults={'file': file_obj}
                    )
                    uploaded_count += 1
            
            if uploaded_count > 0:
                messages.success(request, "Berkas berhasil diunggah/diperbarui!")
            else:
                messages.warning(request, "Tidak ada file baru yang dipilih untuk diunggah.")
            
            return redirect('portal_upload')

    # Ambil dictionary file yang sudah di-upload dengan aman (pastikan filenya benar-benar ada)
    if pegawai:
        raw_berkas = BerkasPPPK.objects.filter(pegawai=pegawai)
        for b in raw_berkas:
            if b.file and hasattr(b.file, 'name') and b.file.name:
                uploaded_files[b.jenis_dokumen_id] = b

        # Ambil informasi OPD untuk ditampilkan di header portal
        nama_opd = get_opd_pegawai(pegawai)
        # Sediakan objek pegawai dengan tambahan atribut opd agar template terbaca rapi
        pegawai.opd = nama_opd
        pegawai.nama = pegawai.nama_lengkap # Jaga kompatibilitas nama

    context = {
        'step': step,
        'pegawai': pegawai,
        'jenis_docs': jenis_docs,
        'uploaded_files': uploaded_files,
    }
    return render(request, 'collector/portal.html', context)


# ================= SISI ADMIN / REKAPITULASI =================

@login_required
def admin_rekap_view(request):
    """
    Halaman Dashboard Admin Rekapitulasi Berkas PPPK dengan Server-Side Pagination
    Hanya menampilkan pegawai yang sudah mengunggah minimal 1 dokumen.
    """
    jenis_docs = JenisDokumen.objects.all()
    
    # Ambil parameter pencarian & filter dari URL
    search_query = request.GET.get('q', '').strip()
    selected_opd = request.GET.get('opd', '').strip()

    # OPTIMASI: Hanya ambil pegawai PPPK yang BERKASNYA SUDAH ADA (menggunakan Exists)
    # Ini langsung menyaring di database sehingga yang belum upload tidak ikut ter-load
    subquery_berkas = BerkasPPPK.objects.filter(pegawai=models.OuterRef('pk'))
    
    pegawai_list = Pegawai.objects.filter(
        models.Q(riwayat_kepegawaian__jenis_transaksi__icontains='pppk'),
        models.Exists(subquery_berkas)
    ).distinct().order_by('nama_lengkap')

    # Filter pencarian NIP atau Nama
    if search_query:
        pegawai_list = pegawai_list.filter(
            models.Q(nama_lengkap__icontains=search_query) | 
            models.Q(nip__icontains=search_query)
        )

    # Optimasi OPD: Jika ada filter OPD, kita lakukan pengecekan secara efisien atau 
    # jika fungsi get_opd_pegawai berupa query, kita bisa sesuaikan. 
    # Karena get_opd_pegawai adalah fungsi helper python, kita saring list-nya tapi 
    # dengan prefetch atau struktur yang lebihringan.
    rekap_list = []
    for p in pegawai_list:
        nama_opd = get_opd_pegawai(p)
        
        # Filter berdasarkan OPD jika dipilih di dropdown
        if selected_opd and selected_opd.lower() not in nama_opd.lower():
            continue
            
        rekap_list.append((p, nama_opd))

    # Konfigurasi Paginator (10 data per halaman agar ringan)
    paginator = Paginator(rekap_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Mapping berkas HANYA untuk data pegawai yang tampil di halaman aktif saja
    rekap_data = []
    for idx, (p, nama_opd) in enumerate(page_obj, start=page_obj.start_index()):
        berkas_map = {b.jenis_dokumen_id: b for b in BerkasPPPK.objects.filter(pegawai=p)}

        doc_statuses = {}
        is_complete = True
        
        for d in jenis_docs:
            if d.id in berkas_map:
                doc_statuses[d.id] = berkas_map[d.id]
            else:
                doc_statuses[d.id] = None
                if d.wajib:  
                    is_complete = False

        rekap_data.append({
            'no': idx,
            'pegawai': p,
            'opd': nama_opd,
            'is_complete': is_complete,
            'doc_statuses': doc_statuses
        })

    context = {
        'title': 'Rekapitulasi Pengumpulan Berkas PPPK',
        'rekap_data': rekap_data,
        'jenis_docs': jenis_docs,
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_opd': selected_opd,
    }
    return render(request, 'collector/admin_rekap.html', context)


@staff_member_required
def export_rekap_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekapitulasi PPPK"

    jenis_docs = list(JenisDokumen.objects.all())
    headers = ['No', 'NIP', 'Nama', 'OPD / Unit Kerja', 'Status Kelengkapan'] + [d.nama_dokumen for d in jenis_docs]
    ws.append(headers)

    pegawai_list = Pegawai.objects.all()
    for idx, p in enumerate(pegawai_list, 1):
        berkas_map = {b.jenis_dokumen_id: b for b in BerkasPPPK.objects.filter(pegawai=p)}
        nama_opd = get_opd_pegawai(p)

        doc_statuses = []
        is_complete = True
        for d in jenis_docs:
            if d.id in berkas_map:
                doc_statuses.append("Lengkap")
            else:
                doc_statuses.append("Belum")
                if d.wajib:
                    is_complete = False

        status_total = "Lengkap" if is_complete else "Belum Lengkap"
        row = [idx, p.nip, p.nama_lengkap, nama_opd, status_total] + doc_statuses
        ws.append(row)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Rekap_Pengumpulan_Dokumen_PPPK.xlsx"'
    wb.save(response)
    return response


@staff_member_required
def download_bulk_zip(request, opd_name=None):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        berkas_query = BerkasPPPK.objects.select_related('pegawai', 'jenis_dokumen')

        for b in berkas_query:
            if b.file and os.path.exists(b.file.path):
                folder_opd = get_opd_pegawai(b.pegawai)
                
                # Jika ada filter berdasarkan OPD tertentu
                if opd_name and folder_opd != opd_name:
                    continue

                arcname = os.path.join(
                    folder_opd, 
                    f"{b.pegawai.nip}_{b.pegawai.nama_lengkap}", 
                    os.path.basename(b.file.name)
                )
                zip_file.write(b.file.path, arcname)

    buffer.seek(0)
    filename = f"Berkas_PPPK_{opd_name}.zip" if opd_name else "Semua_Berkas_PPPK.zip"
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def admin_jenis_dokumen_list(request):
    """Menampilkan daftar jenis dokumen dan form tambah/edit"""
    jenis_docs = JenisDokumen.objects.all()
    
    # Jika form dikirim untuk menambah/mengedit
    if request.method == 'POST':
        doc_id = request.POST.get('doc_id')
        nama_dokumen = request.POST.get('nama_dokumen', '').strip()
        wajib = True if request.POST.get('wajib') == 'on' else False

        if nama_dokumen:
            if doc_id:
                # Mode Edit
                doc = get_object_or_404(JenisDokumen, id=doc_id)
                doc.nama_dokumen = nama_dokumen
                doc.wajib = wajib
                doc.save()
                messages.success(request, "Jenis dokumen berhasil diperbarui.")
            else:
                # Mode Tambah Baru
                JenisDokumen.objects.create(nama_dokumen=nama_dokumen, wajib=wajib)
                messages.success(request, "Jenis dokumen baru berhasil ditambahkan.")
        else:
            messages.error(request, "Nama dokumen tidak boleh kosong!")
            
        return redirect('admin_jenis_dokumen')

    context = {
        'title': 'Kelola Jenis Dokumen PPPK',
        'jenis_docs': jenis_docs,
    }
    return render(request, 'collector/admin_jenis_dokumen.html', context)


@login_required
def admin_jenis_dokumen_delete(request, pk):
    """Menghapus jenis dokumen"""
    doc = get_object_or_404(JenisDokumen, pk=pk)
    doc.delete()
    messages.success(request, "Jenis dokumen berhasil dihapus.")
    return redirect('admin_jenis_dokumen')

@login_required
def hapus_pegawai_rekap_view(request, pegawai_id):
    if request.method == 'POST':
        pegawai = get_object_or_404(Pegawai, pk=pegawai_id)
        
        # Ambil parameter query/page/opd agar posisi filter/halaman tidak hilang setelah redirect
        page = request.POST.get('page', '1')
        q = request.POST.get('q', '')
        opd = request.POST.get('opd', '')
        
        # 1. Ambil semua data berkas milik pegawai ini sebelum dihapus dari database
        berkas_list = BerkasPPPK.objects.filter(pegawai=pegawai)
        
        # 2. Hapus file fisik satu per satu dari folder penyimpanan server
        for berkas in berkas_list:
            if berkas.file and default_storage.exists(berkas.file.name):
                default_storage.delete(berkas.file.name)
        
        # 3. Hapus record data dari tabel BerkasPPPK di database
        deleted_count, _ = berkas_list.delete()
        
        nama = getattr(pegawai, 'nama_lengkap', 'Pegawai')
        if deleted_count > 0:
            messages.success(request, f"Seluruh berkas dan file fisik PPPK untuk {nama} berhasil dihapus permanen.")
        else:
            messages.warning(request, f"Tidak ada berkas ditemukan untuk pegawai {nama}.")
        
        # 4. Redirect kembali ke halaman rekap (Gunakan nama URL rute Anda, misal 'admin_rekap')
        # Pastikan tidak menggunakan awalan '/admin/rekap/' agar tidak error 404 admin django
        redirect_url = reverse('admin_rekap') # Sesuaikan dengan nama url rekap Anda, misal 'admin_rekap'
        redirect_url = f"{redirect_url}?page={page}" # Sesuaikan path URL rekap Anda
        if q:
            redirect_url += f"&q={q}"
        if opd:
            redirect_url += f"&opd={opd}"
            
        return redirect(redirect_url)
        
    return redirect('admin_rekap')