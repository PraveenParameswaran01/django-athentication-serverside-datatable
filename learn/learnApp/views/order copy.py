# ---rest-----
from knox.auth import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework import status
# other ----pakages-----
from num2words import num2words
from io import BytesIO


from django.core.files import File
from datetime import date, datetime
from django.db.models import RestrictedError,Prefetch
from django.conf import settings
from django.db import transaction
from BigBrother.datatable import DataTablesServer
from BigBrother.functions import *
from BigBrother.models import *
from BigBrother.serializers.masters import *
from BigBrother.views.common import Log
from BigBrother.serializers.order import *
from .utils import render_to_pdf
from  BigBrother.views.mail_fcm_functions import send_mail,send_notification_orderplaced,send_notification
import json,traceback
# ----mas Models--

# ----------Global Variable -------------



dt = datetime.now()

bblogo = settings.BB_INTL_LOGO
bbfooter = settings.BB_FOOTER

class RazorpayPrefill(APIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'RazorpayPrefill'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            User_data=User.objects.get(id=user_id)
            serializer=RazorpayPrefillSerializer(User_data)
            return Response(serializer.data)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST) 

class OrderAPI(generics.ListCreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    def post(self, request, *args, **kwargs):
        Transactionname = 'Order'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            order_serializer = OrderSerializer(data=request.data, context={'request': request})
            OrderDetails = request.POST.get('OrderDet')    
            dict_order =(json.loads(OrderDetails))
            if order_serializer.is_valid():
                try:
                    with transaction.atomic():
                        order_serializer.save()
                        data=order_serializer.data
                        order_id=data.get('Order_Id')
                        FromUser_Id=data.get('User_Id')
                        ToUser_Id=data.get('To_User_Id')
                        status_id = data.get('Status_Id')
                        Transaction_Amount=data.get('Transaction_Amount')
                        total_netweight=0
                        
                        
                        """ Order details table creation """
                        for det in dict_order:
                            weight = Product.objects.get(Product_Id=det['Product_Id']).NetWeight
                            total_netweight+=weight
                            wholesale_price = Product.objects.get(Product_Id=det['Product_Id']).Wholesale_Price
                            OrderDet.objects.create(Order_Id_id=order_id,Product_Id_id=det['Product_Id'],Tax_Id_id=det['Tax_Id'],Qty=det['Qty'],CGST=det['CGST'],CGST_Amount=det['CGST_Amount']
                            ,SGST=det['SGST'],SGST_Amount=det['SGST_Amount'],IGST=det['IGST'],IGST_Amount=det['IGST_Amount'],Tax_Amount=det['TaxAmount'],Rate=det['Rate'],Discount_Amount=det['Discount_Amount']
                            ,DiscountPer=det['DiscountPer'],Amount=det['Amount'],NetAmount=det['NetAmount'],Unit_Id_id=det['Unit_Id'],Wholesale_Rate=wholesale_price)
                        
                        #Commission Calculation :
                        order_det_list = list(OrderDet.objects.filter(Order_Id_id=order_id).values_list('OrderDet_Id',flat=True))
            
                        payment_commission = 0  
                        for order_det in order_det_list:
                            wholesale = OrderDet.objects.get(OrderDet_Id=order_det).Wholesale_Rate
                            order_rate = OrderDet.objects.get(OrderDet_Id=order_det).Rate
                            qty = OrderDet.objects.get(OrderDet_Id=order_det).Qty
                            total = (order_rate - wholesale) * qty
                            
                            payment_commission+=total
                
                        """ paymenthistory creation """
                        
                        PaymentHistory.objects.create(Order_Id_id=order_id,FromUser_Id_id=FromUser_Id,ToUser_Id_id=ToUser_Id,
                                                    Total_Amount=Transaction_Amount,Commission_Amount=payment_commission)
                        
                        is_success = True 

                except Exception as e:
                    msg = {'status': 'something went wrong',
                    'message': e}
                    Log(Transactionname, msg, Mode, Ip,user_id)
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                        
                        
                if is_success:
                    try:
                        with transaction.atomic():
                            
                            """ Razorpay id generation """
                            razorpay_order=RazorpayOrder(Transaction_Amount)
                            Razorpay_Gen_orderid=razorpay_order.get('id')
                            Razorpay_amount=razorpay_order.get('amount')
                            Razorpay_currency=razorpay_order.get('currency')
                            data['Razorpay_amount']=Razorpay_amount
                            data['Razorpay_currency']=Razorpay_currency
                            data['Razorpay_Generated_Order_Id']=Razorpay_Gen_orderid
                        
                            """ Order no generation """
                            Order_no = generate_orderno(order_id)
                        

                            Order.objects.filter(Order_Id=order_id).update(Order_No=Order_no,Razorpay_Generated_Order_Id=Razorpay_Gen_orderid)
                            total_discount_amt = OrderDet.objects.filter(Order_Id_id=order_id).aggregate(Sum('Discount_Amount'))['Discount_Amount__sum']
                            Order.objects.filter(Order_Id=order_id).update(Total_Discount_Amount=total_discount_amt,Total_NetWeight=total_netweight)
                            
                            """" creating a order history row """
                            OrderHistory.objects.create(Order_Id_id=order_id,User_Id_id=ToUser_Id,Status_Id_id=status_id)
        
                            return Response(data,status.HTTP_201_CREATED)
                    
                    except Exception as e:
                        msg = {'status': 'something went wrong while generating razorpayid',
                        'message': e}
                        Log(Transactionname, msg, Mode, Ip,user_id)
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                    
            else:
                msg = {'status': status.HTTP_400_BAD_REQUEST,
                    'message': order_serializer.errors}
                Log(Transactionname, msg, Mode, Ip,user_id)
                return Response(order_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST) 
    
      



class UpdateOrderPaymentStatusAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated] 
    
    def put(self,request,*arg,**kwarg):
        Transactionname = 'UpdateOrderPaymentStatus'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            order_id=request.query_params.get('order_id')
            is_app=request.query_params.get('is_app')
            up_data=Order.objects.get(Order_Id=order_id)
            transaction_status = request.data['Transaction_Status']
            serializer=UpdateOrderStatusSerializer(up_data,data=request.data)  
            if serializer.is_valid():
                
                """ If transaction status is success if condition will get triggered  """
                if transaction_status == '11':
                    try:
                        with transaction.atomic():
                            serializer.save()
                            order_no = serializer.data.get('Order_No')
                        
                            """  Generating Invoice number from adminconfig table """
                            Invoice_no,orderid=generate_invoiceno()
                            
                            """ Updating Invoice no in Order table """
                            Order.objects.filter(Order_Id=order_id).update(Invoice_No=Invoice_no)
                            nxt_order_id = orderid + 1
                            
                            """ Updating next Invoice no in Adminconfig """
                            AdminConfig.objects.update(Invoice_Live=nxt_order_id)
                        
                            """ If payment successfull cart gets deleted for the user  """
                            if is_app:
                                Cart.objects.filter(User_Id_id=user_id).delete() 
                    
                    except Exception as e:    
                        message = 'order:{order_id},error:{e}'.format(order_id=order_id,e=e)
                        msg = {'status':'Error has occurred while saving serializer',
                                'message': message}
                        Log(Transactionname, msg, Mode, Ip, user_id)   
                        
                        transaction_response="Payment Success"
                        """ Changing transaction status from success to transaction failed """
                        Order.objects.filter(Order_Id=order_id).update(Transaction_Status=21,Transaction_Response=transaction_response)
                        return Response(msg,status=status.HTTP_400_BAD_REQUEST)
                        
                    
        
                    try:
                        with transaction.atomic():                            
                            '''
                            If Payment is successfull pdf will generate and 
                            save in database
                            
                            '''        
                            queryset  = Order.objects.get(Order_Id=order_id)
                            serializer = OrderViewDownloadSerializer(queryset,context={'request':request})
                            str_data = json.dumps(serializer.data)
                            dict_data = json.loads(str_data)
                            orderdata = dict_data
                            grandtotal = float(orderdata['Grand_Total'])
                            
                            """ Converting number to words using num2words package """
                            total_in_words = (num2words(grandtotal,lang='en').title())       
                            order = Order.objects.get(Order_Id=order_id)
                            
                            """ Generating a pdf with data and stored in database """
                            pdf = render_to_pdf(orderdata,total_in_words,bblogo,bbfooter)
                            invno = order.Invoice_No
                            filename = f"{invno}.pdf" 
                            order.Invoice_Pdf.save(filename, File(BytesIO(pdf.content)))
                            
                            """ Status 20 for invoice successfully generared """
                            Order.objects.filter(Order_Id=order_id).update(Invoice_Status=20)
                        
                            is_success = True
                    
                    except Exception as e:    
                        message = 'order:{order_id},error:{e}'.format(order_id=order_id,e=e)
                        msg = {'status':'Error has occurred while saving invoicepdf',
                                'message': message}
                        Log(Transactionname, msg, Mode, Ip, user_id)      
                        return Response(msg,status=status.HTTP_400_BAD_REQUEST) 
                        
                    if is_success:        
                        Order_from_user_acctype = User.objects.get(id=Order.objects.get(Order_Id=order_id).User_Id_id).AccountType_Id_id
                        order_to_user_acctype = User.objects.get(id=Order.objects.get(Order_Id=order_id).To_User_Id_id).AccountType_Id_id
                        
                        if Order_from_user_acctype == 1:
                            
                            """ Mail """
                            """ If admin places an order admin receives mail """ 
                            try:
                                order_from_id = User.objects.get(id=Order.objects.get(Order_Id=order_id).User_Id_id).id
                            except:
                                order_from_id=''
                            try:
                                email_type = "2"
                                order_to_id= User.objects.get(id=Order.objects.get(Order_Id=order_id).To_User_Id_id).id
                                order_no = Order.objects.get(Order_Id=order_id).Order_No
                                send_mail(email_type,order_from_id,order_no=order_no,order_to_user_id=order_to_id)
                            except Exception as e:
                                message = {'status': 'While sending mail to {},error has occured'.format(order_from_id),
                                        'message':  e}
                                Log(Transactionname, message, Mode, Ip)
                        
                            
                            """ Notification """
                            """ Notification will be received to the user who is placing the order   """
                            if Notification.objects.filter(NotificationType_Id=3).exists():
                                try:
                                    status_id = '1'
                                    new_order_receieved_index = 1
                                    fcm_user_id = Order.objects.get(Order_Id=order_id).To_User_Id_id
                                    dataobject={
                                        "Screen" : "Receivedorder",
                                        "Order_id" :'{}'.format(order_id),
                                        }
                                    send_notification_orderplaced(order_id,status_id,new_order_receieved_index,fcm_user_id,dataobject)
                                except Exception as e:    
                                    message = 'order:{order_id},error:{e}'.format(order_id=order_id,e=e)
                                    msg = {'status':'Error has occurred while sending notification',
                                            'message': message}
                                    Log(Transactionname,msg,Mode,Ip) 
                            
                            
                        elif order_to_user_acctype == 1:
                            
                            """ Mail """
                            """ If admin receives an order admin will get  mail"""
                            try:
                                email_type = "11"
                                order_from_id = User.objects.get(id=Order.objects.get(Order_Id=order_id).User_Id_id).id
                                order_to_id= User.objects.get(id=Order.objects.get(Order_Id=order_id).To_User_Id_id).id
                                order_no = Order.objects.get(Order_Id=order_id).Order_No
                                send_mail(email_type,order_to_id,order_no=order_no,order_to_user_id=order_from_id)
                            except Exception as e:
                                message = {'status': 'While sending mail to {},error has occured'.format(user_id),
                                        'message':  e}
                                Log(Transactionname, message, Mode, Ip)
                            
                            
                            """ Notification """
                            """ Notification will be received to the user who placed the order   """
                            
                            
                            if Notification.objects.filter(NotificationType_Id=3).exists() :
                                try:
                                    status_id = '1'
                                    new_order_placed_index = 0
                                    fcm_user_id = Order.objects.get(Order_Id=order_id).User_Id_id
                                    dataobject={
                                        "Screen" : "Receivedorder",
                                        "Order_id" :'{}'.format(order_id),
                                        }
                                            
                                    send_notification_orderplaced(order_id,status_id,new_order_placed_index,fcm_user_id,dataobject)
                                except Exception as e:    
                                    message = 'order:{order_id},error:{e}'.format(order_id=order_id,e=e)
                                    msg = {'status':'Error has occurred while sending notification',
                                            'message': message}
                                    Log(Transactionname,msg,Mode,Ip) 
            
                    return Response({'Message':'Updated Successfully'},status=status.HTTP_200_OK)
                
                else:
                    serializer.save()
                    return Response({'Message':'Updated Successfully'},status=status.HTTP_200_OK)    
            
            else:
                msg = {'status': status.HTTP_400_BAD_REQUEST,'message':serializer.errors}
                Log(Transactionname,msg,Mode,Ip,user_id)
                
                if request.data['Transaction_Status'] == '11':
                    transaction_response='Payment Success'
                    """ Changing transaction status from success to transaction failed due to logical error """
                    Order.objects.filter(Order_Id=order_id).update(Transaction_Status=21,Transaction_Response=transaction_response)
                
                else:
                    transaction_response='Payment Failed'
                    """ Changing transaction status from success to transaction failed """
                    Order.objects.filter(Order_Id=order_id).update(Transaction_Status=21,Transaction_Response=transaction_response)
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
           
            if request.data['Transaction_Status'] == '11':
                transaction_response='Payment Success'
                """ Changing transaction status from success to transaction failed due to logical error """
                Order.objects.filter(Order_Id=order_id).update(Transaction_Status=21,Transaction_Response=transaction_response)
                
            else:
                transaction_response='Payment Failed'
                """ Changing transaction status from success to transaction failed """
                Order.objects.filter(Order_Id=order_id).update(Transaction_Status=21,Transaction_Response=transaction_response) 
            return Response(msg,status=status.HTTP_400_BAD_REQUEST) 

 
class AdminAddressAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        
        Transactionname = 'AdminAddressAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            admin_add = User.objects.get(AccountType_Id_id=1)
            serializer = AdminAddressSerializer(admin_add)
            return Response(serializer.data)   
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
        
class GetManufacturerProductAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'GetManufacturerProductAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            manufact_id = request.GET.get('manufact_id')
            product  = Product.objects.select_related('Unit_Id').filter(Manufacture_Id_id=manufact_id,Status_Id_id=15)
            serializer = GetManufacturerProductSerializer(product,many=True,context={'request':request})
            return Response(serializer.data)

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
class GetProductDetailAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'GetProductDetailAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            product_id = request.GET.get('product_id')
            product  = Product.objects.select_related('Tax_Id').get(Product_Id=product_id)
            serializer = GetProductDetailSerializer(product,context={'request':request})
            return Response(serializer.data)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        

class LoadUnitAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'LoadUnitAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            unit  = Unit.objects.all()
            serializer = LoadUnitSerializer(unit,many=True)
            return Response(serializer.data)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
    
class LoadManufactureAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'LoadManufactureAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            user  = User.objects.filter(AccountType_Id_id=2,Status_Id_id=15)
            serializer = LoadManufactureSerializer(user,many=True)
            return Response(serializer.data)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
class LoadOrderNoAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        
        Transactionname = 'LoadOrderNoAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id=request.query_params.get('user_id')
        
        try:
            try:
                order_id = Order.objects.last()
                next_order_id = order_id.Order_Id + 1
            except:
                next_order_id =  1
                
            order = AdminConfig.objects.first()
            inv_format = order.Invoice_No_Format
            order_pre = order.Order_No_Prefix
            no_of_digits = order.Digits_Length
            order_id_digits = str(next_order_id).zfill(no_of_digits)

            today = date.today()
            d1 = today.strftime("%d/%m/%Y")
            
            return Response({'Order_no':order_pre+order_id_digits,'Invoice_no':inv_format+order_id_digits,'Order_Date':d1})
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
    
class PlacedOrdersAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
         
        Transactionname = 'PlacedOrdersAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid=request.query_params.get('user_id')
        
        try:
            data_table=json.loads(request.query_params.get('data_table'))
            status_id = request.query_params.get('status_id')
            startdate = request.query_params.get('startdate')
            enddate = request.query_params.get('enddate') 
            
            acc_type = Accounttypeid(userid)
            if AccountType.objects.get(AccountType_Id=acc_type).IsDefault == False:
                user_id = User.objects.get(AccountType_Id_id=1).id
            else:
                user_id =  userid
        
            if status_id == '0':
                queryset = Order.objects.select_related('Transaction_Status','Status_Id','To_User_Id').filter(User_Id=user_id,Transaction_Date__date__range=[startdate,enddate])
            else:
                queryset = Order.objects.select_related('Transaction_Status','Status_Id','To_User_Id').filter(User_Id=user_id,Status_Id=status_id,Transaction_Date__date__range=[startdate,enddate])
            
            
            serializer_class=PlacedOrdersSerializer
            searchField=['Order_No','To_User_Id__Name','To_User_Id__Username','Invoice_No','Transaction_Date','Total_Qty','Grand_Total','Transaction_Status__Status_Name','Status_Id__Status_Name','Exp_Delivery_Date','Reject_Reason']
            columns=['Order_Id','Transaction_Date','Order_No','To_User_Id','Invoice_No','Total_Qty','Grand_Total','Transaction_Status','Status_Id']
            result = DataTablesServer(datatable=data_table, columns=columns, qs=queryset,
                        searchField=searchField,serializer=serializer_class,request = request).output_result()
            return Response(result,status=status.HTTP_200_OK)   

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
class ReceivedOrdersAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        Transactionname = 'ReceivedOrdersAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid=request.query_params.get('user_id')
        
        try:
            data_table=json.loads(request.query_params.get('data_table'))
            userid = request.GET.get('user_id')
            status_id = request.GET.get('status_id')
            startdate = request.query_params.get('startdate')
            enddate = request.query_params.get('enddate') 
            acc_type = Accounttypeid(userid)
            if AccountType.objects.get(AccountType_Id=acc_type).IsDefault == False:
                to_user_id = User.objects.get(AccountType_Id_id=1).id
            else:
                to_user_id =  userid
        
            if status_id == '0':
                queryset = Order.objects.select_related('User_Id','Status_Id','Transaction_Status').filter(To_User_Id=to_user_id,Transaction_Date__date__range=[startdate,enddate]).order_by('-Transaction_Date')
            else:
                queryset = Order.objects.select_related('User_Id','Status_Id','Transaction_Status').filter(To_User_Id=to_user_id,Status_Id=status_id,Transaction_Date__date__range=[startdate,enddate]).order_by('-Transaction_Date')
            
            serializer_class=ReceivedOrdersSerializer
            
            searchField=['Order_No','User_Id__Name','User_Id__Username','Invoice_No','Transaction_Date','Total_Qty','Grand_Total','Transaction_Status__Status_Name','Status_Id__Status_Name','Reject_Reason']
            columns=['Order_Id','Transaction_Date','Order_No','User_Id','Invoice_No','Total_Qty','Grand_Total','Transaction_Status','Status_Id']
            result = DataTablesServer(datatable=data_table, columns=columns, qs=queryset,
                        searchField=searchField,serializer=serializer_class,request = request).output_result()
            return Response(result,status=status.HTTP_200_OK)   

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)


class receivedOrdersStatusAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'receivedOrdersStatusAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid=request.query_params.get('user_id')
        
        try:
            status_id=[2,3,5,7]
            queryset  = Status.objects.filter(Status_Id__in=status_id)    
            serializer_class = ReceivedOrdersStatusSerializer(queryset,many=True)
            return Response(serializer_class.data)

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)

class ReceivedOrderStatusJsAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        
        Transactionname = 'ReceivedOrderStatusJsAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        id =  request.query_params.get('id')
        
        try:
            # use above id for log
            
            # acc_type = Accounttypeid(id)
            # if AccountType.objects.get(AccountType_Id=acc_type).IsDefault == False:
            #     user_id = User.objects.get(AccountType_Id_id=1).id
            # else:
            #     user_id =  userid
            user_id=  request.query_params.get('user_id')
            order_id = request.query_params.get('order_id')
            status_id = Order.objects.get(User_Id_id=user_id,Order_Id=order_id).Status_Id_id
            
            if status_id == 1:
                status_id=[2,3]
                queryset  = Status.objects.filter(Status_Id__in=status_id)
            elif status_id == 2 :
                queryset  = Status.objects.filter(Status_Id=5) 
            elif status_id == 5:
                queryset  = Status.objects.filter(Status_Id=6)       
            elif status_id == 6:
                queryset  = Status.objects.filter(Status_Id=7)  
            elif status_id == 7:
                queryset  = Status.objects.filter(Status_Id=8)
            elif status_id == 8:
                queryset  = Status.objects.filter(Status_Id=9)    
            serializer_class = ReceivedOrdersStatusSerializer(queryset,many=True)
            return Response(serializer_class.data)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)



class OrderViewAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        
        Transactionname = 'OrderViewAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id =  request.query_params.get('user_id')
        
        try:
            order_id = request.GET.get('order_id')
            queryset  = Order.objects.select_related('User_Id','To_User_Id','Transaction_Status').prefetch_related('orddet_ordid').get(Order_Id=order_id)
            serializer_class = OrderViewSerializer(queryset,context={'request':request})
            return Response(serializer_class.data)
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        

class OrderViewDownloadAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'OrderViewDownload'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id =  request.query_params.get('user_id')
        
        try:
            order_id = request.GET.get('order_id')
            order = Order.objects.get(Order_Id=order_id)
            pdfserializer = PdfSerializer(order,context={'request':request})
            
            """ Notification will be delivered while calling download invoice api  """
                
            notification_type = '12'
            if Notification.objects.filter(NotificationType_Id=int(notification_type)).exists() :
                user_id =  Order.objects.get(Order_Id=order_id).User_Id_id
                try:
                    dataobject={'screen':'orderviewdownload'}
                    send_notification(notification_type_id=notification_type,user_id=user_id,dataobject=dataobject)
                except Exception as e:
                    message = 'user_id :{},error :{e}'.format(user_id,e)
                    msg = {'status': 'Error has occurred while sending notification',
                        'message': message}
                    Log(Transactionname, msg, Mode, Ip)

            return Response(pdfserializer.data,status=status.HTTP_200_OK)

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)

