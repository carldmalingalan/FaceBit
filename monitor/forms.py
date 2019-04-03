from django.forms import ModelForm
from django import forms
from .models import Student, DataSets, InternalConfiguration

class StudentRegisterForm(ModelForm):
	middle_initial = forms.CharField(required=False)

	class Meta:
		model = Student
		fields = [
			'student_number',
			'student_course',
			'first_name',
			'middle_initial',
			'last_name',
			'profile_picture',
		]

class Configuration(ModelForm):
	class Meta:
		model = InternalConfiguration
		fields = [
			'ip_webcam',
			'identifier_interval',
		]



