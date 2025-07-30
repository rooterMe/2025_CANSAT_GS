#라이브러리 import
import numpy as np
import cv2
import sys
import serial
import threading
import time
import datetime as dt
import csv
import os
import base64
from queue import Queue
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon, QPixmap, QImage
from PyQt5.QtWidgets import *
from PyQt5 import uic
import copy
from PIL import Image, ImageFile
from io import BytesIO
ImageFile.LOAD_TRUNCATED_IMAGES = True

form_class = uic.loadUiType("cansat2025_QtDs.ui")[0]

csv_data = []
img_txt = []
foldername = ''


# 데이터 수신(thread)
def read_data(ser, queue):
    data = b''
    flag = False
    try:
        while True:
            if ser and ser.isOpen():
                raw_data = ser.read()

                #print(raw_data) 
                
                

                if raw_data == b'\r':
                    flag = True

                elif raw_data == b'\n':
                    if flag == True:
                        if len(data)>1:
                            queue.put(data)
                            print(data)
                        data= b''
                        flag = False
                    else:
                        data += b'\n'

                elif  raw_data != b'':
                    if flag:
                        data += b'\r'
                        flag = False
                    #data += str(raw_data)[2:-1]
                    data += raw_data

    except Exception as e:
        print(f"Error reading data: {e}")

