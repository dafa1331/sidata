from django.urls import path
from . import views

urlpatterns = [
    path('', views.jabatan_list, name='jabatan_list'),
    path('tambah/', views.jabatan_create, name='jabatan_create'),
    path('<int:pk>/edit/', views.jabatan_update, name='jabatan_update'),
    path('<int:pk>/hapus/', views.jabatan_delete, name='jabatan_delete'), # <-- Path Baru
    path('import/', views.jabatan_import, name='jabatan_import'),
    path('export/', views.jabatan_export, name='jabatan_export'), # <-- TAMBAHKAN RUTE INI
]