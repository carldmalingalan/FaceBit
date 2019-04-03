from django.apps import AppConfig
from FaceBit import settings
from PIL import Image
from . import models
from datetime import datetime, timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template

from xhtml2pdf import pisa

import json
import cv2
import numpy as np
import face_recognition
import os
import pickle
import uuid


class MonitorConfig(AppConfig):
    name = 'monitor'

    def ready(self):
    	import monitor.signals

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def train_datasets(stud_list):
	file_list = {}
	result = {'status':None}
	if len(stud_list):
		file = pickle.loads(open(settings.TRAINING_FILE_DIR, 'rb').read())
		
		for data in stud_list:
			if not data in file['student_number']:
				is_valid = os.listdir(os.path.join(settings.DATASETS_DIR, data))
				if len(is_valid) >= 5:
					file_list[data] = [os.path.join(os.path.join(settings.DATASETS_DIR, data),path) for path in os.listdir(os.path.join(settings.DATASETS_DIR, data))]

		if len(file_list):
			for stud_num in file_list:
				for path in file_list[stud_num]:
					img = cv2.imread(path)
					rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

					boxes = face_recognition.face_locations(rgb, model="hog")
					encs = face_recognition.face_encodings(rgb, boxes, num_jitters=5)
					for enc in encs:
						file['encodings'].append(enc)
						file['student_number'].append(stud_num)

				file_data = open(settings.TRAINING_FILE_DIR, 'wb')
				file_data.write(pickle.dumps(file))
				file_data.close()

			result['status'] = 'Finished training!'

		else:
			result['status'] = 'Nothing to train.'

		channel_layer = get_channel_layer()
		async_to_sync(channel_layer.group_send)("training",{
				'type':'training.status',
				'event': 'Status Report',
				'log_data': json.dumps(result)
			})
		



def log_face(roi, faces, interval):
	master_enc = pickle.loads(open(settings.TRAINING_FILE_DIR, 'rb').read())

	face_encs = face_recognition.face_encodings(roi, faces)
	names = []
	for enc in face_encs:
		matches = face_recognition.compare_faces(master_enc['encodings'], enc)
		name = "Unknown"

		if True in matches:
			matchIds = [index for index, value in enumerate(matches) if value]
			count = {}

			for ind in matches:
				name = master_enc['student_number'][ind]
				count[name] = count.get(name, 0) + 1

			name = max(count, key=count.get)
			names.append(name)
	print(names)
	for ((top, right, bottom, left), name) in zip(faces, names):
		if name == 'dummy':
			continue
		print(name)
		#Fetch the student log information
		student_id = models.MonitorLog.objects.filter(student_number=name).order_by('-log_time')

		# See if QuerySet isn't empty
		if not len(student_id):
			uniq_id = uuid.uuid4()
			file_path = os.path.join(settings.LOGS_ROOT, f"{uniq_id}.jpg")
			file_picture = cv2.resize(cv2.cvtColor(roi[top:bottom, left:right], cv2.COLOR_RGB2BGR), (150,150), interpolation=cv2.INTER_AREA)
			cv2.imwrite(file_path, file_picture)		
			student = models.MonitorLog.objects.create(student_number = name, log_image=file_path)
			student.save()
			continue
		# if Student is lo
		total_diff = (datetime.now() - student_id[0].log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).replace(tzinfo=None))
		print(total_diff)
		# print(f"Student Latest Entry => {student_id[0].log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).replace(tzinfo=None).strftime('%c')}, Current Time => {datetime.now().strftime('%c')}, Total Difference => {total_diff}")
		if len(student_id) and int(abs(total_diff.total_seconds())) > interval:	
		# Uncomment if training is fixed
			uniq_id = uuid.uuid4()
			file_path = os.path.join(settings.LOGS_ROOT, f"{uniq_id}.jpg")
			file_picture = cv2.resize(cv2.cvtColor(roi[top:bottom, left:right], cv2.COLOR_RGB2BGR), (150,150), interpolation=cv2.INTER_AREA)
			cv2.imwrite(file_path, file_picture)		
			student = models.MonitorLog.objects.create(student_number = name, log_image=file_path)
			student.save()
			continue

		

