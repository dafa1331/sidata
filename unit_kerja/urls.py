from django.urls import path
from . import views

urlpatterns = [
    path('', views.unit_kerja_list, name='unit_kerja_list'),
    path('tambah/', views.unit_kerja_create, name='unit_kerja_create'),
    path('<int:pk>/edit/', views.unit_kerja_update, name='unit_kerja_update'),
    path('<int:pk>/hapus/', views.unit_kerja_delete, name='unit_kerja_delete'),
    path('import/', views.unit_kerja_import, name='unit_kerja_import'),
]