from django.shortcuts import render
from django.http import JsonResponse
import json
from learnApp.datatable import DataTablesServer
from learnApp.models import masUser
from learnApp.srializers.userslist import userSerializer

def users_list(request):

    data_table=dict(request.GET)
    datatable = json.dumps(data_table)

    queryset = masUser.objects.all()

    serializer_class=userSerializer

    searchField=['id','user_name']
    columns=['id','user_name']
    result = DataTablesServer(datatable=data_table, columns=columns, qs=queryset,
                searchField=searchField,serializer=serializer_class,request = request).output_result()
    return JsonResponse(result, safe=False)
   