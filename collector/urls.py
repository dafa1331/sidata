from django.urls import path
from . import views

urlpatterns = [
    path('', views.portal_upload, name='portal_upload'),
    path('admin-rekap/', views.admin_rekap_view, name='admin_rekap'), # <--- Rute halaman rekap admin

    # Rute Kelola Jenis Dokumen
    path('admin-rekap/dokumen/', views.admin_jenis_dokumen_list, name='admin_jenis_dokumen'),
    path('admin-rekap/dokumen/<int:pk>/hapus/', views.admin_jenis_dokumen_delete, name='admin_jenis_dokumen_delete'),

    path('rekap/excel/', views.export_rekap_excel, name='export_rekap_excel'),
    path('rekap/zip/', views.download_bulk_zip, name='download_bulk_zip'),
    path('rekap/zip/<str:opd_name>/', views.download_bulk_zip, name='download_bulk_zip_opd'),
]
