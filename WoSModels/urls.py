from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),

    path('auth/signup/', views.signup_view, name='signup'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/<int:slot_id>/', views.upload_to_slot, name='upload_to_slot'),
    path('slot/create/', views.create_slot, name='create_slot'),
    path('slot/<int:slot_id>/delete/', views.delete_slot_zip, name='delete_slot_zip'),

    path('worlds/', views.worlds_index, name='worlds_index'),
    path('worlds/<slug:slug>.zip', views.serve_world_zip, name='serve_world_zip'),
    path('api/worlds/', views.api_world_list, name='api_world_list'),

    # Non primary additions
    path('atheliasquest/', views.athelias_quest, name='athelias_quest'),

]
