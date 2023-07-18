from multiprocessing import context
from django.conf import settings
from django.shortcuts import redirect, render
import requests,json,traceback
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from BigBrotherAdmin.functions import razorpay_clientfunc,Log
import razorpay
from BigBrotherAdmin.views.views import verifyuser

url = settings.API_URL
Rpay_logo_url=settings.RAZORPAY_LOGO_URL
Rpay_callback_url=settings.RAZORPAY_CALLBACK_URL

# Create your views here.
MODE = 'edit'


@never_cache
def OrderView(request):
    Transactionname = 'OrderView'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'POST,GET'
    
    try:
        Token = request.session['Token']
        USER_ID = request.session['UserId']  
    except KeyError:
        return redirect('login')
    
    try:
        if request.method == 'POST': 
            order_id = request.POST['hidOrderId']
            params = {'order_id': order_id,'user_id':USER_ID}
            headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
            order = requests.get('{url}/orderview/'.format(url=url),params=params, headers=headers).json()
    
            # Rate Total
            Tax_Amount=[]
            for data in order['Orderdetails']:
                TotalTax=data['Tax_Amount']
                Tax_Amount.append(float(TotalTax))

            # Amount Total 
            Amount=[]
            for data in order['Orderdetails']:
                Amount.append(float(data['NetAmount']))
                
            for data in order.keys():
                if order[data] == None:
                    order[data] = ''
            
            context = {
                'order': order,
                "Tax_Amount":sum(Tax_Amount),
                "Amount":sum(Amount)}

            return render(request,'mypanel/orderview.html',context=context)
        else:
            return render(request,'mypanel/orderview.html')

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip, Mode, USER_ID)
        return render(request,'mypanel/error.html')     

@never_cache
def PlacedOrderView(request,id):
    Transactionname = 'PlacedOrderView'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'
     
    try:
        Token = request.session['Token']
        USER_ID = request.session['UserId']  
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
        
    except KeyError:
        return redirect('login')

    try:
        order_id = id
        params = {'order_id': order_id,'user_id':USER_ID}
       
        order = requests.get('{url}/orderview/'.format(url=url),params=params, headers=headers).json()

        # Rate Total
        Tax_Amount=[]
        for data in order['Orderdetails']:
            TotalTax=data['Tax_Amount']
            Tax_Amount.append(float(TotalTax))

        # Amount Total 
        Amount=[]
        for data in order['Orderdetails']:
            Amount.append(float(data['NetAmount']))
            
        for data in order.keys():
            if order[data] == None:
                order[data] = ''
        
        context = {
            'order_id':order_id,
            'order': order,
            "Tax_Amount":sum(Tax_Amount),
            "Amount":sum(Amount)}

        return render(request,'mypanel/orderview.html',context=context)

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip, Mode, USER_ID)
        return render(request,'mypanel/error.html')   



@never_cache
def DownloadOrder(request):
    Transactionname = 'DownloadOrder'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'
    
    try:
        Token = request.session['Token']
        USER_ID = request.session['UserId']   
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
        
    except KeyError:
        return redirect('login')
    
    try:
        order_id = request.POST['hidOrderId']
        params = {'order_id':order_id ,'user_id':USER_ID}
       
        order_post = requests.get('{url}/orderviewdownload/'.format(url=url),params=params, headers=headers)
        order_view = order_post.json()
        context = {
            'order_view':order_view.get('Invoice_Pdf')
        }
        return render(request,'mypanel/pdfview.html',context=context)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip, Mode, USER_ID)
        return render(request,'mypanel/error.html')   