class WindowClass(QMainWindow, form_class):

    # init
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pushButton_connect.clicked.connect(self.connectSerial)
        self.pushButton_disconnect.clicked.connect(self.disconnectSerial)
        self.pushButton_BTscan.clicked.connect(self.BT_scan)
        self.pushButton_BTINQ.clicked.connect(self.BT_INQ)
        self.pushButton_ATZ.clicked.connect(self.ATZ)
        self.pushButton_UARTCONFIG.clicked.connect(self.UARTCONFIG)
        self.pushButton_ATplus.clicked.connect(self.ATplus)
        self.pushButton_ATH.clicked.connect(self.ATH)
        self.pushButton_ATD.clicked.connect(self.ATD)
        self.pushButton_sendCMD.clicked.connect(self.chk_user_CMD)
        self.pushButton_save_csv.clicked.connect(self.save_csv)

        self.queue = Queue()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkQueue)
        self.timer.timeout.connect(self.show_GsTime)
        self.timer.timeout.connect(self.reconnect)
        self.timer.start(3)

        self.initUI()

    def initUI(self):
        for i in range(1, 14):
            self.CB_port.addItem("COM" + str(i))

        self.CB_baudrate.addItems(["1200","2400", "4800", "9600", "38400", "57600", "115200","230400","460800","921600"])

        self.setWindowTitle("cansat 2025 GS")
        self.setWindowIcon(QIcon('cansat_icon_tmp.png'))

        # CAM0, CAM1
        self.pixmap = QPixmap("cam_default0")
        scaled_pixmap = self.pixmap.scaled(600, 450, Qt.KeepAspectRatio)
        self.label_image_left.setPixmap(scaled_pixmap)

        self.pixmap = QPixmap("cam_default1")
        scaled_pixmap = self.pixmap.scaled(600, 450, Qt.KeepAspectRatio)
        self.label_image_right.setPixmap(scaled_pixmap)

        # GPS map
        self.show_GPS_map(0,0)

        self.ser = None
        self.connect = False
        self.thread = None

        self.sendATD = False
        self.sendATH = False

        self.IMU_data = ''

        self.can_time=''

        self.folder_name = ''
        self.Lattitue = -1
        self.Longitude = -1
        self.Altitude = -1

        self.reconnect_cnt = 0
    
    def show_GsTime(self):
        self.KST = str(dt.datetime.now())[11:22]
        self.label_gstime.setText("GS Time : "+self.KST)

    # 시리얼 연결
    def connectSerial(self):
        try:
            if self.ser and self.ser.isOpen():
                self.ser.close()

            port = self.CB_port.currentText()
            baudrate = int(self.CB_baudrate.currentText())
            try:
                self.ser = serial.Serial(port, baudrate, timeout=1)
                self.lineEdit.setText(f"Connected to {port} with {baudrate} baudrate")
                self.label_Port.setText(f"Port: {port}")
                self.label_Baudrate.setText(f"Baudrate: {baudrate}")
                self.label_Serial_connect.setText("Serial connect : True")
                print(f"Connected to {port} with {baudrate} baudrate")
                self.connect = True
                
                # thread 시작
                if self.thread is None:
                    self.thread = threading.Thread(target=read_data, args=(self.ser, self.queue), daemon=True)
                    self.thread.start()

            except serial.SerialException as e:
                self.lineEdit.setText(f"Failed to connect to {port}: {e}")
                print(f"Failed to connect to {port}: {e}")
                self.ser = None

        except Exception as e:
            self.lineEdit.setText(f"Unexpected error: {e}")
            print(f"Unexpected error: {e}")
    
    def disconnectSerial(self):
        try:
            if self.ser and self.ser.isOpen():
                self.thread.join(timeout=1)
                self.thread = None

                self.ser.close()
                self.label_Port.setText("Port: ")
                self.label_Baudrate.setText("Baudrate: ")
                self.lineEdit.setText("Serial disconnected")
                print("Serial disconnected")
                self.label_Serial_connect.setText("Serial connect : False")
                self.connect = False

        except Exception as e:
            print(f"{e}")

    # 송신부
    def chk_user_CMD(self):
        cmd = self.lineEdit_sendCMD.text()
        self.send_user_CMD(cmd)

    def send_user_CMD(self, cmd):
        #cmd = self.lineEdit_sendCMD.text() 
        i=8
        while i<len(cmd) and self.ser and self.ser.isOpen():
            self.ser.write(f'{cmd[i-8:i]}'.encode())
            i+=8

        if self.ser and self.ser.isOpen():
            self.ser.write(f'{cmd[i-8:]}\r\n'.encode())
            print(f"send : {cmd}")

        self.label_sendCMD.setText(f"send : {cmd}") 

    # 수신부
    def checkQueue(self):
        if not self.queue.empty():
            data = self.queue.get()
            self.process_data(data)

    # 데이터 처리 
    def process_data(self, data):
        try:
            global csv_data
            if data: 
                #self.lineEdit_SerialRead.setText(f"{data}")
                #print(data[:20])

                decoded = data.decode()

                # IMU
                if decoded[0]=='*':
                    value = ('IMU,'+decoded[1:]).split(',')
                    self.IMU_data = copy.deepcopy(value)
                    value.insert(1,self.KST)
                    csv_data.append(value)
                    self.show_IMU(self.IMU_data)
                
                # GPS
                elif decoded[0]=='$':
                    value = ['GPS',*(decoded.split(',')[1:])]
                    self.show_GPS(value)
                        
                
                # TIME
                elif decoded[0]=='%':
                    self.show_CanTime(decoded.strip('%'))

                # CAM
                elif decoded[0]=='&':
                    global img_txt
                    img_txt.append(str(data[2:].hex()))
                    
                    #csv_data.append([f"CAM{decoded[1]}", f"{self.KST}"])

                    self.decoding_image(str(data[2:].hex()), decoded[1])

                # COMMON
                else:
                    self.common_data(decoded)
                    

        except Exception as e:
            print(f"Error processing data: {e}")

    def common_data(self, data):
        #print(data)
        self.lineEdit_SerialRead.setText(f"{data}, {self.KST}")

        sentence = data.split(' ')

        if sentence[0] == 'CONNECT':
            self.label_Bluetooth_connect.setText("Bluetooth connect : True")
            self.label_Bluetooth_ID.setText(f"Bluetooth ID : {sentence[1]}")

            self.sendATH = False
            self.sendATD = False
            
            today = str(dt.datetime.now())
            today = today.replace('-','')
            today = today.replace(':','')
            today = today.replace('.','')
            today = today.replace(' ','-')
            current = today[:15] 
            os.makedirs(f"cansat_data_{current[:8]}/{current[9:]}")
            os.makedirs(f"cansat_data_{current[:8]}/{current[9:]}/camera0")
            os.makedirs(f"cansat_data_{current[:8]}/{current[9:]}/camera1")

            self.folder_name = f"cansat_data_{current[:8]}/{current[9:]}"
            global foldername
            foldername = self.folder_name

            print(self.folder_name)

        if sentence[0] == 'DISCONNECT':
            self.label_Bluetooth_connect.setText("Bluetooth connect : False")
            self.label_Bluetooth_ID.setText("Bluetooth ID : ")
            self.sendATD = True

            self.save_csv()
        
    def show_CanTime(self, value):
        self.can_time = f'{value[9:11]}:{value[11:13]}:{value[13:15]}.{value[15:17]}'
        self.label_cantime.setText("Can Time : "+self.can_time)

        global csv_data

        value = ['TIME',self.KST,self.can_time]
        csv_data.append(value)
    
    def show_IMU(self, value):
        try: 
            self.label_yaw.setText(f"yaw : {value[1]}")
            self.label_pitch.setText(f"pitch : {value[2]}")
            self.label_roll.setText(f"roll : {value[3]}")
            self.label_a_X.setText(f"aX : {value[7]}")
            self.label_a_Y.setText(f"aY : {value[8]}")
            self.label_a_Z.setText(f"aZ : {value[9]}")
            self.label_Diff_X.setText(f"DiffX : {value[10]}")
            self.label_Diff_Y.setText(f"DiffY : {value[11]}")
            self.label_Diff_Z.setText(f"DiffZ : {value[12]}")

        except Exception as e:
            print(f"IMU error: {e}")

    def show_GPS(self, value):
        try:
            # 위도, 경도, 고도 UI 표시
            if value[1]!='':
                self.label_Lattitue.setText(f"Lattitue : {value[1]}N")
            if value[3]!='':
                self.label_Longitude.setText(f"Longitude : {value[3]}E")
            if value[9]!='':
                # if self.Altitude == -1:
                #     self.Altitude = float(value[9])
                self.label_Altitude.setText(f"Altitude : {float(value[9])}")

            if value[7]!='':
                self.label_Satellites_Used.setText(f"Satellites Used : {value[7]}")

            # GPS map 표시
            if value[1]!='' and value[3]!='':
                if self.Lattitue == -1 and self.Longitude == -1:
                    self.Lattitue = float(value[1])
                    self.Longitude = float(value[3])
                
                self.show_GPS_map(float(value[1])-self.Lattitue, float(value[3])-self.Longitude)

            global csv_data
            value.insert(1,self.KST)
            csv_data.append(value)
        
        except Exception as e:
            print(f"GPS error: {e}")

    def create_GPS_map(self, Lat, Lon):
        GPSmap = np.zeros((440, 440, 3), dtype=np.uint8)
        color = (255, 255, 255)
        thickness = 2
        radius = [40, 80, 120, 160, 200]
        for R in radius:
            cv2.circle(GPSmap, (220,220), R, color, thickness)

        cv2.circle(GPSmap, (220+int(Lon*100*11.1*2), 220-int(Lat*100*11.1*2)), 3, (0,255,0), 5)

        GPSmap = cv2.cvtColor(GPSmap, cv2.COLOR_BGR2RGB)
        return GPSmap

    def show_GPS_map(self, Lat, Lon):
        image = self.create_GPS_map(Lat, Lon)
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        scaled_q_image = QPixmap.fromImage(q_image).scaled(440, 440, Qt.KeepAspectRatio)
        self.label_image_GPS.setPixmap(scaled_q_image)

    def decoding_image(self, cam_data, cam_num):
        try:
            print("img")
            cam_data = bytes.fromhex(cam_data)
            image_data = base64.b64decode(cam_data)
            filename = f'{self.folder_name}/camera{cam_num}/{self.can_time.replace(".","").replace(":","-")}'

            with open(f'{filename}.jpg','wb') as f:
                f.write(image_data)

            self.show_image(filename, cam_num)

            global csv_data
            csv_data.append([f"CAM{cam_num}", f"{self.KST}", f"{filename}"])
        except Exception as e:
            print(f"Error decoding data: {e}")
    
    def show_image(self, filename, cam_num):
        try:
            self.pixmap = QPixmap(f"{filename}")
            scaled_pixmap = self.pixmap.scaled(600, 450, Qt.KeepAspectRatio)

            if cam_num == '0':
                self.label_image_left.setPixmap(scaled_pixmap)
            else:
                self.label_image_right.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error show imagr: {e}")

    def reconnect(self):
        if not self.sendATH and self.sendATD:
            self.reconnect_cnt+=1
        not self.sendATH and self.sendATD
        if self.reconnect_cnt%7000 == 1:
            self.send_user_CMD('ATD')
    
    # csv 파일 저장
    def save_csv(self):
        global csv_data
        print("save_csv")
        now = str(dt.datetime.now())[11:19].replace(':','-')
        
        # 파일 저장
        with open(f'{self.folder_name}/cansat log {now}.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['sensor', 'time', 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
            for row in csv_data:
                writer.writerow(row)

    # parani 명령어 단축키
    def BT_scan(self):
        self.send_user_CMD('AT+BTSCAN')

    def BT_INQ(self):
        self.send_user_CMD('AT+BTINQ?')

    def ATZ(self):
        self.send_user_CMD('ATZ')
    
    def ATD(self):
        self.send_user_CMD('ATD')

    def ATplus(self):
        self.send_user_CMD('+++')

    def ATH(self):
        self.sendATH = True
        self.send_user_CMD('ATH')
    
    def UARTCONFIG(self):
        self.send_user_CMD(f'AT+UARTCONFIG,{self.CB_baudrate.currentText()},N,1')

if __name__ == "__main__":

    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    app.exec_()


    # csv 파일 저장
    if len(csv_data)!=0:
        print("save_csv")
        now = str(dt.datetime.now())[11:19].replace(':','-')
        with open(f'{foldername}/cansat log {now}.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['sensor', 'time', 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
            for row in csv_data:
                writer.writerow(row)

    if len(img_txt)!=0:
        print('save txt')
        now = str(dt.datetime.now())[11:19].replace(':','-')
        with open(f'{foldername}/img data {now}.txt', 'w+') as file:
            file.write('\n'.join(img_txt))

