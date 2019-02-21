import urllib
import urllib.request
import numpy as np
import cv2

class IPconnect():

    
    def __init__(self,ip):
        self.ip = ip
        self.result = None
        self.img_array = None
        self.frame = None
        self.dtype = np.uint8
        self.stream()
        
    
    def get_frame(self):
        try:
            self.stream()
            if self.result:
                self.img_array = np.asarray(bytearray(self.result), dtype = self.dtype)
                self.frame = cv2.imdecode(self.img_array,-1)
                return self.frame
            else:
                return False
        except KeyboardInterrupt:
            print('Message: Connection stopped => {}'.format(self.ip))
        
    
    def stream(self):
        try:
            self.result =  urllib.request.urlopen(self.ip).read()

        except Exception as e:
            self.result = False
            print("[ERROR]: {}".format(e))

        if self.result is None or self.result is False:
            print("[ERROR]: Can't connect to IP Camera => {}".format(self.ip))

    @property
    def status(self):
        return True if self.result else False

    @property
    def height(self):
        return self.frame.shape[0] if self.result else False
    
    @property
    def width(self):
        return self.frame.shape[1] if self.result else False


