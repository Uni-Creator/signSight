"""
SignSight Backend - Flask + WebSocket Server
============================================
This server handles:
 - /register    POST  → Firebase user registration
 - /login       POST  → Firebase user login  
 - /history     GET   → Retrieve user translation history
 - /history     POST  → Store a translation
 - /ws          WS    → Real-time camera frame sign detection
"""

import base64
import json
import logging
import time
from collections import deque
from io import BytesIO

import cv2
import numpy as np
import mediapipe as mp
import concurrent.futures
from flask import Flask, request
from flask_cors import CORS
from flask_sock import Sock
from PIL import Image

mp_drawing = None

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.framework.formats import landmark_pb2
    mp_drawing = mp.solutions.drawing_utils
except Exception as e:
    print(f"MediaPipe Tasks API init failed: {e}")

def apply_landmarks(image: Image.Image, pose_detector, hand_detector) -> Image.Image:
    """Applies MediaPipe Tasks API landmarks to a PIL Image and returns the annotated image."""
    img = np.array(image)
    img_rgb = img  # Image is already RGB from PIL

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    
    pose_result = pose_detector.detect(mp_image) if pose_detector else None
    hand_result = hand_detector.detect(mp_image) if hand_detector else None

    if not pose_result and not hand_result:
        return image

    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    # Draw Pose
    if pose_result and pose_result.pose_landmarks:
        for pose_landmarks in pose_result.pose_landmarks:
            pose_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
            pose_landmarks_proto.landmark.extend([
                landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in pose_landmarks
            ])
            mp_drawing.draw_landmarks(
                img_bgr,
                pose_landmarks_proto,
                mp.solutions.pose.POSE_CONNECTIONS,
                mp.solutions.drawing_styles.get_default_pose_landmarks_style()
            )

    # Draw Hands
    if hand_result and hand_result.hand_landmarks:
        for hand_landmarks in hand_result.hand_landmarks:
            hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
            hand_landmarks_proto.landmark.extend([
                landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in hand_landmarks
            ])
            mp_drawing.draw_landmarks(
                img_bgr,
                hand_landmarks_proto,
                mp.solutions.hands.HAND_CONNECTIONS,
                mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                mp.solutions.drawing_styles.get_default_hand_connections_style()
            )

    return Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

from authentication import register_account, login_account
from history import retrieve_history, store_translation
from model import ISLModelAPI

# App setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Global ThreadPool for background HF API requests
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})   # Allow all origins for dev
sock = Sock(app)

# Configuration
CLIP_LENGTH = 16
FRAME_DELAY = 0.08

# Initialize model caller
model_api = ISLModelAPI(top_k=1)


@app.route("/")
def index():
    return json.dumps({"message": "SignSight API is running", "version": "2.0"})


@app.route("/register", methods=["POST"])
def register():
    """Register a new user in Firebase."""
    account = request.get_json(silent=True)
    if not account or "email" not in account or "password" not in account:
        return json.dumps({"id": "", "error": "Missing email or password"}), 400

    user_id = register_account(account["email"], account["password"])
    logger.info(f"Register: {account['email']} → id={user_id or 'FAILED'}")
    return json.dumps({"id": user_id})


@app.route("/login", methods=["POST"])
def login():
    """Authenticate and return user id."""
    account = request.get_json(silent=True)
    if not account or "email" not in account or "password" not in account:
        return json.dumps({"id": "", "error": "Missing email or password"}), 400

    user_id = login_account(account["email"], account["password"])
    logger.info(f"Login: {account['email']} → id={user_id or 'FAILED'}")
    return json.dumps({"id": user_id})


@app.route("/history", methods=["GET"])
def get_history():
    """Retrieve translation history for a user."""
    user_id = request.args.get("id", "")
    if not user_id:
        return json.dumps({"history": [], "error": "Missing user id"}), 400

    history = retrieve_history(user_id)
    return json.dumps({"history": history})


@app.route("/history", methods=["POST"])
def post_history():
    """Store a translation entry."""
    try:
        body = request.get_json(silent=True)
        if not body:
            return json.dumps({"message": "error", "detail": "No JSON body"}), 400

        user_id = body.get("id", "")
        translation = body.get("translation", "")
        if not user_id or not translation:
            return json.dumps({"message": "error", "detail": "Missing id or translation"}), 400

        store_translation(user_id, translation)
        return json.dumps({"message": "success"})
    except Exception as e:
        logger.error(f"post_history error: {e}")
        return json.dumps({"message": "error", "detail": str(e)}), 500


