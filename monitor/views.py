from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages

from datetime import datetime
from .IPcamera import IPconnect 
from .forms import StudentRegisterForm, Configuration
from .models import Student, DataSets, MonitorLog, InternalConfiguration, MonitorLog
from . import apps 
from .tasks import *
from threading import *

import json
import cv2
import base64
import face_recognition

conf = InternalConfiguration.objects.first()

ip_add = conf.ip_webcam
interval = conf.identifier_interval


def monitor_home(request):
	return render(request, 'monitor/home.html')


def print_report(request):
	logs = MonitorLog.print_log_all()
	context = {'data':logs}
	pdf = apps.render_to_pdf('dashboard/log_report.html', context)
	response = HttpResponse(pdf, content_type="application/pdf")
	response['Content-Disposition'] = f"inline;filename='{datetime.now().strftime('%c')}.pdf'"
	return response

def fetch_state(request):

	data = ret_state.delay()
	val = data.get()
	
	temp = [name['id'] for name in val['celery@carl-Lenovo-G40-70'] if name['name'].split('.')[-1] == 'train_data']
	
	ret_val = {'process' : len(temp)}	
	return HttpResponse(json.dumps(ret_val))

def training(request):
	
	liststud = DataSets.valid_student(DataSets.objects)
	dataTrain = Thread(target=apps.train_datasets, args=(liststud,))

	if not dataTrain.isAlive():
		dataTrain.start()

	return HttpResponse('Initializing')

def settings(request):
	form = InternalConfiguration.objects.first()
	if request.method == "POST":
		temp_form = Configuration(request.POST)
		if temp_form.is_valid:
			form.ip_webcam = request.POST['ip_webcam']
			form.identifier_interval = request.POST['identifier_interval']
			form.save()
	
	# print(form.identifier_interval)
	context = {
		'form': form,
		'title': {
			'main' : 'Settings',
			'text' : 'This is internal configuration of the system',
		}
	}
	return render(request, 'dashboard/settings.html', context)

def logs(request):
	log_list = MonitorLog.log_all_for_view()
	context = {
		'form' : log_list,
		'title': {
			'main': 'Student Logged Records',
			'text': "Here's all the record of all student whose been identified in the monitor."
		}
	}

	return render(request, "dashboard/logs.html", context)

def dashboard(request):
	form = Student.objects.all()
	context = {
		"form": form,
		"title": {
				"main": 'Student Information',
				"text": 'Master record of all existing registered students.'
				}
	}
	return render(request, 'dashboard/home.html', context)

def profile_dataset_save(request):
	student = Student.objects.get(id=request.POST['id'])
	for data in request.FILES:
		
		if apps.list_image_count(student.student_number) >= 10: 
			break

		create = DataSets.objects.create(student_info = student, dataset_image = request.FILES[data])		
	return HttpResponse(request)


def profile_register(request, pk):
	data = Student.objects.get(id=pk)
	return render(request, 'monitor/training_student.html', {'form': data, 'images': apps.list_image(data.student_number)})


def register_student(request):
	if request.method == "POST":
		student = StudentRegisterForm(request.POST, request.FILES)
		if student.is_valid():
			student.save()
			id = Student.objects.latest('id')
			return redirect('register-profile', pk=id.id)
		messages.error(request, "Some fields aren't supposed to be left empty.")		
	else:	
		student = StudentRegisterForm()
	
	return render(request, 'monitor/register_student.html', {'form': student})

def delete_student(request, pk):
	Student.objects.get(id=pk).delete()
	return redirect('dashboard')



def monitor_stream(request):
	#Connecting thru IP Camera
	if len(ip_add) and interval >= 5:
		cap = IPconnect(ip_add)
		frame = cap.get_frame()
		if cap.status:
			ratio = 120
			color = (0,0,255)
			
			rh = int(cap.height / 2)
			rw = int(cap.width / 2)
			rgb = frame[:,:,::-1]
			
			roi_face = rgb[rh-ratio:rh+ratio, rw-ratio: rw+ratio]
			detect_something = face_recognition.face_locations(roi_face,model='hog')
			
			if len(detect_something):
				apps.log_face(roi_face, detect_something, interval)
				color = (0,255,0)

			#Left part (Broken Rectangle)
			cv2.line(frame,(rw-ratio,rh-ratio),(rw-int(ratio / 2),rh-ratio),color,2)
			cv2.line(frame,(rw-ratio,rh-ratio),(rw-ratio,rh-int(ratio / 2)),color,2)
			cv2.line(frame,(rw-ratio,rh+ratio),(rw-ratio,rh+int(ratio / 2)),color,2)
			cv2.line(frame,(rw-ratio,rh+ratio),(rw-int(ratio / 2),rh+ratio),color,2)

			#Right part (Broken Rectangle)
			cv2.line(frame,(rw+ratio,rh-ratio),(rw+int(ratio / 2),rh-ratio),color,2)
			cv2.line(frame,(rw+ratio,rh-ratio),(rw+ratio,rh-int(ratio / 2)),color,2)
			cv2.line(frame,(rw+ratio,rh+ratio),(rw+ratio,rh+int(ratio / 2)),color,2)
			cv2.line(frame,(rw+ratio,rh+ratio),(rw+int(ratio / 2),rh+ratio),color,2)

			#Converting the frame to jpg
			_, frame_buff = cv2.imencode('.jpg', frame)
			
			#Converting jpg to base64
			frame64 = base64.b64encode(frame_buff).decode('utf-8')
			
			#Craeting a dict for json.dumps, 
			elements = {'main': frame64}

			data = json.dumps(elements)
			return HttpResponse(data)