class  GetStatusAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'GetStatusAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        user_id =  request.query_params.get('user_id')
        
        try:
            queryset  = Status.objects.all().order_by('Status_Id')
            serializer_class = GetStatusSerializer(queryset,many=True)
            return Response(serializer_class.data)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
class PaymentHistoryAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'PaymentHistoryAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            payment = request.query_params.get('payment')
            data_table=json.loads(request.query_params.get('data_table'))
            startdate = request.query_params.get('startdate')
            enddate = request.query_params.get('enddate')
            acc_type = Accounttypeid(userid)
            if AccountType.objects.get(AccountType_Id=acc_type).IsDefault == False:
                user_id = User.objects.get(AccountType_Id_id=1).id
            else:
                user_id =  userid
            
            
            if payment == '0':
                paymenthistory_from = PaymentHistory.objects.select_related('Order_Id__Transaction_Status','FromUser_Id','ToUser_Id').filter(FromUser_Id_id=user_id,Transaction_Date__date__range=[startdate,enddate]).order_by('-Transaction_Date')
                paymenthistory_to = PaymentHistory.objects.select_related('Order_Id__Transaction_Status','FromUser_Id','ToUser_Id').filter(ToUser_Id_id=user_id,Transaction_Date__date__range=[startdate,enddate]).order_by('-Transaction_Date')
                queryset = paymenthistory_from | paymenthistory_to
            
            elif payment == '1':
                queryset = PaymentHistory.objects.select_related('Order_Id__Transaction_Status','FromUser_Id','ToUser_Id').filter(ToUser_Id_id=user_id,Transaction_Date__date__range=[startdate,enddate]).order_by('-Transaction_Date')
            
            elif payment == '2':
                queryset = PaymentHistory.objects.select_related('Order_Id__Transaction_Status','FromUser_Id','ToUser_Id').filter(FromUser_Id_id=user_id,Transaction_Date__date__range=[startdate,enddate]).order_by('-Transaction_Date')
            
            serializer_class = PaymentHistorySerializer
            
            searchField=['Transaction_Date','Order_Id__Order_No','FromUser_Id__Name','ToUser_Id__Name','Order_Id__Transaction_Status__Status_Name','Order_Id__Grand_Total']
            columns=['PaymentHistory_Id','Transaction_Date','Order_Id__Order_No','FromUser_Id__Name','ToUser_Id__Name','Order_Id__Transaction_Status__Status_Name','Commission_Amount','Order_Id__Grand_Total']

            result = DataTablesServer(datatable=data_table, columns=columns, qs=queryset,
                        searchField=searchField,serializer=serializer_class,request = request).output_result()
            return Response(result,status=status.HTTP_200_OK)      
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, user_id)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
class PaymentCommissionAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'PaymentCommissionAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            order_id  = request.query_params.get('order_id')
            order_det_list = list(OrderDet.objects.filter(Order_Id_id=order_id).values_list('OrderDet_Id',flat=True))
            payment_commission = 0  
            for order_det in order_det_list:
                wholesale = OrderDet.objects.get(OrderDet_Id=order_det).Wholesale_Rate
                order_rate = OrderDet.objects.get(OrderDet_Id=order_det).Rate
                qty = OrderDet.objects.get(OrderDet_Id=order_det).Qty
                total = (order_rate - wholesale) * qty
                payment_commission+=total
            data={}
            data['Total'] = payment_commission
            return Response(data)    
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
class GetOrderCancellationChargesAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        Transactionname = 'GetOrderCancellationChargesAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            order_cancellation_charges = OrderCancellationCharges.objects.select_related('FromStatus_Id','ToStatus_Id').all()
            serializer = OrderCancellationChargesSerializer(order_cancellation_charges,many=True)
            return Response(serializer.data)  
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
        
