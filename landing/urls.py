from django.urls import path
from . import views

urlpatterns = [
    # Mengarahkan halaman utama landing page ke view 'index'
    path('', views.index, name='landing_index'),
]