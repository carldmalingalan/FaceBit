from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages

from datetime import datetime
from .IPcamera import IPconnect 
from .forms import StudentRegisterForm
from .models import Student, DataSets
from . import apps 
from .tasks import *

import json
import cv2
import base64
import face_recognition

def monitor_home(request):
	return render(request, 'monitor/home.html')

def fetch_state(request):

	data = ret_state.delay()
	val = data.get()
	
	temp = [name['id'] for name in val['celery@carl-Lenovo-G40-70'] if name['name'].split('.')[-1] == 'train_data']
	
	ret_val = {'process' : len(temp)}	
	return HttpResponse(json.dumps(ret_val))

def training(request):
	
	liststud = DataSets.valid_student(DataSets.objects)
	data = train_data.delay(liststud)

	return HttpResponse(json.dumps(data.get()))
	


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
	cap = IPconnect('http://192.168.43.1:8080/shot.jpg')
	frame = cap.get_frame()
	
	ratio = 120
	color = (0,0,255)
	
	rh = int(cap.height / 2)
	rw = int(cap.width / 2)
	rgb = frame[:,:,::-1]
	
	roi_face = rgb[rh-ratio:rh+ratio, rw-ratio: rw+ratio]
	detect_something = face_recognition.face_locations(roi_face,model='hog')
	
	if len(detect_something):
		# Uncomment if training is done
		apps.log_face(roi_face, detect_something)
		color = (0,255,0)

	#Execute in the background
	#Face Recognition
	# var = json.dumps(frame.tolist())
	# identify_face.delay(var)

	# frame_with_box = apps.detect_faces(frame)

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
