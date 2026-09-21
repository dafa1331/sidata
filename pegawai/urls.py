from django.urls import path
from . import views
from pegawai.views.proyeksi_views import proyeksi_habis_kontrak_view

urlpatterns = [
    # Master Pegawai
    path('', views.pegawai_list, name='pegawai_list'),
    path('tambah/', views.pegawai_create, name='pegawai_create'),
    path('<int:pk>/edit/', views.pegawai_update, name='pegawai_update'),
    path('<int:pk>/detail/', views.pegawai_detail, name='pegawai_detail'),
    path('<int:pk>/hapus/', views.pegawai_delete, name='pegawai_delete'),
    
    # Riwayat Kepegawaian
    path('<int:pegawai_id>/riwayat-kepegawaian/tambah/', views.riwayat_kepegawaian_create, name='riwayat_kepegawaian_create'),
    path('riwayat-kepegawaian/<int:pk>/edit/', views.riwayat_kepegawaian_update, name='riwayat_kepegawaian_update'), # <-- Tambahkan ini
    path('riwayat-kepegawaian/<int:pk>/hapus/', views.riwayat_kepegawaian_delete, name='riwayat_kepegawaian_delete'),
    
    # Import
    path('import/', views.pegawai_import, name='pegawai_import'),

    # Riwayat Jabatan
    path('<int:pegawai_id>/riwayat-jabatan/tambah/', views.riwayat_jabatan_create, name='riwayat_jabatan_create'),
    path('riwayat-jabatan/<int:pk>/edit/', views.riwayat_jabatan_update, name='riwayat_jabatan_update'),
    path('riwayat-jabatan/<int:pk>/hapus/', views.riwayat_jabatan_delete, name='riwayat_jabatan_delete'),
    path('riwayat-jabatan/pelantikan-massal/', views.pelantikan_massal, name='pelantikan_massal'),

    path('api/jabatan/<int:jabatan_id>/detail/', views.get_detail_jabatan_api, name='api_detail_jabatan'),

    path('riwayat-jabatan/import/', views.riwayat_jabatan_import, name='riwayat_jabatan_import'),

    #url riwayat pangkat
    path('<int:pegawai_id>/riwayat-pangkat/tambah/', views.riwayat_pangkat_create, name='riwayat_pangkat_create'),
    path('riwayat-pangkat/<int:pk>/edit/', views.riwayat_pangkat_update, name='riwayat_pangkat_update'),
    path('riwayat-pangkat/<int:pk>/hapus/', views.riwayat_pangkat_delete, name='riwayat_pangkat_delete'),
    path('riwayat-pangkat/import/', views.riwayat_pangkat_import, name='riwayat_pangkat_import'),

    #url riwayat pendidikan
    path('<int:pegawai_id>/riwayat-pendidikan/tambah/', views.riwayat_pendidikan_create, name='riwayat_pendidikan_create'),
    path('riwayat-pendidikan/<int:pk>/edit/', views.riwayat_pendidikan_update, name='riwayat_pendidikan_update'),
    path('riwayat-pendidikan/<int:pk>/hapus/', views.riwayat_pendidikan_delete, name='riwayat_pendidikan_delete'),
    path('riwayat-pendidikan/import/', views.riwayat_pendidikan_import, name='riwayat_pendidikan_import'),

    path('layanan/jabatan/input/', views.riwayat_jabatan_entry, name='riwayat_jabatan_entry'),
    path('layanan/pangkat/input/', views.riwayat_pangkat_entry, name='riwayat_pangkat_entry'),
    path('layanan/pendidikan/input/', views.riwayat_pendidikan_entry, name='riwayat_pendidikan_entry'),

    path('pensiun/proyeksi/', views.proyeksi_pensiun_view, name='proyeksi_pensiun'),
    path('pensiun/<int:pegawai_id>/eksekusi/', views.eksekusi_pensiun_action, name='eksekusi_pensiun'),

    path('laporan/', views.laporan_kepegawaian_view, name='laporan_kepegawaian'),
    path('laporan/export-pdf/', views.export_laporan_pdf, name='export_laporan_pdf'),

    path('proyeksi-habis-kontrak/', proyeksi_habis_kontrak_view, name='proyeksi_habis_kontrak'),
]