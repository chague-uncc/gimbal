import cv2
from picamera import PiCamera
from picamera.array import PiRGBArray
import time
import numpy as np
from SunFounder_PCA9685 import Servo
# import RPi.GPIO as GPIO

TEMP_FILE = 'gif/im{0}.jpg'
ALL_OFF_PIN = 11

INTEGRAL_HISTORY = 10
KP = 4e-2
KI = 1e-8
KD = 0

def main():
    try:
        print('setup...')
        # emergency shuttoff
        # GPIO.setmode(GPIO.BOARD)
        # GPIO.setup(ALL_OFF_PIN, GPIO.OUT)
        # GPIO.output(ALL_OFF_PIN, GPIO.HIGH)
        # enable the PC9685 and enable autoincrement
        pan = Servo.Servo(1, bus_number=1)
        tilt = Servo.Servo(0, bus_number=1)
        currentPan = 0
        currentTilt = 0
        # camera and open cv
        picSpace = (640, 480)
        camera = PiCamera()
        camera.resolution = picSpace
        camera.framerate = 32
        rawCapture = PiRGBArray(camera, size=picSpace)
        faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        # pid variables
        history = [np.array([[0], [0], [0]])] * INTEGRAL_HISTORY
        # allow the camera to warmup
        time.sleep(0.1)
        tilt.write(70)
        currentTilt = 70
        pan.write(90)
        currentPan = 90
        j = 0
        print('starting ctrl+C to exit...')
        # capture frames from the camera
        for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            img = frame.array
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            found = faces.detectMultiScale(gray, minSize =(20, 20))
            if len(found) != 0:
                x, y, width, height = found[0]
                # center of face
                cX = x + width / 2
                cY = y + height / 2
                # transform coordinate system
                pX = cX - picSpace[0] / 2
                pY = (cY - picSpace[1] / 2) * -1
                error, integral, derivative, dt = calcErrorTerms(pX, pY, time.time(), history)
                #  print('error terms P ({0},{1}) I ({2},{3}) D ({4},{5})'.format(error[0], error[1], integral[0], integral[1], derivative[0], derivative[1]))
                pid = KP * error + KI * integral + KD * derivative
                # coordinate transformation to angles
                currentPan = -pid[0, 0] + currentPan
                currentTilt = -pid[1, 0] + currentTilt
                pan.write(currentPan)
                tilt.write(currentTilt)
                print('theta: {0:.2f} phi: {1:.2f}'.format(currentPan, currentTilt))

                # write images for gif
                cv2.rectangle(img, (x, y), 
                            (x + height, y + width), 
                            (0, 255, 0), 5)
                text = 'current ({4:.2f}, {5:.2f}), error ({0:.2f}, {1:.2f}), integral error ({2:.2f}, {3:.2f})'.format(pX, pY, integral[0, 0], integral[1, 0], currentTilt, currentPan)
                cv2.putText(img, text, (0,470), cv2.FONT_HERSHEY_SIMPLEX, .25, (255, 0, 255), 1, cv2.LINE_AA)
                cv2.imwrite(TEMP_FILE.format(j), img)
                j += 1
            else:
                print('no face found!')
                calcErrorTerms(0, 0, time.time(), history)
            # clear the stream in preparation for the next frame
            rawCapture.truncate(0)
    finally:
        pan.write(0)
        tilt.write(0)
        # GPIO.cleanup()

def calcErrorTerms(x, y, t, history):
    history.append(np.array([[x], [y], [t]]))
    history.pop(0)
    intg = np.zeros([2,1])
    for i in range(len(history) - 1):
        dt = history[i + 1][2] - history[i][2]
        # left sum
        intg = history[i][:2] * dt + intg
    der = (history[-1][:2] - history[-2][:2]) / (history[-1][2] - history[-2][2])
    return np.array([[x], [y]]), intg, der, dt

if __name__ == '__main__':
        main()
