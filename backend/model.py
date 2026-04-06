import requests
import json
import os
import tempfile
import cv2
import numpy as np
import time

class ISLModelAPI:
    def __init__(self, top_k=5):
        """
        Initializes the API handler for Indian Sign Language recognition.
        """
        self.url = "https://creator-090-isl-api.hf.space/predict"
        self.top_k = top_k

    def predict(self, video_path):
        """
        Sends a video file to the Hugging Face Space for inference.
        """
        if not os.path.exists(video_path):
            return {"error": f"File not found: {video_path}"}

        # Parameters for the query
        params = {"top_k": self.top_k}

        # Open the video file in binary mode
        try:
            with open(video_path, 'rb') as video_file:
                # Prepare the multipart form-data payload
                files = {
                    'file': (os.path.basename(video_path), video_file, 'video/mp4')
                }
                
                # Make the POST request
                response = requests.post(self.url, params=params, files=files)
                
                # Check for successful response
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "error": f"Server returned status code {response.status_code}",
                        "message": response.text
                    }
        except Exception as e:
            return {"error": str(e)}

    def predict_from_frames(self, frames):
        """
        Takes a list of PIL Images, creates a temporary mp4 video, and sends it for inference.
        """
        if not frames:
            return {"error": "No frames provided"}
            
        os.makedirs('saved_captures', exist_ok=True)
        temp_video_path = os.path.join('saved_captures', f"capture_{int(time.time() * 1000)}.mp4")
            
        try:
            width, height = frames[0].size
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, 15.0, (width, height))
            
            for frame in frames:
                cv_img = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
                out.write(cv_img)
            
            out.release()
            return self.predict(temp_video_path)
            
        except Exception as e:
            return {"error": str(e)}

# --- Example Usage ---
if __name__ == "__main__":
    isl_api = ISLModelAPI(top_k=5)
    test_video = "MVI_9490.MOV"
    
    if os.path.exists(test_video):
        print(f"Sending {test_video} to API...")
        result = isl_api.predict(test_video)
        print(json.dumps(result, indent=4))
    else:
        print(f"Test video {test_video} not found.")