@never_cache
def OrdertoManufacture(request):
    Transactionname = 'OrdertoManufacture'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'POST,GET'
    
    try:    
        Token = request.session['Token']
        user_id=request.session['UserId']
        user_id_params = {'user_id':user_id}
    except KeyError:
        return redirect('login')

    try:
        if request.method == 'POST':

            Order_Id = request.POST['OrderId']
            Delivery_Charge = "0"
            User_Id = request.session['UserId']
            To_User_Id = request.POST['ddlManufacture']
            Total_IGST_Amount = request.POST['hidIgs']
            Total_SGST_Amount =request.POST['hidSgs']
            Total_CGST_Amount = request.POST['hidCgs']
            Total_Qty = request.POST['hidQty']
            Taxable_Amount = request.POST['txtTaxableAmt']
            Total_Tax_Amount = request.POST['txtTaxAmt']
            Sub_Total = request.POST['txtSubTotal']
            RoundOff = "0"#request.POST['txtRound']
            Grand_Total = request.POST['txtGrandTotal']
            Transaction_Amount = request.POST['txtGrandTotal']
            Desc = request.POST['txtDescription']
            Status_Id = "1"
            Transaction_Status = "10"
            edit = request.POST['edit']
            OrderDet = request.POST.getlist('OrderDet')
            orderIn = json.dumps(OrderDet)
            orddata = json.loads(orderIn)
            headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
            admin_add =  requests.get('{url}/adminaddress/'.format(url=url), headers=headers, params=user_id_params).json()
            Delivery_Address =''
            for i in admin_add.get('admin_address'):
                Delivery_Address+=f' {i},'
            data = {'Transaction_Status':Transaction_Status,'Delivery_Address':Delivery_Address,'Delivery_Charge':Delivery_Charge,'To_User_Id': To_User_Id, 'User_Id':User_Id,'Desc':Desc,'Total_IGST_Amount':Total_IGST_Amount,'Total_SGST_Amount':Total_SGST_Amount,'Total_CGST_Amount':Total_CGST_Amount,'Total_Qty':Total_Qty,'Taxable_Amount':Taxable_Amount,'Total_Tax_Amount':Total_Tax_Amount,'Sub_Total':Sub_Total,'RoundOff':RoundOff,'Grand_Total':Grand_Total,'Transaction_Amount':Transaction_Amount,'Status_Id':Status_Id,'OrderDet':orddata}
            orderdata = requests.post('{url}/order/'.format(url=url), data=data, headers=headers , params=user_id_params)
            if orderdata.status_code == 400:
                message="Order has not been placed"
                messages.error(request,message)
                return redirect('order')
            else:    
                orderjson = orderdata.json()
                request.session['orderid']=orderjson.get('Order_Id')
                param={"user_id":user_id}
                razorpayprefill = requests.get('{url}/razorpayprefill/'.format(url=url),params=param ,headers=headers).json()
                Razorpay_Generated_Order_Id=orderjson.get('Razorpay_Generated_Order_Id')
                Razorpay_amount = orderjson.get('Razorpay_amount')
                Razorpay_currency = orderjson.get('Razorpay_currency')
                Email=razorpayprefill.get('email')
                Mobilenumber=razorpayprefill.get('MobileNo')
                razorpay_client,razor_key_id = razorpay_clientfunc()
                context = {'Razorpay_Generated_Order_Id': Razorpay_Generated_Order_Id,}
                context['razorpay_merchant_key'] =razor_key_id
                context['razorpay_amount'] = Razorpay_amount
                context['currency'] = Razorpay_currency
                context['rpay_url'] = Rpay_logo_url
                context['callback'] = Rpay_callback_url
                context['name'] = "BigBrother"
                context['description'] = "Order Transaction"
                context['email'] = Email
                context['mobilenumber'] = Mobilenumber
                return render(request, 'mypanel/order.html', context)

        else:
            headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
            admin_add =  requests.get('{url}/adminaddress/'.format(url=url), headers=headers , params=user_id_params).json()
            manufacture = requests.get('{url}/loadmanufacture/'.format(url=url), headers=headers,  params=user_id_params).json()
            unit = requests.get('{url}/loadunit/'.format(url=url), headers=headers,  params=user_id_params).json()
            Ono = requests.get('{url}/loadorderno/'.format(url=url), headers=headers,  params=user_id_params).json() 
            context = {'manufacture': manufacture,'unit': unit,'Ono': Ono,'admin_add':admin_add}
            return render(request, 'mypanel/order.html', context)

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip, Mode, user_id)
        return render(request,'mypanel/error.html')  
    
