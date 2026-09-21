from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import TingkatPendidikan
from .forms import TingkatPendidikanForm

# READ
@login_required
def tingkat_pendidikan_list(request):
    data_list = TingkatPendidikan.objects.all().order_by('urutan')
    return render(request, 'pendidikan/index.html', {
        'data_list': data_list,
        'title': 'Master Tingkat Pendidikan'
    })

# CREATE
@login_required
def tingkat_pendidikan_create(request):
    if request.method == 'POST':
        form = TingkatPendidikanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data tingkat pendidikan berhasil ditambahkan!')
            return redirect('tingkat_pendidikan_list')
    else:
        form = TingkatPendidikanForm()
    
    return render(request, 'pendidikan/form.html', {
        'form': form,
        'title': 'Tambah Tingkat Pendidikan'
    })

# UPDATE
@login_required
def tingkat_pendidikan_update(request, pk):
    obj = get_object_or_404(TingkatPendidikan, pk=pk)
    if request.method == 'POST':
        form = TingkatPendidikanForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data tingkat pendidikan berhasil diperbarui!')
            return redirect('tingkat_pendidikan_list')
    else:
        form = TingkatPendidikanForm(instance=obj)
        
    return render(request, 'pendidikan/form.html', {
        'form': form,
        'title': 'Edit Tingkat Pendidikan'
    })

# DELETE
@login_required
def tingkat_pendidikan_delete(request, pk):
    obj = get_object_or_404(TingkatPendidikan, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Data tingkat pendidikan berhasil dihapus!')
    return redirect('tingkat_pendidikan_list')