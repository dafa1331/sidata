from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserManagementForm


@login_required
def dashboard(request):
    return render(request, 'dashboard/dashboard.html')

# LIST USER
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'accounts/user_list.html', {'users': users, 'title': 'Manajemen Akun Pengguna'})

# TAMBAH USER
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_create(request):
    if request.method == 'POST':
        form = UserManagementForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            
            # Penetapan Group/Role
            selected_role = form.cleaned_data.get('role')
            if selected_role:
                user.groups.clear()
                user.groups.add(selected_role)

            messages.success(request, f"Akun pengguna {user.username} berhasil dibuat.")
            return redirect('user_list')
    else:
        form = UserManagementForm()

    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Tambah Akun Pengguna Baru'})

# EDIT USER
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_update(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserManagementForm(request.POST, instance=user_obj)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()

            # Update Group/Role
            selected_role = form.cleaned_data.get('role')
            if selected_role:
                user.groups.clear()
                user.groups.add(selected_role)

            messages.success(request, f"Akun pengguna {user.username} berhasil diperbarui.")
            return redirect('user_list')
    else:
        form = UserManagementForm(instance=user_obj)

    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'Edit Akun: {user_obj.username}'})

# HAPUS USER
@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f"Akun pengguna {username} berhasil dihapus.")
        return redirect('user_list')
    return redirect('user_list')

