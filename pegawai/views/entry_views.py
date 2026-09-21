from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from pegawai.decorators import role_required
from pegawai.forms import EntryJabatanForm, EntryPangkatForm, EntryPendidikanForm

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