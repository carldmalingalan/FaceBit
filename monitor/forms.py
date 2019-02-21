from django import forms
from .models import Student, DataSets

class StudentRegisterForm(forms.ModelForm):
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




