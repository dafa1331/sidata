"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# from django.contrib import admin
# from django.urls import include, path
# from django.shortcuts import redirect


# def home(request):
#     return redirect("login")


# urlpatterns = [
#     path("", home, name="home"),

#     path("admin/", admin.site.urls),
#     path("dashboard/", include("dashboard.urls")),
#     path("accounts/", include("accounts.urls")),
#     path("pegawai/", include("pegawai.urls")),
#     path("jabatan/", include("jabatan.urls")),
#     path("unit_kerja/", include("unit_kerja.urls")),
#     path("pangkat/", include("pangkat.urls")),
#     path("pendidikan/", include("pendidikan.urls")),
#     path("dashboard/", include("dashboard.urls")),
# ]

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # 1. LANDING PAGE HALAMAN UTAMA (http://localhost:8000/)
    path("", include("landing.urls")),

    # 2. PANEL ADMIN & APP INTERNAL
    path("admin/", admin.site.urls),
    path("dashboard/", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("pegawai/", include("pegawai.urls")),
    path("jabatan/", include("jabatan.urls")),
    path("unit_kerja/", include("unit_kerja.urls")),
    path("pangkat/", include("pangkat.urls")),
    path("pendidikan/", include("pendidikan.urls")),
]
