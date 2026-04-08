import requests
import json
import os
import base64
import cv2
import numpy as np
import time
from io import BytesIO
from PIL import Image

class ISLModelAPI:
    def __init__(self, top_k=5):
        """
        Initializes the API handler for Indian Sign Language recognition.
        """
        self.base_url = "https://creator-090-isl-api.hf.space"
        self.predict_frames_url = f"{self.base_url}/predict_frames"
        self.predict_video_url = f"{self.base_url}/predict"
        self.health_url = f"{self.base_url}/health"
        self.top_k = top_k
        self.session = requests.Session()

    def check_health(self):
        """Checks if the remote model is loaded and ready."""
        try:
            response = self.session.get(self.health_url, timeout=3)
            return response.status_code == 200 and response.json().get("status") == "ok"
        except:
            return False

    def predict(self, frames):
        """
        Takes a list of PIL Images, compiles them into a temporary mp4 video,
        and sends it to the /predict endpoint of the Hugging Face API.
        """
        if not frames:
            return {"error": "No frames provided"}

        # 1. Create temporary video file
        temp_video_path = f"temp_inference_{int(time.time())}.mp4"
        try:
            width, height = frames[0].size
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, 15.0, (width, height))
            
            for frame in frames:
                cv_img = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
                out.write(cv_img)
            out.release()

            # 2. Send to API via multipart/form-data
            params = {"top_k": self.top_k}
            with open(temp_video_path, 'rb') as video_file:
                files = {'file': (os.path.basename(temp_video_path), video_file, 'video/mp4')}
                response = self.session.post(
                    self.predict_video_url, 
                    params=params, 
                    files=files, 
                    timeout=15
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"API error {response.status_code}: {response.text}"}
        
        except Exception as e:
            return {"error": str(e)}
        finally:
            # Cleanup
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

    def predict_from_frames(self, frames):
        """
        Encodes 16 PIL frames to base64 and sends via JSON to /predict_frames.
        """
        if not frames or len(frames) != 16:
            return {"error": f"Exactly 16 frames required, got {len(frames) if frames else 0}"}

        encoded_frames = []
        for frame in frames:
            buffer = BytesIO()
            frame.save(buffer, format="JPEG", quality=85)
            encoded_frames.append(base64.b64encode(buffer.getvalue()).decode())

        payload = {"frames": encoded_frames, "top_k": self.top_k}

        # Retry logic and timeout
        last_err = "Unknown error"
        for attempt in range(2):
            try:
                response = self.session.post(
                    self.predict_frames_url,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 503:
                    time.sleep(2)
                    continue
                else:
                    last_err = f"API error {response.status_code}: {response.text}"
            except Exception as e:
                last_err = str(e)
                time.sleep(1)
                continue
                
        return {"error": last_err}

# --- Example Usage ---
if __name__ == "__main__":
    isl_api = ISLModelAPI(top_k=5)
    print(f"Health check: {isl_api.check_health()}")
