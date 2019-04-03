from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from PIL import Image, ExifTags

from FaceBit import settings
from . import apps


import os
import shutil
import json
import face_recognition

#Course starts here
class Course(models.Model):
	course_name = models.CharField(max_length=255)

	def __str__(self):
		return f"{self.course_name}"
#Ends here

#Start of InternalConfiguration

class InternalConfiguration(models.Model):
	TIME = (
		(5, '5 Seconds'),
		(10, '10 Seconds'),
		(15,'15 Seconds'),
		(30, '30 Seconds'),
		(60, '1 Minute'),
		)
	ip_webcam = models.CharField(max_length=255)
	identifier_interval = models.IntegerField(choices=TIME, default='5 Seconds')

	# def __str__(self):
	# 	return f"{self.ip_webcam} => {self.indentifier_interval} secs"

#Ends here

#Student starts here
def user_directory_path(instance, filename):
	split = filename.split('.')
	split[0] = instance.student_number
	temp = ".".join(split)
	filename = temp
	return os.path.join('student_profile_image', filename)

class Student(models.Model):
	student_number_format = RegexValidator(regex=r"^20{1,2}[1-2][0-9]-[0-9]{6}", message="Please enter a valid student number (example:2019-123456)")
	student_number 	= models.CharField(validators=[student_number_format], max_length=11, blank=True, unique=True, help_text="Student number must be this format 20YY-99999")
	student_course  = models.ForeignKey(Course, on_delete=models.CASCADE)
	first_name     	= models.CharField(max_length=255)
	middle_initial  = models.CharField(max_length=2)
	last_name	   	= models.CharField(max_length=255)
	profile_picture = models.ImageField(upload_to=user_directory_path)
	date_registered = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"{self.id}:{self.student_number} => {self.first_name} {self.middle_initial}, {self.last_name}"

	def get_absolute_url(self):
		return reverse('register-profile', kwargs={'pk': self.id})

	def delete(self):
		try:
			os.remove(self.profile_picture.path)
			shutil.rmtree(os.path.join(settings.DATASETS_DIR, self.student_number))
			super(Student, self).delete()
		except OSError as e:
			print(f"[ERROR] => {e}")	

	def save(self, *args, **kwargs):
		super(Student, self).save(*args, **kwargs)
		os.mkdir(os.path.join(settings.DATASETS_DIR,self.student_number))
		apps.crop_face_thumbnail(self.profile_picture.path)		
		StudentEncoding.objects.create(student_info=self, student_encoding=apps.quick_encode(self.profile_picture.path))

	@property
	def full_name(self):
		m = " "
		m += (self.middle_initial + ". ") if self.middle_initial else ""
		return self.first_name + m + self.last_name

#Ends Here

#DataSets starts here
def dataset_directory_path(instance, filename):
	ext      = filename.split('.')[-1]
	count    = apps.list_image_count(instance.student_info.student_number)
	filename = f"{instance.student_info.student_number}-{count}.{ext}"
	return os.path.join(os.path.join(settings.DATASETS_DIR,instance.student_info.student_number),filename)

class DataSets(models.Model):
	student_info  = models.ForeignKey(Student, on_delete=models.CASCADE)
	dataset_image = models.ImageField(upload_to=dataset_directory_path)
	date_upload   = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return self.student_info.full_name

	def valid_student(self):
		valid = self.values('student_info').annotate(entries=models.Count('student_info')).filter(entries__gte=5)
		student = [Student.objects.get(id=stud_num['student_info']).student_number for stud_num in valid]
		return student

	def save(self, *args, **kwargs):
		super(DataSets, self).save(*args, **kwargs)
		
		#Fetching the student profile picture encodings
		enc = StudentEncoding.objects.get(student_info=self.student_info).student_encoding
		
		#Checking if image is rotated
		try:
		    image=Image.open(self.dataset_image.path)
		    for orientation in ExifTags.TAGS.keys():
		        if ExifTags.TAGS[orientation]=='Orientation':
		            break
		    exif=dict(image._getexif().items())

		    if exif[orientation] == 3:
		        image=image.rotate(180, expand=True)
		    elif exif[orientation] == 6:
		        image=image.rotate(270, expand=True)
		    elif exif[orientation] == 8:
		        image=image.rotate(90, expand=True)
		    image.save(self.dataset_image.path)
		    image.close()

		except (AttributeError, KeyError, IndexError):
		    # cases: image don't have getexif
		    pass

		#Testing if the picture is a valid image
		if apps.quick_compare(enc, self.dataset_image.path) is False:
			self.delete()

	def delete(self):
		try:
			if os.path.isfile(self.dataset_image.path):
				os.remove(self.dataset_image.path)
				super(DataSets, self).delete()
		except OSError as E:
			print(f'[ERROR] => {E}')
		
