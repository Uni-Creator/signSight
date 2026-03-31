# signSight

![GitHub Repo stars](https://img.shields.io/github/stars/Uni-Creator/signSight?style=social) ![GitHub forks](https://img.shields.io/github/forks/Uni-Creator/signSight?style=social)

A real-time Indian Sign Language (ISL) recognition system powered by a Swin3D + BiLSTM deep learning pipeline, served via a Flask API and paired with a Flutter mobile app. 🖐️

---

## Description

**signSight** is an end-to-end ISL recognition system that processes video input, extracts spatial-temporal features, and classifies sign gestures in real time. The system is designed for accessibility — enabling communication for the hearing-impaired by translating ISL gestures into readable text, with optional text-to-speech output on the mobile frontend.

### Project Overview

The pipeline is organized into three layers:

1. **Model** (`model/`): A Swin3D-S backbone combined with a BiLSTM head processes sequences of video frames to extract and classify ISL gestures. Model checkpoints and training datasets are stored here.

2. **Backend** (`backend/`): A Flask server exposes a REST/WebSocket API (using `flask-sock`) for real-time inference. It uses MediaPipe for hand landmark extraction, OpenCV for frame capture and preprocessing, and PyTorch + JAX for model inference.

3. **Frontend** (`frontend/`): A Flutter Android/iOS app that streams camera input to the backend, displays recognized gestures in real time, and reads them aloud via `flutter_tts`.

---

## Technologies Used

- **Python 3.10** — Backend, model training, and inference
- **PyTorch / JAX** — Model training and inference
- **Swin3D + BiLSTM** — Spatial-temporal feature extraction and sequence modeling
- **MediaPipe** — Hand landmark detection
- **OpenCV** — Frame capture and preprocessing
- **Flask + flask-sock** — REST and WebSocket API server
- **Flutter (Dart)** — Cross-platform mobile frontend
- **firebase / Pyrebase4** — Authentication and data sync
- **NumPy / SciPy / Matplotlib** — Data processing and visualization

---

## Project Structure

```plaintext
.
├── backend/                        # Flask API server + Python environment
│   ├── saved_captures/             # Saved gesture video captures
│   └── Lib/site-packages/          # Virtual environment dependencies
│
├── frontend/                       # Flutter mobile application
│   ├── lib/
│   │   ├── providers/              # State management
│   │   ├── screens/                # UI screens
│   │   └── services/               # API communication services
│   ├── assets/                     # Static assets (icons, images)
│   ├── android/                    # Android build configuration
│   └── ios/                        # iOS build configuration
│
└── model/
    ├── checkpoints/                # Saved model weights
    └── dataset/                    # ISL gesture training data
```

---

## Setup Instructions

### Prerequisites

- Python 3.10
- Flutter SDK (≥ 3.x)
- Android Studio or Xcode (for mobile deployment)
- CUDA-compatible GPU (recommended for training)

### Backend Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Uni-Creator/signSight.git
   cd signSight
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv backend
   source backend/bin/activate        # On Windows: backend\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Flask server**:
   ```bash
   cd backend
   python app.py
   ```

   The API will be available at `http://localhost:5000`.

### Frontend Setup

1. **Navigate to the Flutter project**:
   ```bash
   cd frontend
   ```

2. **Install Flutter dependencies**:
   ```bash
   flutter pub get
   ```

3. **Run the app** (with a connected device or emulator):
   ```bash
   flutter run
   ```

---

## GPU Acceleration

If a CUDA-compatible GPU is available, the model will automatically use it for inference. Ensure the appropriate versions of PyTorch and CUDA drivers are installed.

---

## API Overview

The Flask backend exposes:

| Endpoint | Method | Description |
|---|---|---|
| `/predict` | `POST` | Accepts a video frame sequence and returns a gesture label |
| `/ws` | WebSocket | Real-time streaming inference |

---

## Project Workflow

1. **Capture** — The Flutter app streams live camera frames to the backend.
2. **Preprocess** — MediaPipe extracts hand landmarks; OpenCV handles frame normalization.
3. **Inference** — The Swin3D + BiLSTM model classifies the gesture sequence.
4. **Display** — The recognized ISL sign is shown on-screen and optionally spoken via TTS.

---

## Contributors

<a href="https://github.com/Uni-Creator/signSight/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Uni-Creator/signSight" />
</a>

---

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes.
4. Push to the branch.
5. Open a pull request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Contact

For questions or inquiries, reach out at [abhayr24564@gmail.com](mailto:abhayr24564@gmail.com).