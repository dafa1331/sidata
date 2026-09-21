from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'),name='login'),

    path('logout/', auth_views.LogoutView.as_view(),name='logout'),

    # path(
    #     'dashboard/',
    #     views.dashboard,
    #     name='dashboard'
    # ),

    path('users/', views.user_list, name='user_list'),
    path('users/tambah/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_update, name='user_update'),
    path('users/<int:pk>/hapus/', views.user_delete, name='user_delete'),
]