@csrf_exempt
def OrderCallback(request):
    Transactionname = 'OrderCallback'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'POST'
    try:
        def verify_signature(response_data):
            razorpay_client,razor_key_id = razorpay_clientfunc()
            return razorpay_client.utility.verify_payment_signature(response_data)
        
        if "razorpay_signature" in request.POST:
            payment_id = request.POST.get("razorpay_payment_id", "")
            provider_order_id = request.POST.get("razorpay_order_id", "")
            signature_id = request.POST.get("razorpay_signature", "")
            if verify_signature(request.POST):
                status = "SUCCESS"
                context={"status": status,
                    "razorpay_payment_id":payment_id,
                    "razorpay_order_id" :provider_order_id,
                    "signature_id":signature_id
                    }
                return render(request, "mypanel/orderpaystatus.html", context=context)
            else:
                status ="FAILURE"
        
                return render(request, "mypanel/orderpaystatus.html", context={"status":status})
        elif "error[code]" in request.POST:
            
            code = request.POST.get("error[code]")
            description = request.POST.get("error[description]")
            reason = request.POST.get("error[reason]")
            Error_Response=str(code) + "  " +str(description)+ "  " +str(reason)
            status ="FAILURE"
            return render(request, "mypanel/orderpaystatus.html", context={"status": status,"error_response":Error_Response})
        else:
            return redirect('placedorders')
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip, Mode)
        return render(request,'mypanel/error.html')
    
@never_cache    
def UpdateOrderPaymentStatus(request):
    Transactionname = 'UpdateOrderPaymentStatus'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'PUT'
      
    try:
        Token = request.session['Token']
        USER_ID=request.session['UserId'] 
        razorpay_payment_id=request.GET.get('razorpay_payment_id',None)
        razorpay_order_id=request.GET.get('razorpay_order_id',None)
        signature_id =request.GET.get('signature_id',None)
        Transaction_Response=request.GET.get('transaction_response',None)
        error_response=request.GET.get('error_response',None)
        params={'order_id':request.session['orderid'], 'user_id':USER_ID}
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
        
        
        if Transaction_Response == 'SUCCESS':
            headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
            data={
                'Transaction_Response':Transaction_Response,
                'Transaction_Status':11,
                'Razorpay_Payment_Id':razorpay_payment_id,
                'Razorpay_signature':signature_id, 
                'Razorpay_Order_Id':razorpay_order_id
            }
            payment_update = requests.put('{url}/updateorderpaymentstatus/'.format(url=url), data=data, params=params, headers=headers)
            if payment_update.status_code == 200:
                return JsonResponse({"status":"success",'order_id':request.session['orderid']})
            else:
                return JsonResponse({"status":"logical error"})
        else:
            data={
                'Transaction_Response':error_response,
                'Transaction_Status':12,
            }
            payment_update = requests.put('{url}/updateorderpaymentstatus/'.format(url=url), data=data, params=params, headers=headers)
            return JsonResponse({"status":"failed",'order_id':request.session['orderid']})

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip, Mode, USER_ID)
        return render(request,'mypanel/error.html')

@never_cache
def OrderDelete(request, id, **kwarg):
    Transactionname = 'OrderDelete'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'DELETE' 
    try:    
        Token = request.session['Token']
        USER_ID=request.session['UserId'] 
         
    except KeyError:
        return redirect('login')
    
    try:
        params={'user_id':USER_ID}
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)} 
        status=requests.delete('{url}/orderupdate/{id}/'.format(url=url, id=id), headers=headers, params=params)
        statusjson=status.json()                     

        if status.status_code == 400 :        
            messages.success(request, statusjson.get('message'))
            return redirect('order')
        else:
            messages.success(request,statusjson.get('message'))
            return redirect('order')

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip, Mode, USER_ID)
        return render(request,'mypanel/error.html')
    
@never_cache
def GetManufacturerProduct(request):
    Transactionname = 'GetManufacturerProduct'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET' 
    
    try:
        Token = request.session['Token']
        USER_ID=request.session['UserId']  
    except KeyError:
        return redirect('login')
    
    try:
        manufact_id = request.GET.get('manufact_id')
        params = {'manufact_id': manufact_id,'user_id':USER_ID}
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
        data = requests.get('{url}/getmanufacturerproduct/'.format(url=url),params=params, headers=headers).json()
        data = {'data': data}
        return JsonResponse(data)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, USER_ID)
        return render(request,'mypanel/error.html')

