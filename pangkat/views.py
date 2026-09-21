from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, ProtectedError
from .models import Pangkat
from .forms import PangkatForm

# 1. READ (List, Search & Pagination)
@login_required
def pangkat_list(request):
    query = request.GET.get('q', '').strip()
    pangkat_qs = Pangkat.objects.all()

    if query:
        pangkat_qs = pangkat_qs.filter(
            Q(golongan__icontains=query) |
            Q(nama_pangkat__icontains=query)
        )

    paginator = Paginator(pangkat_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'pangkat/index.html', {
        'pangkat_list': page_obj,
        'query': query
    })

# 2. CREATE
@login_required
def pangkat_create(request):
    if request.method == 'POST':
        form = PangkatForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Master pangkat berhasil ditambahkan.')
            return redirect('pangkat_list')
    else:
        form = PangkatForm()
    return render(request, 'pangkat/form.html', {'form': form, 'title': 'Tambah Master Pangkat'})

# 3. UPDATE
@login_required
def pangkat_update(request, pk):
    pangkat = get_object_or_404(Pangkat, pk=pk)
    if request.method == 'POST':
        form = PangkatForm(request.POST, instance=pangkat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Master pangkat berhasil diperbarui.')
            return redirect('pangkat_list')
    else:
        form = PangkatForm(instance=pangkat)
    return render(request, 'pangkat/form.html', {'form': form, 'title': 'Edit Master Pangkat'})

# 4. DELETE
@login_required
def pangkat_delete(request, pk):
    pangkat = get_object_or_404(Pangkat, pk=pk)
    if request.method == 'POST':
        try:
            pangkat.delete()
            messages.success(request, f'Pangkat "{pangkat.nama_pangkat} ({pangkat.golongan})" berhasil dihapus.')
        except ProtectedError:
            messages.error(request, f'Gagal menghapus! Pangkat "{pangkat.golongan}" masih digunakan pada data riwayat pegawai.')
        return redirect('pangkat_list')
        
    return render(request, 'pangkat/delete_confirm.html', {'pangkat': pangkat})