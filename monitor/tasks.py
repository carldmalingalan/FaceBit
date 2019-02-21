from celery import shared_task
from celery.task.control import inspect
from FaceBit import settings
from FaceBit.celery import app
from . import models


import time
import os
import pickle
import cv2
import face_recognition
import json
import uuid
import numpy as np

@shared_task
def ret_state():
	ins = app.control.inspect()
	return ins.active()

@shared_task
def train_data(stud_list):
	file_list = {}
	status = False
	if len(stud_list):
		file = pickle.loads(open(settings.TRAINING_FILE_DIR, 'rb').read())
		for data in stud_list:
			if data not in file['student_number']:
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

			return {'status': 'finish'}

		return {'status': "Nothin to add"}





@shared_task
def identify_face(arr):
	#Convert the arr [list] to numpy.array
	new_arr   = np.array(json.loads(arr), dtype="uint8")

	#convert BGR to RGB
	rgb   = new_arr[:,:,::-1]

	#Detect coordinates of faces inside the image
	faces = face_recognition.face_locations(rgb, model='hog')

	if len(faces):
		return None

	#Loads the master encodings
	master_encodings = pickle.loads(open(settings.TRAINING_FILE_DIR, 'rb').read())

	

	#Encode the faces present in the image
	enc   = face_recognition.face_encodings(rgb, faces)

	#Put it in a list
	main_enc = [encs for encs in enc]

	#Declare a empty list
	names = []

	#Iterate thru all the encodings
	for encoding in main_enc:

		#Compare the faces in the image with the face in the master encodings
		matches = face_recognition.compare_faces(master_encodings['encodings'], encoding)

		#Constant name value if face is not present in the master encodings
		name = 'Unknown'

		#If there is a match inside the encodings
		if True in matches:

			#Compile all indexes of all encodings that comes out true
			encIds = [encIndex for (encIndex, value) in enumerate(matches) if value]

			#Declare and empty dict for tally of the result
			counts = {}

			#Iterate from all the indexes gathered
			for num in encIds:

				#Get the corresponding student number of the encoding that come out True
				name = master_encodings['student_number'][num]

				#Append it or Incement it inside the dict
				counts[name] = counts.get(name, 0) + 1

			#Fetch the student number of the highest possible face
			name = max(counts, key=counts.get)
			names.append(name)

	for ((top, right, bottom, left), stud_num) in zip(faces, names):

		#Pre-define the path location of the image
		file_path = os.path.join(settings.LOGS_ROOT, f"{uuid.uuid4()}.png")

		#Convert the image size to fix 150x150
		file_picture = cv2.resize(new_arr[top:bottom, left:right], (150,150), interpolation=cv2.INTER_AREA)
		cv2.imwrite(file_path, file_picture)

	return f"{names}"

		# PIL image resizing and saving
	    # file_picture = Image.fromarray(arr[top:bottom, left:right])
		# file_picture.resize((150,150), Image.ANTIALIAS)
		# file_picture.save(file_path)

		# if stud_num != "Unknown":
		# 	stud_ins = models.Student.objects.get(student_number=stud_num)
		# 	models.MonitorLog.objects.create(student_info=stud_ins, log_image=file_path)
		# else:
		# 	models.MonitorLog.objects.create(log_image=file_path)