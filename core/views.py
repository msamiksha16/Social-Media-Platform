from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, PostForm, CommentForm
from .models import Post, Comment, Like
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from .models import Profile, User
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.http import HttpResponseRedirect

from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification

@login_required
def feed(request):
    # Handle post creation
    if request.method == 'POST' and 'post_submit' in request.POST:
        content = request.POST.get('content')
        image = request.FILES.get('image')
        if content or image:
            Post.objects.create(author=request.user, content=content, image=image)
        return redirect('feed')

    # Handle comment creation
    if request.method == 'POST' and 'comment_submit' in request.POST:
        post_id = request.POST.get('post_id')
        content = request.POST.get('content')
        if post_id and content:
            post = Post.objects.get(id=post_id)
            Comment.objects.create(post=post, author=request.user, content=content)
        return redirect('feed')

    # Handle like/unlike
    if request.method == 'POST' and 'like_submit' in request.POST:
        post_id = request.POST.get('post_id')
        post = Post.objects.get(id=post_id)
        existing_like = Like.objects.filter(post=post, user=request.user)
        if existing_like.exists():
            existing_like.delete()
        else:
            Like.objects.create(post=post, user=request.user)
        return redirect('feed')

    # Get all posts
    posts = Post.objects.all().order_by('-created_at')

    # Annotate posts with flags for template
    for post in posts:
        # Whether the current user liked this post
        post.liked_by_user = Like.objects.filter(post=post, user=request.user).exists()
        # Total number of likes
        post.total_likes = Like.objects.filter(post=post).count()

    return render(request, 'core/feed.html', {'posts': posts})


def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('feed')
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('feed')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})
  

def like_post(request):
    if request.method == "POST":
        post_id = request.POST.get("post_id")
        post = Post.objects.get(id=post_id)
        user = request.user

        liked = False
        like_obj, created = Like.objects.get_or_create(post=post, user=user)
        if not created:
            # If already liked, remove like
            like_obj.delete()
        else:
            liked = True

        total_likes = post.likes.count()
        return JsonResponse({"liked": liked, "total_likes": total_likes})


@login_required
def profile_view(request, username):
    user = get_object_or_404(User, username=username)

    # Ensure a Profile exists
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == "POST" and request.user == user:
        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']
            profile.save()
            return redirect('profile', username=username)

    posts = user.post_set.all().order_by('-created_at')
    return render(request, 'core/profile.html', {'profile': profile, 'posts': posts})


@login_required
def edit_profile_image(request):
    if request.method == "POST" and request.FILES.get("profile_image"):
        # Ensure the user can only edit their own profile
        profile = request.user.profile
        profile.profile_image = request.FILES["profile_image"]
        profile.save()
    return redirect("profile", username=request.user.username)



# Signal to create profile for new users (no change needed)
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


def logout_view(request):
    logout(request)
    return redirect('login')

def feed_view(request):
    posts = Post.objects.all().order_by('-created_at')
    profiles = Profile.objects.filter(user__in=[post.author for post in posts])
    context = {
        'posts': posts,
        'profiles': profiles,
    }
    return render(request, 'feed.html', context)

# core/views.py
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

def follow_toggle(request, user_id):
    current_user = request.user
    target_user = User.objects.get(id=user_id)

    logger.info(f"🚀 follow_toggle called! {current_user.username} -> {target_user.id}")

    if current_user in target_user.profile.followers.all():
        target_user.profile.followers.remove(current_user)
        following = False
        logger.info(f"{current_user.username} unfollowed {target_user.username}")
    else:
        target_user.profile.followers.add(current_user)
        following = True
        logger.info(f"{current_user.username} followed {target_user.username}")

        # Send notification to target user
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{target_user.id}",
            {
                "type": "send_notification",
                "text": f"{current_user.username} followed you!"
            }
        )
        logger.info(f"Notification sent to group notifications_{target_user.id}")
    
    return JsonResponse({
        "following": following,
        "followers_count": target_user.profile.followers.count()
    })

    
@login_required
def my_posts(request):
    posts = Post.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'core/my_posts.html', {'posts': posts})


@login_required
def search_view(request):
    query = request.GET.get('q', '')
    posts = Post.objects.filter(content__icontains=query).order_by('-created_at')
    users = User.objects.filter(username__icontains=query)
    
    return render(request, 'core/search_results.html', {
        'query': query,
        'posts': posts,
        'users': users
    })

@login_required
def live_search(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        users = User.objects.filter(username__icontains=query)[:5]  # Limit to top 5
        for u in users:
            results.append({
                "username": u.username,
                "full_name": f"{u.first_name} {u.last_name}".strip()
            })
    return JsonResponse({"results": results})