@never_cache
def GetProductDetails(request):
    Transactionname = 'GetProductDetails'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'  
    try:
        Token = request.session['Token']
        USER_ID=request.session['UserId']   
    except KeyError:
        return redirect('login')
    
    try:
        product_id = request.GET.get('product_id')
        params = {'product_id': product_id,'user_id':USER_ID}
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
        data = requests.get('{url}/getproductdetail/'.format(url=url),params=params, headers=headers).json()
        data = {'data': data}
        return JsonResponse(data)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, USER_ID)
        return render(request,'mypanel/error.html')
    
@never_cache
def Placedorders(request):
    Transactionname = 'Placedorders'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'  
    
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)} 
        params = {'user_id':user_id} 
    except KeyError:
        return redirect('login')
    
    try:
        status= requests.get('{url}/getstatus/'.format(url=url),headers=headers, params=params).json()
        context = {
            'status':status,
            }
        return render(request, "mypanel/placedorders.html",context=context)

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')
    
@never_cache
def Recivedorders(request):
    Transactionname = 'Recivedorders'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET' 
     
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        params = {'user_id':user_id}  
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
    except KeyError:
        return redirect('login')
    
    try:
        status= requests.get('{url}/getstatus/'.format(url=url),headers=headers, params=params).json()
        context = {'status':status,}
        return render(request, "mypanel/receivedorders.html",context=context)
        
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')
    
@never_cache
def Getrecievedstatusjs(request):
    Transactionname = 'Getrecievedstatusjs'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET' 
     
    try:
        Token = request.session['Token']
        USER_ID = request.session['UserId']
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
        
    except KeyError:
        return redirect('login')
    
    try:
        order_id=request.GET.get('order_id')
        user_id=request.GET.get('user_id')
        params = {'order_id': order_id,'user_id':user_id,'id':USER_ID}
        receviedstatus = requests.get('{url}/receivedorderstatusjs/'.format(url=url),headers=headers,params=params).json()
        data={'receviedstatus':receviedstatus}
        return JsonResponse(data)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, USER_ID)
        return render(request,'mypanel/error.html')
    
@never_cache
def ReceivedOrderStatusUpdate(request):
    Transactionname = 'ReceivedOrderStatusUpdate'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'PUT,GET' 
    
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
   
    except KeyError:
        return redirect('login')

    try:
        if request.method == 'POST':
            status_id = request.POST['ddlStatus']
            order_id = request.POST['hidOrderid']
            paramsstatus = {'user_id': user_id,'order_id':order_id}   
            data={'Status_Id':status_id}
            if request.POST['ddlStatus'] == '2':
                txtExpectetdate =  request.POST['txtExpectetdate']
                data['Exp_Delivery_Date'] = txtExpectetdate
            
            elif request.POST['ddlStatus'] == '3':
                txtcancelling =  request.POST['txtcancelling']
                data['Reject_Reason'] = txtcancelling     
        
            requests.put('{url}/updateorderstatus/'.format(url=url),params=paramsstatus,data=data,headers=headers)
            messages.success(request, 'Status Updated Successfully')
            return redirect('receivedorders')

        else:
            status = requests.get('{url}/getstatus/'.format(url=url),headers=headers).json()
            context = {
                'status':status,
                }
            return render(request, "mypanel/receivedorders.html",context=context)
        
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')

@never_cache
def PaymentHistory(request):
    Transactionname = 'PaymentHistory'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET' 
    
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
      
    except KeyError:
        return redirect('login')
    
    try:
        return render(request, "mypanel/paymenthistory.html")

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')
    
