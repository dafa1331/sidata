from django.urls import path
from . import views

urlpatterns = [
    path('', views.pangkat_list, name='pangkat_list'),
    path('tambah/', views.pangkat_create, name='pangkat_create'),
    path('<int:pk>/edit/', views.pangkat_update, name='pangkat_update'),
    path('<int:pk>/hapus/', views.pangkat_delete, name='pangkat_delete'),
]