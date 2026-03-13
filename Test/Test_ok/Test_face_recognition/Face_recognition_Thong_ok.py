import cv2
import face_recognition
import os
import numpy as np
import time

previousTime = 0
path = "/home/tai/Ung_dung/Code/Python/Camera/faces_db/"
images = [] 
classname = []  
mylist = os.listdir(path)
print(mylist)
cond = []
for img in mylist:
    currentImg= cv2.imread(f"{path}/{img}", 1)
    images.append(currentImg)
    classname.append(os.path.splitext(img)[0])
print(classname)

def encode(images):
    encodelist = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_encode = face_recognition.face_encodings(img)[0]
        encodelist.append(img_encode)
    return encodelist

encodeListKnown = encode(images)
print("Mã hóa thành công!")
print(len(encodeListKnown))

cap = cv2.VideoCapture(0)



while True:
        ret, frame = cap.read()
        frame = cv2.flip(frame, 180)
        frame = cv2.resize(frame, (0,0),None, fx = 0.5, fy = 0.5)

        face_current = face_recognition.face_locations(frame,number_of_times_to_upsample=1, model= "hog")
        print(face_current)
        encodecurrent = face_recognition.face_encodings(frame)
        if face_current != cond:
            for encoderFace, faceLoc in zip(encodecurrent, face_current):
                matches = face_recognition.compare_faces(encodeListKnown, encoderFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encoderFace)

                matchIndex = np.argmin(faceDis) 

                if faceDis[matchIndex] < 0.5:
                    name = classname[matchIndex].upper()

                else:
                    name = "Unknown"


            print(name)
            cv2.rectangle(frame, (faceLoc[3], faceLoc[0]), (faceLoc[1], faceLoc[2]), (255,0,255),1)
            cv2.putText(frame, name, (faceLoc[1],faceLoc[0]), cv2.FONT_HERSHEY_COMPLEX,0.7,(255,255,255),1)

        currentTime = time.time()
        fps = 1 / (currentTime - previousTime)
        previousTime = currentTime
        cv2.putText(frame, f"FPS:{int(fps)}",(0,50), cv2.FONT_HERSHEY_COMPLEX,1,(255,0,0),1)
        cv2.imshow("Window", frame)
        if cv2.waitKey(1) == ord("q"):
            break

cap.release()
cv2.destroyAllWindows()