@never_cache
def ReturnReason(request):
    Transactionname = 'ReturnReason'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'POST,GET' 
     
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization':'Token {Token}'.format(Token=Token)}
        params1={'user_id':user_id}
    except:
        return redirect('login')    
    
    try:
        get_all_return_reason = requests.get('{url}/returnreasonpostget/'.format(url=url),headers=headers,params=params1).json()
        if request.method == 'POST':
            reason = request.POST.get('txtreturnreason')
            mode = request.POST.get('edit')
            if MODE == mode:
                OrderReturnReason_Id = request.POST.get('editid')
                data={'ReturnReason':reason,'Editedby':user_id}
                params={'OrderReturnReason_Id':OrderReturnReason_Id,'user_id':user_id}
                order_return_reason = requests.put('{url}/returnreasonupdatedelete/'.format(url=url),data=data,headers=headers,params=params)
                if order_return_reason.status_code == 200:
                    messages.success(request,'Order return reason updated successfully')
                    return redirect('returnreason')
                else:
                    order_return_reason_error = order_return_reason.json
                    context = {'order_return_reason_error':order_return_reason_error,
                            'reason':reason,'get_all_return_reason':get_all_return_reason}
                    return render(request,'mypanel/returnreason.html',context=context)
                
            else:
                data={'ReturnReason':reason,'Createdby':user_id,}
                params={'user_id':user_id}
                order_return_reason = requests.post('{url}/returnreasonpostget/'.format(url=url),data=data,headers=headers,params=params)
                if order_return_reason.status_code == 200:
                    messages.success(request,'Order return reason added successfully')
                    return redirect('returnreason')
                else:
                    order_return_reason_error = order_return_reason.json
                    context = {'order_return_reason_error':order_return_reason_error,
                            'reason':reason,'get_all_return_reason':get_all_return_reason}
                    return render(request,'mypanel/returnreason.html',context=context)
        else:        
            context={'get_all_return_reason':get_all_return_reason}        
            return render(request,'mypanel/returnreason.html',context=context)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')
       
def ReturnReasonDelete(request,id):
    Transactionname = 'ReturnReasonDelete'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'DELETE'
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization':'Token {Token}'.format(Token=Token)}
    except:
        return redirect('login') 
    
    try:
        params={'id':id,'user_id':user_id}
        order_return_reason = requests.delete('{url}/returnreasonupdatedelete/'.format(url=url),headers=headers,params=params)
        if order_return_reason.status_code == 200:
            messages.success(request,'Order return reason deleted successfully')
            return redirect('returnreason')
        else:
            messages.error(request,'Order return reason is being referenced with another instance')
            return redirect('returnreason')

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')

def OrderReturnList(request):
    Transactionname = 'OrderReturnList'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'
        
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization':'Token {Token}'.format(Token=Token)}
    except:
        return redirect('login')
    
    try:
        params={'user_id':user_id}
        returnord_status = requests.get('{url}/returnorderstatuslist/'.format(url=url),headers=headers,params=params).json()
        context={'status':returnord_status}
        return render(request,'mypanel/orderreturnlist.html',context=context)    

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')
    
def OrderReturnDetailsList(request):
    Transactionname = 'OrderReturnDetailsList'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'
    
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization':'Token {Token}'.format(Token=Token)}
    except:
        return redirect('login')
    
    try:
        order_ret_id = request.GET.get('order_ret_id')
        params={'order_ret_id':order_ret_id,'user_id':user_id}
        get_returned_orderdetlist = requests.get('{url}/returnorderdetlist/'.format(url=url),headers=headers,params=params).json()
        return JsonResponse(get_returned_orderdetlist,safe=False)

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')
    
 
@never_cache
def GetReturnStatusjs(request):
    Transactionname = 'GetReturnStatusjs'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'
    
    try:
        Token = request.session['Token']
        user_id = request.session['UserId'] 
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)} 
    except KeyError:
        return redirect('login')
    
    try:
        ret_ord_id=request.GET.get('ret_ord_id')
        params = {'ret_ord_id': ret_ord_id,'user_id':user_id}
        ret_ord_status = requests.get('{url}/returnorderstatusjs/'.format(url=url),headers=headers,params=params).json()
        data={'ret_ord_status':ret_ord_status}
        return JsonResponse(data)

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')
    
@never_cache
def ReturnOrderstatusupdate(request):
    Transactionname = 'ReturnOrderstatusupdate'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'PUT'
    
    """
    Method:'PUT'

    Description of the Function:
        gather the return order status and update in return order table

    Parameter for API:
        None

    Response: 
        renders the template with data 

    """
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
        
    except KeyError:
        return redirect('login')
    
    try:
        ret_order_id = request.POST.get('hidOrderid')
        status_id = request.POST.get('ddlStatus')
        data={'Status_Id':status_id}
        if status_id == '16':
            reject_reason = request.POST.get('txtreject')
            data['Reject_Reason'] = reject_reason
        params={'ret_order_id':ret_order_id,'user_id':user_id}
        ret_order_status_update = requests.put('{url}/returnorderstatusupdate/'.format(url=url),headers=headers,params=params,data=data)
        if ret_order_status_update.status_code == 200:
            messages.success(request,'Status updated successfully')
            return redirect('orderreturnlist')
        else:
            messages.error(request,'Status update not successfull')
            return redirect('orderreturnlist')
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')
   
   
@never_cache   
def OrderCancellist(request):
    Transactionname = 'OrderCancellist'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'
    
    """
    Method:'GET'

    Description of the Function:
        gathers all cancel order details

    Parameter for API:
        None

    Response: 
        renders the template with data 

    """
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
    except:
        return redirect('login')
    
    try:
        return render(request,'mypanel/ordercancellist.html')
       
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')    
    
    
    