@sock.route("/ws")
def websocket_translate(ws):
    """
    Real-time sign translation via WebSocket.
    """
    logger.info("WebSocket client connected")
    ws.send(json.dumps({"status": "connected", "message": "Ready for frames"}))

    # Dynamic Config
    config = {"mode": "hybrid"}
    
    frame_buffer = deque(maxlen=CLIP_LENGTH)
    last_receive_time = time.monotonic()
    last_prediction_future = None
    
    # Safely instantiate Task API Landmarkers
    pose_detector = None
    hand_detector = None
    try:
        if mp_drawing: # MediaPipe successfully imported
            pose_base_options = mp_python.BaseOptions(model_asset_path='pose_landmarker_full.task')
            pose_options = mp_vision.PoseLandmarkerOptions(base_options=pose_base_options)
            pose_detector = mp_vision.PoseLandmarker.create_from_options(pose_options)

            hand_base_options = mp_python.BaseOptions(model_asset_path='hand_landmarker.task')
            hand_options = mp_vision.HandLandmarkerOptions(
                base_options=hand_base_options,
                num_hands=2
            )
            hand_detector = mp_vision.HandLandmarker.create_from_options(hand_options)
    except Exception as e:
        logger.error(f"Failed to load Landmarkers: {e}")

    # Initial Health Check
    if not model_api.check_health():
        logger.warning("Remote model API is not ready. Predictions may fail.")
    else:
        logger.info("Remote model API is healthy.")

    try:
        while True:
            message = ws.receive(timeout=30)
            if not message:
                break

            # Handle commands
            try:
                data = json.loads(message)
                if data.get("type") == "config":
                    new_mode = data.get("mode")
                    if new_mode in ["frames", "video", "hybrid"]:
                        config["mode"] = new_mode
                        ws.send(json.dumps({"status": "config_updated", "mode": new_mode}))
                        logger.info(f"Switching inference mode to: {new_mode}")
                        continue
            except:
                pass

            now = time.monotonic()
            if now - last_receive_time < FRAME_DELAY:
                continue
            last_receive_time = now

            # Decode incoming base64 frame from Flutter
            try:
                t0 = time.time()
                data = json.loads(message)
                b64 = data.get("frame", "")
                if not b64:
                    continue
                img_bytes = base64.b64decode(b64)
                
                # Apply landmarks before resizing
                raw_image = Image.open(BytesIO(img_bytes)).convert("RGB")
                t_decode = time.time()

                if pose_detector and hand_detector:
                    annotated_img = apply_landmarks(raw_image, pose_detector, hand_detector)
                    image = annotated_img.resize((224, 224))
                else:
                    image = raw_image.resize((224, 224))
                
                t_process = time.time()
                capture_ms = (t_decode - t0) * 1000
                process_ms = (t_process - t_decode) * 1000
                print(f"[Latencies] Capture/Decode: {capture_ms:.1f}ms | MediaPipe: {process_ms:.1f}ms")

            except Exception as e:
                logger.warning(f"Frame decode error: {e}")
                ws.send(json.dumps({"error": "Invalid frame"}))
                continue

            frame_buffer.append(image)

            # Check if background prediction is done
            if last_prediction_future is not None and last_prediction_future.done():
                try:
                    result = last_prediction_future.result()
                    if "error" in result:
                        logger.error(f"API Error: {result['error']}")
                    else:
                        label = result.get('prediction', '')
                        conf = result.get('confidence', 0.0)
                        
                        hf_inference = result.get('inference_time_ms', 0.0)
                        total_predict = result.get('total_latency_ms', 0.0)
                        print(f"[TOTAL Latencies] {config['mode'].upper()} Predict Task: {total_predict:.1f}ms (HF API time: {hf_inference:.1f}ms)")
                        print(f"Detected: {label} ({conf:.0%})")
                        try:
                            conf = float(conf)
                        except ValueError:
                            conf = 0.0

                        if label and conf > 0.4:
                            ws.send(json.dumps({"label": label, "confidence": conf}))
                            logger.info(f"Detected: {label} ({conf:.0%})")
                            frame_buffer.clear() 
                except Exception as e:
                    logger.error(f"Background prediction failed: {e}")
                
                last_prediction_future = None

            # Dispatch new prediction if buffer is full and executor is free
            if len(frame_buffer) == CLIP_LENGTH and last_prediction_future is None:
                frames_copy = list(frame_buffer)
                
                def predict_with_latency(frames, selected_mode):
                    start_t = time.time()
                    
                    if selected_mode == "frames":
                        res = model_api.predict_from_frames(frames)
                    elif selected_mode == "video":
                        res = model_api.predict(frames)
                    else:
                        # Hybrid logic
                        res = model_api.predict_from_frames(frames)
                        if "error" in res:
                            logger.warning(f"Hybrid: Fast inference failed. Falling back to video.")
                            res = model_api.predict(frames)
                    
                    res['total_latency_ms'] = (time.time() - start_t) * 1000
                    return res
                
                last_prediction_future = executor.submit(predict_with_latency, frames_copy, config["mode"])

    except Exception as e:
        logger.warning(f"WebSocket closed: {e}")
    finally:
        if pose_detector:
            pose_detector.close()
        if hand_detector:
            hand_detector.close()
        logger.info("WebSocket client disconnected")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SignSight Backend starting...")
    print("  REST API:  http://0.0.0.0:5000/")
    print("  WebSocket: ws://0.0.0.0:5000/ws")
    print("  Android emulator: use 10.0.2.2 instead of localhost")
    print("="*60 + "\n")
    # threaded=True for handling multiple WebSocket clients
    app.run(host="0.0.0.0", port=5000, threaded=True)
