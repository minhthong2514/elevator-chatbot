import cv2
import face_recognition
import os
import numpy as np


class FaceRecognition:
    def __init__(self, face_root, threshold=0.45):
        self.face_root = face_root
        self.threshold = threshold
        self.known_encodings = []
        self.known_names = []

        self.load_and_encode_faces()

    # ===============================
    # LOAD & ENCODE FACES
    # ===============================
    def load_and_encode_faces(self):
        print("[INFO] Loading & encoding faces...")

        for person_name in os.listdir(self.face_root):
            person_dir = os.path.join(self.face_root, person_name)
            if not os.path.isdir(person_dir):
                continue

            enc_list = []

            for img_name in os.listdir(person_dir):
                if img_name.lower().endswith((".jpg", ".png", ".jpeg")):
                    img_path = os.path.join(person_dir, img_name)
                    img = cv2.imread(img_path)
                    if img is None:
                        continue

                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    encs = face_recognition.face_encodings(rgb)

                    if encs:
                        enc_list.append(encs[0])

            if len(enc_list) >= 3:
                mean_enc = np.mean(enc_list, axis=0)
                self.known_encodings.append(mean_enc)
                self.known_names.append(person_name.upper())
                print(f"  [+] {person_name}: {len(enc_list)} images")

        print("[INFO] Loaded persons:", self.known_names)

    # ===============================
    # PROCESS FRAME
    # ===============================
    def recognize_faces(self, frame):
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

        face_locations = face_recognition.face_locations(
            small, number_of_times_to_upsample=1, model="hog"
        )

        face_encodings = face_recognition.face_encodings(
            small, face_locations
        )

        detected_names = set()

        for face_encoding, face_loc in zip(face_encodings, face_locations):
            name = "UNKNOWN"

            if self.known_encodings:
                distances = face_recognition.face_distance(
                    self.known_encodings, face_encoding
                )
                best_idx = np.argmin(distances)

                if distances[best_idx] < self.threshold:
                    name = self.known_names[best_idx]
                    detected_names.add(name)

            # Scale bounding box
            top, right, bottom, left = face_loc
            top *= 2
            right *= 2
            bottom *= 2
            left *= 2

            # cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 255), 2)
            # cv2.putText(
            #     frame,
            #     name,
            #     (left, top - 10),
            #     cv2.FONT_HERSHEY_COMPLEX,
            #     0.8,
            #     (255, 255, 255),
            #     2,
            # )

        return frame, detected_names