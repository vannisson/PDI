import cv2
import mediapipe as mp
import numpy as np
import asyncio
import websockets
import json

# Inicializar MediaPipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)

# Suposição dos parâmetros de calibração da câmera (matriz de câmera e coeficientes de distorção)
camera_matrix = np.array([[800, 0, 320],
                          [0, 800, 240],
                          [0, 0, 1]], dtype="double")
dist_coeffs = np.zeros((4, 1))  # Assumindo nenhuma distorção para simplificação

def calculate_head_orientation(landmarks, frame_width, frame_height):
    """Calcula a orientação da cabeça usando landmarks 3D."""
    nose_tip = np.array([landmarks[1].x * frame_width, landmarks[1].y * frame_height, landmarks[1].z * frame_width])
    chin = np.array([landmarks[152].x * frame_width, landmarks[152].y * frame_height, landmarks[152].z * frame_width])
    left_eye_outer = np.array([landmarks[263].x * frame_width, landmarks[263].y * frame_height, landmarks[263].z * frame_width])
    right_eye_outer = np.array([landmarks[33].x * frame_width, landmarks[33].y * frame_height, landmarks[33].z * frame_width])
    
    eye_center = (left_eye_outer + right_eye_outer) / 2.0
    nose_to_chin = chin - nose_tip
    eye_to_eye = left_eye_outer - right_eye_outer
    
    roll = np.arctan2(eye_to_eye[1], eye_to_eye[0])
    pitch = np.arctan2(nose_to_chin[1], np.linalg.norm([nose_to_chin[0], nose_to_chin[2]]))
    yaw = np.arctan2(nose_tip[0] - eye_center[0], nose_tip[1] - eye_center[1])
    
    return (nose_tip, roll, pitch, yaw)

def process_frame(frame):
    """Processa o quadro de vídeo e retorna os landmarks faciais."""
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(frame_rgb)

    if not result.multi_face_landmarks:
        return None

    return result.multi_face_landmarks[0].landmark

async def capture_and_send(websocket, path):
    """Captura vídeo da webcam e envia dados de rastreamento de cabeça via WebSocket."""
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        landmarks = process_frame(frame)
        if landmarks:
            frame_height, frame_width, _ = frame.shape
            position, roll, pitch, yaw = calculate_head_orientation(landmarks, frame_width, frame_height)
            data = {
                "position": [position[0], position[1], position[2]],
                "rotation": [roll, pitch, yaw]
            }
            await websocket.send(json.dumps(data))
        await asyncio.sleep(0.033)
    cap.release()

async def main():
    async with websockets.serve(capture_and_send, "localhost", 8000):
        await asyncio.Future()  # Executa para sempre

if __name__ == "__main__":
    asyncio.run(main())