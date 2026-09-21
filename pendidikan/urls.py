from django.urls import path
from . import views

urlpatterns = [
    path('', views.tingkat_pendidikan_list, name='tingkat_pendidikan_list'),
    path('tambah/', views.tingkat_pendidikan_create, name='tingkat_pendidikan_create'),
    path('<int:pk>/edit/', views.tingkat_pendidikan_update, name='tingkat_pendidikan_update'),
    path('<int:pk>/hapus/', views.tingkat_pendidikan_delete, name='tingkat_pendidikan_delete'),
]