#Crop uploaded profile picture
def crop_face_thumbnail(path):
	try:

		#Loads image from OpenCV
		img = cv2.imread(path, cv2.IMREAD_COLOR)
		rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
		#Resize image to 1/4 of its size
		rgb = cv2.resize(rgb, (0,0), fx=0.25, fy=0.25)

		#Convert to RGB *face_recognition default
		small_frame = rgb[:, :, ::-1]

		#Locating faces inside the image
		small_locs = face_recognition.face_locations(rgb, model='hog')

		#Get a portion of the frame
		ratio_y = int(img.shape[0] / 16)
		ratio_x = int(img.shape[1] / 16)
		face = None

		
		for (top, right, bottom, left) in small_locs:
		    top   *= 4
		    left  *= 4
		    bottom*= 4
		    right *= 4
		    face = img[top-(ratio_y*2):bottom+ratio_y, left-ratio_x:right+ratio_x]
		if face.shape[0] > 300 or face.shape[1] > 300:
			face = cv2.resize(face, (300,300), interpolation = cv2.INTER_AREA)

		cv2.imwrite(path, face)

	except Exception as e:
		return e

#Datasets image path
def list_image(student_num):
	try:
		
		#Processing the student datasets directory path
		d_path = os.path.join(settings.DATASETS_DIR, student_num)
		items = []

		#If there's a file inside the dataset folder of the student
		if len(os.listdir(d_path)):

			#Creating a list key paired for template 
			items = [
				{
					'url': os.path.join(os.path.join(settings.DATASETS_URL, student_num), filename), 
					'filename': filename
				} 
				for filename in os.listdir(d_path)
			]
		return items

	#Too ambigous *for future change
	except Exception as e:
		return e

#Datasets image counter
def list_image_count(student_num):
	try:
		
		#Processing the student datasets directory path
		d_path = os.path.join(settings.DATASETS_DIR, student_num)
		count = 0

		#If there's file inside the dataset folder of the student
		if len(os.listdir(d_path)):

			#Max number images inside the list
			count = max(enumerate(os.listdir(d_path)))[0] + 1
		return count + 1 if count == 0 else count

	#Too ambigous *for future change
	except Exception as e:
		return e

#Single encode
def quick_encode(path):
	try:
		#Load image
		face_img = face_recognition.load_image_file(path)

		#Encode image and converting to a list for json compatability
		face_enc = face_recognition.face_encodings(face_img)[0].tolist()

		#Returning as json string
		return json.dumps(face_enc)

	#Too ambigous *for future change
	except Exception as E:
		return E


#Compare student profile picture to uploaded image
def quick_compare(student_enc, picture_path):

	#Load profile student encodings making it numpy array
	stud_enc    = [np.array(json.loads(student_enc))]
	
	#Loads picture want to validate
	picture     = face_recognition.load_image_file(picture_path)
	
	#Getting a portion of the image size
	ratio_y = int(picture.shape[0] / 16)
	ratio_x = int(picture.shape[1] / 16)

	#Converting image to 1/4 of its size
	#for better performance
	small_frame = cv2.resize(picture, (0,0), fx=0.25, fy=0.25)

	#Then converting to RGB *face_recognition default
	rgb_small_frame = small_frame[:, :, ::-1]

	#Locating faces in the image
	face_locs   = face_recognition.face_locations(rgb_small_frame, model='hog')

	#Resizing coordinates
	face_locs   = [(w*4,x*4,y*4,z*4) for (w,x,y,z) in face_locs]
	
	#Encode the picture
	picture_enc = face_recognition.face_encodings(picture, face_locs)

	stats = []

	#Iterating thru the face encoding that detected within the image
	for (i,encoding) in enumerate(picture_enc):
		matches = face_recognition.compare_faces(stud_enc, encoding)
		if True in matches:
			stats.append(i)
	
	#If there is face that is valid overwrite the current with the validated image
	if len(stats):
		container = [face_locs[stats[0]]]
		for (top, right, bottom, left) in container:
			
			#Converting image to BGR *OpenCV default
			img = cv2.cvtColor(picture[top:bottom, left:right], cv2.COLOR_RGB2BGR)

			#Saving the just the portion of the image with the validated face only
			cv2.imwrite(picture_path, img)

	#Returning state if there is a face validated to the student profile picture
	return True if len(stats) else False