#Ends here

#Student Encodings starts here
class StudentEncoding(models.Model):
	student_info 	 = models.OneToOneField(Student, on_delete=models.CASCADE)
	student_encoding = models.TextField()


	def __str__(self):
		return self.student_info.full_name

#Ends here


#MonitorLogs starts here

class MonitorLog(models.Model):
	student_number = models.CharField(max_length=11, default='Unknown', unique=False)
	log_image	   = models.ImageField() 
	log_time	   = models.DateTimeField(default=timezone.now)

	def delete(self):
		try:
			if os.path.isfile(self.log_image.path):
				os.remove(self.log_image.path)
				super(MonitorLog, self).delete()
		except OSError as E:
			print(f"[ERROR] => {E}")
			
	def log_info_batch():
		to_display = []
		logged = MonitorLog.objects.distinct().order_by('-log_time')
		for data in logged:
			student_inst = Student.objects.get(student_number=data.student_number)
			clean_data = {
				'student_number'  : data.student_number,
				'student_name'	  : student_inst.full_name,
				'student_img_url' : student_inst.profile_picture.url,
				'logged_img_url'  : "/"+"/".join(data.log_image.path.split('/')[-3:]),
				'logged_time'	  : data.log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%I:%M:%S %p'),
				'logged_date'	  : data.log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%B %d, %Y'),
				}
			to_display.append(clean_data)
		return to_display

	def latest_log_info():
		to_display = []
		logged = MonitorLog.objects.distinct().order_by('-log_time')[:1]
		for data in logged:
			student_inst = Student.objects.get(student_number=data.student_number)
			clean_data = {
				'student_number'  : data.student_number,
				'student_name'	  : student_inst.full_name,
				'student_img_url' : student_inst.profile_picture.url,
				'logged_img_url'  : "/"+"/".join(data.log_image.path.split('/')[-3:]),
				'logged_time'	  : data.log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%I:%M:%S %p'),
				'logged_date'	  : data.log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%B %d, %Y'),
			}
			to_display.append(clean_data)
		return to_display

	def log_all_for_view():
		to_display = []
		temp_data = {}
		data = MonitorLog.objects.all().order_by('-log_time')
		#Iterate thru all the data in the MonitorLog table
		'''
			See if the student name is present in the temporary data
			I use this temp_data so that for every iteration if the 
			the student number has been processed in the previous iteration
			then it woundn't fetch the data from the datebase so that it execution time
		'''
		for element in data:
			student_name = temp_data.get(element.student_number, False)
			if not student_name:
				student_name = Student.objects.get(student_number=element.student_number).full_name
				temp_data[element.student_number] = student_name

			ret_data = {
				'image': "/"+"/".join(element.log_image.path.split('/')[-3:]),
				'student_number': element.student_number,
				'name' : student_name,
				'logged_datetime' : element.log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%B %d, %Y/%I:%M:%S %p'),
			}
			to_display.append(ret_data)

		return to_display

	def print_log_all():
		to_display = []
		temp_data = {}
		data = MonitorLog.objects.all().order_by('-log_time')
		#Iterate thru all the data in the MonitorLog table
		'''
			See if the student name is present in the temporary data
			I use this temp_data so that for every iteration if the 
			the student number has been processed in the previous iteration
			then it woundn't fetch the data from the datebase so that it execution time
		'''
		for element in data:
			student_name = temp_data.get(element.student_number, False)
			if not student_name:
				student_name = Student.objects.get(student_number=element.student_number).full_name
				temp_data[element.student_number] = student_name

			ret_data = {
				'student_number': element.student_number,
				'name' : student_name,
				'logged_date' : element.log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%B %d, %Y'),
				'logged_time' : element.log_time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%I:%M:%S %p"),
			}
			to_display.append(ret_data)

		return to_display

	def __str__(self):
		return f"{self.student_number}"

@receiver(post_save, sender=MonitorLog)
def display_to_front(sender, **kwargs):
	if kwargs.get('created', False):
		channel_layer = get_channel_layer()
		async_to_sync(channel_layer.group_send)(
			"logStatus", {
				'type': "logStatus.newEntry",
				'event': "New Entry",
				'log_data': json.dumps(MonitorLog.latest_log_info()),
			}
			)
	
# Ends here