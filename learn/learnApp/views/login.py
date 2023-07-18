from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from learnApp.srializers.login import *
from knox.models import AuthToken
from django.shortcuts import render, redirect


def home(request):
    return render(request, 'mypanel/login/register.html')

def user_register(request):
    if request.method == 'POST':
        serializer = UserRegisterSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            return render(request, 'mypanel/login/register.html')
        
def user_login(request):
    if request.method == 'POST':
        serializer = UserLoginSerializer(data=request.POST, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token = AuthToken.objects.create(user)[1]
        request.session['user_id'] = user.id
        request.session['token'] = token
        redirect('dashboard.html')
    else:
        return render(request, 'mypanel/login/login.html')
    

def log_out(request):
    request.session.flush()
    return render(request, 'mypanel/login/register.html')
        
