from rest_framework import serializers
from learnApp.models import masUser


class userSerializer(serializers.ModelSerializer):
    class Meta:
        model = masUser
        fields = ['id', 'user_name', 'mobile_number', 'email']