class ReturnReasonPostGETAPI(APIView):
    authentication_classes = [TokenAuthentication]    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        """
        Method: 'GET'
        
        Description of the Function:
           returns all order return reason 
        
        Parameter:
            None
        
        Response: 'JSONResponse with data and status code'.

        """
        Transactionname = 'ReturnReasonPostGETAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            return_reason = OrderReturnReason.objects.all().order_by('-CreatedOn')
            serializer = ReturnReasonPostSerializer(return_reason,many=True)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
    
    def post(self,request):
        """
        Method: 'POST'
        
        Description of the Function:
           saves order return reason 
        
        Parameter:
            None
        
        Response: 'JSONResponse with data and status code'.

        """
        Transactionname = 'ReturnReasonPostGETAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            serializer = ReturnReasonPostSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data,status=status.HTTP_200_OK)        
            else:
                msg = {'status': status.HTTP_400_BAD_REQUEST,
                    'message': serializer.errors}
                Log(Transactionname, msg, Mode, Ip)
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)

class ReturnReasonUpdateDeleteAPI(APIView):
    authentication_classes = [TokenAuthentication]    
    permission_classes = [IsAuthenticated]
    
    def put(self,request):
        """
        Method: 'PUT'
        
        Description of the Function:
           update the order return reason
        
        Parameter:
            OrderReturnReason_Id(pk)
        
        Response: 'JSONResponse with data and status code'.

        """
        Transactionname = 'ReturnReasonUpdateDeleteAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            order_returnreason_id = request.query_params.get('OrderReturnReason_Id')
            return_reason = OrderReturnReason.objects.get(OrderReturnReason_Id=order_returnreason_id)
            serializer = ReturnReasonUpdateDeleteSerializer(return_reason,data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data,status=status.HTTP_200_OK)        
            else:
                msg = {'status': status.HTTP_400_BAD_REQUEST,
                    'message': serializer.errors}
                Log(Transactionname, msg, Mode, Ip, userid)
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self,request):
        """
        Method: 'DELETE'
        
        Description of the Function:
           delete the order return reason
        
        Parameter:
            id(pk)
        
        Response: 'JSONResponse with data and status code'.

        """
        Transactionname = 'ReturnReasonUpdateDeleteAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            try:
                id = request.query_params.get('id')
                return_reason = OrderReturnReason.objects.get(OrderReturnReason_Id=id)
                return_reason.delete()
                return Response(status=status.HTTP_200_OK)
            except RestrictedError:
                return Response(status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)


class ReturnOrderListAPI(APIView):
    authentication_classes = [TokenAuthentication]    
    permission_classes = [IsAuthenticated]   
    """
        Method: 'GET'
        
        Description of the Function:
           returns all order return list 
        
        Parameter:
            None
        
        Response: 'JSONResponse with data and status code'.

    """
    def get(self,request):
        
        Transactionname = 'ReturnOrderListAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            data_table=json.loads(request.query_params.get('data_table'))
            startdate = request.query_params.get('startdate')
            enddate = request.query_params.get('enddate') 
            status_id = request.query_params.get('ret_status')
            if status_id == '0':
                queryset = OrderReturn.objects.select_related('Order_Id__User_Id','Status_Id').filter(Transaction_Date__date__range=[startdate,enddate])
            else:     
                queryset = OrderReturn.objects.select_related('Order_Id__User_Id','Status_Id').filter(Status_Id_id=status_id,Transaction_Date__date__range=[startdate,enddate])
                
            serializer_class = ReturnOrderListSerializer
            searchField=['OrderReturn_Date','Order_Id__Order_No','OrderReturn_No','Order_Id__User_Id__Name','Total_Qty','Grand_Total','Status_Id__Status_Name']
            columns=['OrderReturn_Id','OrderReturn_Date','Order_Id__Order_No','OrderReturn_No','Order_Id__User_Id__Name','Total_Qty','Grand_Total','Status_Id__Status_Name']
            
            result = DataTablesServer(datatable=data_table, columns=columns, qs=queryset,
                        searchField=searchField,serializer=serializer_class,request = request).output_result()
            return Response(result,status=status.HTTP_200_OK)     
      
      
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
            
