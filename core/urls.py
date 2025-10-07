from django.urls import path
from . import views

urlpatterns = [
    path('', views.feed, name='feed'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('like/', views.like_post, name='like_post'),  # AJAX endpoint
    path('profile/<str:username>/', views.profile_view, name='profile'),
    
    path('follow-toggle/<int:user_id>/', views.follow_toggle, name='follow_toggle'),
    path('my-posts/', views.my_posts, name='my_posts'),
    path('edit-profile-image/', views.edit_profile_image, name='edit_profile_image'),
    path('search/', views.search_view, name='search'),
    
    path('live-search/', views.live_search, name='live_search'),



    
]
