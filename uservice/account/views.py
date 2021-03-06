from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from .models import Category, Photo, Post
from django.contrib.auth.decorators import login_required
from nltk.sentiment import SentimentIntensityAnalyzer

from .forms import CreateUserForm, PostForm


def register_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse_lazy('account:gallery'))
    else:
        form = CreateUserForm()
        success_url = reverse_lazy('account:login')
        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                form.save()
                user = form.cleaned_data.get('username')
                messages.success(request, 'Account was created for ' + user)
                return HttpResponseRedirect(success_url)

        context = {'form': form}
        return render(request, 'register.html', context)


def login_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse_lazy('account:gallery'))
    else:
        success_url = reverse_lazy('account:gallery')
        failure_url = reverse_lazy('account:login')
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return HttpResponseRedirect(success_url)
            else:
                messages.info(request, 'Username or password is incorrect')
                return HttpResponseRedirect(failure_url)
        context = {}
        return render(request, 'login.html', context)


def logout_page(request):
    success_url = reverse_lazy('account:login')
    logout(request)
    return HttpResponseRedirect(success_url)


@login_required(login_url='account:login')
def gallery(request):
    user = request.user
    category = request.GET.get('category')
    if category == None:
        photos = Photo.objects.all()
    else:
        photos = Photo.objects.filter(
            category__name=category, category__user=user)
    photo_scores = {}
    for photo in photos:
        posts = Post.objects.filter(photo=photo).order_by('-date_posted').all()
        sia = SentimentIntensityAnalyzer()
        scores = {'negative': 0, 'positive': 0, 'neutral': 0}
        for post in posts:
            score = sia.polarity_scores(str(post))
            maximum = max(score['neg'], score['neu'], score['pos'])
            if maximum == score['neg']:
                scores['negative'] += 1
            if maximum == score['neu']:
                scores['neutral'] += 1
            if maximum == score['pos']:
                scores['positive'] += 1
        if photo.id not in photo_scores.keys():
            photo_scores[photo.id] = scores
    categories = Category.objects.filter(user=user)
    context = {'categories': categories, 'photos': photos, 'scores': photo_scores}
    return render(request, 'gallery.html', context)


@login_required(login_url='account:login')
def viewPhoto(request, pk):
    photo = Photo.objects.get(id=pk)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.photo = photo
            post.save()
            return HttpResponseRedirect(request.path_info)
    else:
        form = PostForm()
    posts = Post.objects.filter(photo=photo).order_by('-date_posted').all()
    sia = SentimentIntensityAnalyzer()
    post_score = {}
    for post in posts:
        score = sia.polarity_scores(str(post))
        maximum = max(score['neg'], score['neu'], score['pos'])
        if maximum == score['neg']:
            post_score[post.id] = -1
        if maximum == score['neu']:
            post_score[post.id] = 0
        if maximum == score['pos']:
            post_score[post.id] = 1
    context = {'form': form, 'posts': posts, 'photo': photo, 'post_score': post_score}
    return render(request, 'photo.html', context)


@login_required(login_url='login')
def addPhoto(request):
    user = request.user

    categories = user.category_set.all()

    if request.method == 'POST':
        data = request.POST
        images = request.FILES.getlist('images')

        if data['category'] != 'none':
            category = Category.objects.get(id=data['category'])
        elif data['category_new'] != '':
            category, created = Category.objects.get_or_create(
                user=user,
                name=data['category_new'])
        else:
            category = None

        for image in images:
            photo = Photo.objects.create(
                category=category,
                description=data['description'],
                image=image,
            )

        return redirect('account:gallery')

    context = {'categories': categories}
    return render(request, 'add.html', context)