class ReturnOrderDetListAPI(APIView):
    authentication_classes = [TokenAuthentication]    
    permission_classes = [IsAuthenticated]   
    """
        Method: 'GET'
        
        Description of the Function:
           returns all order return details list 
        
        Parameter:
            order_ret_id
        
        Response: 'JSONResponse with data and status code'.

    """
    def get(self,request):
        
        Transactionname = 'ReturnOrderDetListAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            order_ret_id = request.query_params.get('order_ret_id')
            order_return = OrderReturnDet.objects.select_related('Product_Id','OrderReturn_Id','OrderReturnReason_Id').filter(OrderReturn_Id=order_ret_id)
            context = {'request':request}
            serializer = OrderReturnDetsSerializer(order_return,many=True,context=context)
            return Response(serializer.data)
        
        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)

class ReturnOrderStatusjsAPI(APIView):
    """
        Method: 'GET'
        
        Description of the Function:
           returns all the return order status 
        
        Parameter:
            ret_ord_id
        
        Response: 'JSONResponse with data and status code'.

    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        
        Transactionname = 'ReturnOrderStatusjsAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            ret_ord_id = request.query_params.get('ret_ord_id')
            status_id = OrderReturn.objects.get(OrderReturn_Id=ret_ord_id).Status_Id_id

            if status_id == 22 :
                status_id=[18,16]
                queryset  = Status.objects.filter(Status_Id__in=status_id) 
            elif status_id == 18:
                queryset  = Status.objects.filter(Status_Id=19)       

            serializer_class = ReceivedOrdersStatusSerializer(queryset,many=True)
            return Response(serializer_class.data)

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)

class ReturnOrderStatuslistAPI(APIView):
    """
        Method: 'GET'
        
        Description of the Function:
           returns all the return order status list
        
        Parameter:
            None
        
        Response: 'JSONResponse with data and status code'.

    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        
        Transactionname = 'ReturnOrderStatuslistAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            """ refund initiated,refund processed and order return request """
            status_id = [18,19,22,16]
            returnord_status  = Status.objects.filter(Status_Id__in=status_id)    
            serializer = ReceivedOrdersStatusSerializer(returnord_status,many=True)
            return Response(serializer.data)

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)
        
class CancelOrderDetailsAPI(APIView):
    """
        Method: 'GET'
        
        Description of the Function:
           returns all cancel order details
        
        Parameter:
            None
        
        Response: 'JSONResponse with data and status code'.

    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        
        Transactionname = 'CancelOrderDetailsAPI'
        Ip = request.META['REMOTE_ADDR']
        Mode = request.method
        userid =  request.query_params.get('user_id')
        
        try:
            """ Status 4 for order cancel """
            data_table=json.loads(request.query_params.get('data_table'))
            startdate = request.query_params.get('startdate')
            enddate = request.query_params.get('enddate') 
            
            prefetch_ordhis = Prefetch('ordhis_ordid',queryset=OrderHistory.objects.exclude(Status_Id_id=4).order_by('-Transaction_Date'))
            prefetch_fromstatus = Prefetch('ordhis_ordid__Status_Id__fromstatus')
            prefetch_tostatus = Prefetch('ordhis_ordid__Status_Id__tostatus')
            queryset = Order.objects.select_related('Status_Id','User_Id','Transaction_Status').prefetch_related(prefetch_ordhis,prefetch_fromstatus,prefetch_tostatus).filter(Status_Id_id=4,Transaction_Date__date__range=[startdate,enddate]).order_by('-Transaction_Date')  
            serializer_class = CancelOrderDetailsSerializer
            
            searchField=['Transaction_Date','User_Id__Name','User_Id__Username','Order_No','Invoice_No','Total_Qty','Transaction_Status__Status_Name','Grand_Total']
            columns=['Order_Id','Transaction_Date','Order_No','User_Id__Name','Invoice_No','Total_Qty','Transaction_Status__Status_Name','Grand_Total']
            
            result = DataTablesServer(datatable=data_table, columns=columns, qs=queryset,
                        searchField=searchField,serializer=serializer_class,request = request).output_result()
            return Response(result,status=status.HTTP_200_OK)   

        except Exception as e:
            msg={'error':str(e),'traceback':traceback.format_exc()}
            Log(Transactionname, msg, Mode, Ip, userid)  
            return Response(msg,status=status.HTTP_400_BAD_REQUEST)