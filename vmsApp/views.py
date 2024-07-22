import datetime
from django.shortcuts import redirect, render
import json
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from vmsApp import models, forms
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
import os
import tempfile
from django.http import HttpResponse
from django.template.loader import render_to_string
import subprocess
import jpype
from jpype import java, JClass, JString
from django.db import connection
from django.http import FileResponse
from django.shortcuts import render
from .utils import generate_report


def context_data(request):
    fullpath = request.get_full_path()
    abs_uri = request.build_absolute_uri()
    abs_uri = abs_uri.split(fullpath)[0]
    context = {
        'system_host' : abs_uri,
        'page_name' : '',
        'page_title' : '',
        'system_name' : 'التصديقات الجوية',
        'topbar' : True,
        'footer' : True,
    }

    return context
    
def userregister(request):
    context = context_data(request)
    context['topbar'] = False
    context['footer'] = False
    context['page_title'] = "User Registration"
    if request.user.is_authenticated:
        return redirect("home-page")
    return render(request, 'register.html', context)

def save_register(request):
    resp={'status':'failed', 'msg':''}
    if not request.method == 'POST':
        resp['msg'] = "No data has been sent on this request"
    else:
        form = forms.SaveUser(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your Account has been created succesfully")
            resp['status'] = 'success'
        else:
            for field in form:
                for error in field.errors:
                    if resp['msg'] != '':
                        resp['msg'] += str('<br />')
                    resp['msg'] += str(f"[{field.name}] {error}.")
            
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def update_profile(request):
    context = context_data(request)
    context['page_title'] = 'Update Profile'
    user = User.objects.get(id = request.user.id)
    if not request.method == 'POST':
        form = forms.UpdateProfile(instance=user)
        context['form'] = form
        print(form)
    else:
        form = forms.UpdateProfile(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile has been updated")
            return redirect("profile-page")
        else:
            context['form'] = form
            
    return render(request, 'manage_profile.html',context)

@login_required
def update_password(request):
    context =context_data(request)
    context['page_title'] = "Update Password"
    if request.method == 'POST':
        form = forms.UpdatePasswords(user = request.user, data= request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Your Account Password has been updated successfully")
            update_session_auth_hash(request, form.user)
            return redirect("profile-page")
        else:
            context['form'] = form
    else:
        form = forms.UpdatePasswords(request.POST)
        context['form'] = form
    return render(request,'update_password.html',context)

# Create your views here.
def login_page(request):
    context = context_data(request)
    context['topbar'] = False
    context['footer'] = False
    context['page_name'] = 'login'
    context['page_title'] = 'Login'
    return render(request, 'login.html', context)

def login_user(request):
    logout(request)
    resp = {"status":'failed','msg':''}
    username = ''
    password = ''
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                resp['status']='success'
            else:
                resp['msg'] = "Incorrect username or password"
        else:
            resp['msg'] = "Incorrect username or password"
    return HttpResponse(json.dumps(resp),content_type='application/json')


@login_required
def home(request):
    context = context_data(request)
    context['page'] = 'home'
    context['page_title'] = 'Home'
    context['dapartments'] = models.Departments.objects.filter(delete_flag = 0, status = 1).all().count()
    context['users'] = User.objects.filter(is_superuser = False).count()
    date = datetime.datetime.now()
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")
    context['visitors'] = models.Visitors.objects.filter(
                        date_added__year = year,
                        date_added__month = month,
                        date_added__day = day
    ).all().count()
    print(context)
    return render(request, 'home.html', context)

def logout_user(request):
    logout(request)
    return redirect('login-page')
    
@login_required
def profile(request):
    context = context_data(request)
    context['page'] = 'profile'
    context['page_title'] = "Profile"
    return render(request,'profile.html', context)


@login_required
def departments(request):
    context = context_data(request)
    context['page'] = 'departments'
    context['page_title'] = "Department List"
    context['departments'] = models.Departments.objects.filter(delete_flag = 0).all()
    return render(request, 'departments.html', context)

@login_required
def save_department(request):
    resp = { 'status': 'failed', 'msg' : '' }
    if request.method == 'POST':
        post = request.POST
        if not post['id'] == '':
            department = models.Departments.objects.get(id = post['id'])
            form = forms.SaveDepartment(request.POST, instance=department)
        else:
            form = forms.SaveDepartment(request.POST) 

        if form.is_valid():
            form.save()
            if post['id'] == '':
                messages.success(request, "Department has been saved successfully.")
            else:
                messages.success(request, "Department has been updated successfully.")
            resp['status'] = 'success'
        else:
            for field in form:
                for error in field.errors:
                    if not resp['msg'] == '':
                        resp['msg'] += str('<br/>')
                    resp['msg'] += str(f'[{field.name}] {error}')
    else:
         resp['msg'] = "There's no data sent on the request"

    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def manage_department(request, pk = None):
    context = context_data(request)
    context['page'] = 'manage_department'
    context['page_title'] = 'Manage Department'
    if pk is None:
        context['department'] = {}
    else:
        context['department'] = models.Departments.objects.get(id=pk)
    
    return render(request, 'manage_department.html', context)

@login_required
def delete_department(request, pk = None):
    resp = { 'status' : 'failed', 'msg':''}
    if pk is None:
        resp['msg'] = 'Department ID is invalid'
    else:
        try:
            models.Departments.objects.filter(pk = pk).update(delete_flag = 1)
            messages.success(request, "Department has been deleted successfully.")
            resp['status'] = 'success'
        except:
            resp['msg'] = "Deleting Department Failed"

    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def users(request):
    context = context_data(request)
    context['page'] = 'users'
    context['page_title'] = "User List"
    context['users'] = User.objects.exclude(pk=request.user.pk).filter(is_superuser = False).all()
    return render(request, 'users.html', context)

@login_required
def save_user(request):
    resp = { 'status': 'failed', 'msg' : '' }
    if request.method == 'POST':
        post = request.POST
        if not post['id'] == '':
            user = User.objects.get(id = post['id'])
            form = forms.UpdateUser(request.POST, instance=user)
        else:
            form = forms.SaveUser(request.POST) 

        if form.is_valid():
            form.save()
            if post['id'] == '':
                messages.success(request, "User has been saved successfully.")
            else:
                messages.success(request, "User has been updated successfully.")
            resp['status'] = 'success'
        else:
            for field in form:
                for error in field.errors:
                    if not resp['msg'] == '':
                        resp['msg'] += str('<br/>')
                    resp['msg'] += str(f'[{field.name}] {error}')
    else:
         resp['msg'] = "There's no data sent on the request"

    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def manage_user(request, pk = None):
    context = context_data(request)
    context['page'] = 'manage_user'
    context['page_title'] = 'Manage User'
    if pk is None:
        context['user'] = {}
    else:
        context['user'] = User.objects.get(id=pk)
    
    return render(request, 'manage_user.html', context)

@login_required
def delete_user(request, pk = None):
    resp = { 'status' : 'failed', 'msg':''}
    if pk is None:
        resp['msg'] = 'user ID is invalid'
    else:
        try:
            User.objects.filter(pk = pk).delete()
            messages.success(request, "user has been deleted successfully.")
            resp['status'] = 'success'
        except:
            resp['msg'] = "Deleting user Failed"

    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def visitors(request):
    context = context_data(request)
    context['page'] = 'visitors'
    context['page_title'] = "Visitor List"
    context['visitors'] = models.Visitors.objects.all()
    return render(request, 'visitors.html', context)

############################################################################
# views.py


# def generate_and_print_report(request):
#     # Fetch data from the database
#     data = visitors.objects.all()  # Replace YourModel with your actual model

#     # Render HTML content using Django template
#     html_content = render_to_string('visitor.html', {'data': data})

#     # Create a unique temporary file
#     with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.html') as temp_file:
#         temp_file.write(html_content)
#         temp_file_path = temp_file.name  # Get the path of the temporary file

#     try:
#         # Call JasperStarter to generate the report
#         subprocess.call(['jasperstarter', 'process', 'path/to/your_report_template.jasper', '-o', 'path/to/output_file.pdf', '-f', 'pdf', '--params', 'htmlContent=' + temp_file_path])

#         # Code to serve or download the generated report
#         with open('path/to/output_file.pdf', 'rb') as report_file:
#             response = HttpResponse(report_file.read(), content_type='application/pdf')
#             response['Content-Disposition'] = 'inline; filename=report.pdf'
#             return response
#     finally:
#         # Clean up: Delete the temporary HTML file after use
#         os.remove(temp_file_path)



# views.py
from django.http import FileResponse
from django.shortcuts import render
from .utils import generate_report

def generate_report_view(request):
    parameters = {
        'param1': 'value1',
        'param2': 'value2',
    }

    output_file = generate_report(parameters=parameters)

    return FileResponse(open(output_file, 'rb'), as_attachment=True)



############################################################################





@login_required
def save_visitor(request):
    resp = { 'status': 'failed', 'msg' : '' }
    if request.method == 'POST':
        post = request.POST
        if not post['id'] == '':
            visitor = models.Visitors.objects.get(id = post['id'])
            form = forms.SaveVisitor(request.POST, instance=visitor)
        else:
            form = forms.SaveVisitor(request.POST) 

        if form.is_valid():
            form.save()
            if post['id'] == '':
                messages.success(request, "Visitor has been saved successfully.")
            else:
                messages.success(request, "Visitor has been updated successfully.")
            resp['status'] = 'success'
        else:
            for field in form:
                for error in field.errors:
                    if not resp['msg'] == '':
                        resp['msg'] += str('<br/>')
                    resp['msg'] += str(f'[{field.name}] {error}')
    else:
         resp['msg'] = "There's no data sent on the request"

    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def manage_visitor(request, pk = None):
    context = context_data(request)
    context['page'] = 'manage_visitor'
    context['page_title'] = 'Manage Visitor'
    if pk is None:
        context['visitor'] = {}
    else:
        context['visitor'] = models.Visitors.objects.get(id=pk)
    context['departments'] = models.Departments.objects.filter(status = 1, delete_flag = 0).all()
    
    return render(request, 'manage_visitor.html', context)
    
@login_required
def view_visitor(request, pk = None):
    context = context_data(request)
    context['page'] = 'manage_visitor'
    context['page_title'] = 'View Visitor Log'
    if pk is None:
        context['visitor'] = {}
    else:
        context['visitor'] = models.Visitors.objects.get(id=pk)
    context['departments'] = models.Departments.objects.filter(status = 1, delete_flag = 0).all()
    
    return render(request, 'view_visit_log.html', context)

@login_required
def delete_visitor(request, pk = None):
    resp = { 'status' : 'failed', 'msg':''}
    if pk is None:
        resp['msg'] = 'Visitor ID is invalid'
    else:
        try:
            models.Visitors.objects.filter(pk = pk).delete()
            messages.success(request, "Visitor has been deleted successfully.")
            resp['status'] = 'success'
        except:
            resp['msg'] = "Deleting Visitor Failed"

    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def report(request):
    context = context_data(request)
    context['page'] = 'visitors'
    context['page_title'] = "التصديقات الجوية- تقرير يومي"
    if 'filter_date' in request.GET:
        date = datetime.datetime.strptime(request.GET['filter_date'],"%Y-%m-%d")
    else:
        date = datetime.datetime.now()
    year = date.strftime('%Y')
    month = date.strftime('%m')
    day = date.strftime('%d')
    context['filter_date'] = date
    context['visitors'] = models.Visitors.objects.filter(
                date_added__year= year,
                date_added__month= month,
                date_added__day= day,
    ).all()
    
    return render(request, 'report.html', context)

