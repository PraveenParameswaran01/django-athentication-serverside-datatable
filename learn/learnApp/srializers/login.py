from rest_framework import serializers
from learnApp.models import *
from django.contrib.auth import authenticate

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        label=("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        max_length=125,
        write_only=True
    )

    class Meta:
        model = masUser
        fields = ['user_name','email', 'password', 'mobile_number']

    def create(self, validated_data):
        user = masUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            user_name=validated_data['user_name'],
            mobile_number=validated_data['mobile_number']
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    user_name = serializers.CharField(max_length=100)
    password = serializers.CharField(
        label=("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        max_length=125,
        write_only=True
    )

    class Meta:
        model = masUser
        fields = ['id', 'user_name', 'password']

    def validate(self, data):
        user_name = data.get('user_name')
        password = data.get('password')

        if user_name and password:
            if masUser.objects.filter(user_name=user_name).exists():
                user = authenticate(request=self.context.get('request'), user_name=user_name, password=password)
               
            else:
                message = 'Invalid Credentials'
                raise serializers.ValidationError(
                    {'Message':message}, code='authorization')
        else:
            message = ('Must include "Username" and "Password"')
            raise serializers.ValidationError({'Message':message}, code='authorization')

        data['user'] = user
        return data

        

