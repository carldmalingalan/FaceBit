import cv2
import numpy as np
from IPcamera import IPconnect

cap = IPconnect('http://192.168.43.1:8080/shot.jpg')

while cap.status and cv2.waitKey(1) != ord('q'):
	n,frame = cap.get_frame()
	print(type(n))
	cv2.imshow('Testing', frame)


cv2.destroyAllWindows()