@never_cache    
def listplacedordersdatatable(request):
    Transactionname = 'listplacedordersdatatable'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'
    
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
    except:
        return redirect('login')
    
    try:
        status_id = request.GET.get('status')
        data_table=dict(request.GET)
        startdate = request.GET.get('startdate')
        enddate = request.GET.get('enddate')
        params = {'data_table':json.dumps(data_table),
                  'user_id':user_id,'status_id':status_id,'enddate':enddate,'startdate':startdate}
        data = requests.get('{url}/placedorders/'.format(url=url),params=params, headers=headers).json()
        return JsonResponse(data,safe=False)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')    


@never_cache
def listrecievedordersdatatable(request):
    Transactionname = 'listrecievedordersdatatable'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'
    
    try:
        Token = request.session['Token']
        user_id = request.session['UserId']
        headers = {'Authorization': 'Token {Token}'.format(Token=Token)}
    except:
        return redirect('login')
    try:
        status_id = request.GET.get('status')
        data_table=dict(request.GET)
        startdate = request.GET.get('startdate')
        enddate = request.GET.get('enddate')
        params = {'data_table':json.dumps(data_table),
                  'user_id':user_id,'status_id':status_id,'enddate':enddate,'startdate':startdate}
        data = requests.get('{url}/receivedorders/'.format(url=url),params=params, headers=headers).json()
        return JsonResponse(data,safe=False)

    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')  


@never_cache
def listpaymenthistorydatatable(request):
    Transactionname = 'listpaymenthistorydatatable'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET' 
    Token,user_id,headers = verifyuser(request)

    try:
        payment = request.GET.get('payment')
        startdate = request.GET.get('startdate')
        enddate = request.GET.get('enddate')
        data_table=dict(request.GET)
        params={'payment':payment,'data_table':json.dumps(data_table),
                'user_id':user_id,'enddate':enddate,'startdate':startdate}
        data = requests.get('{url}/paymenthistory/'.format(url=url),headers=headers,params=params).json()
        return JsonResponse(data,safe=False)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')

@never_cache
def listorderreturndatatable(request):
    Transactionname = 'listorderreturndatatable'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'  
    Token,user_id,headers = verifyuser(request)

    try:
        startdate = request.GET.get('startdate')
        enddate = request.GET.get('enddate')
        ret_status =  request.GET.get('ret_status')
        data_table=dict(request.GET)
        params={'data_table':json.dumps(data_table),'ret_status':ret_status,
                'user_id':user_id,'enddate':enddate,'startdate':startdate}
        data = requests.get('{url}/returnorderlist/'.format(url=url),headers=headers,params=params).json()
        return JsonResponse(data,safe=False)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')        
    
@never_cache
def listordercanceldatatable(request):
    Transactionname = 'listordercanceldatatable'
    Ip = request.META['REMOTE_ADDR']
    Mode = 'GET'   
    Token,user_id,headers = verifyuser(request)

    try:
        startdate = request.GET.get('startdate')
        enddate = request.GET.get('enddate')
        data_table=dict(request.GET)
        params={'data_table':json.dumps(data_table),
                'user_id':user_id,'enddate':enddate,'startdate':startdate}
        data = requests.get('{url}/cancelorderdetails/'.format(url=url),headers=headers,params=params).json()
        return JsonResponse(data,safe=False)
    
    except Exception as e:
        msg={'error':str(e),'traceback':traceback.format_exc()}
        Log(Transactionname, msg, Ip,Mode, user_id)
        return render(request,'mypanel/error.html')     