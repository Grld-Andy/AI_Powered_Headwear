# AI POWERED HEADWEAR FOR THE VISUALLY IMPAIRED

A multimodal interactive system that combines real-time object detection, audio command recognition, TTS, wake word activation, OCR-based reading, and depth estimation for accessibility and assistive technology.

## Features

- **Wake Word Activation**: Listens for a wake word using a socket server.
- **Voice Commands**: Uses voice input to perform specific commands.
- **Multilingual Support**: Supports English and Twi.
- **Text-to-Speech**: Convert text to audio feedback for user.
- **Object Detection**: Detects nearby objects with YOLOv5.
- **Depth Estimation**: Determines if objects are close using MiDaS.
- **Reading Mode**: Uses OCR to read aloud text from camera feed.
- **Audio Feedback**: Use pre-recorded .wav audio clips and generated TTS.

---

## Requirements

### Python Packages

```bash
pip install opencv-python librosa sounddevice pytesseract numpy Pillow ultralytics pydub tensorflow
```
Tesseract OCR (ensure it's in system PATH)
ffmpeg (required by pydub)
A local TTS server running on http://localhost:5000

### External Files
Pretrained models:

- models/yolov5n.pt
- models/Midas-V2.onnx
- models/language_selector.keras
- models/{language}/command_classifier.keras

Pre-translated .wav files stored in:

- translated/phrases/
- translated/numbers/
- translated/labels/

Wake word server running on localhost:65432

## How to Run

Run the wake word socket server

Run the TTS server

Run the main_vision.py file


## Running
The program first asks the user to choose their prefered language which is take in by an audio input.

After that, the system goes into object detection mode.

### Commands
The user can initiate commands by first activating the wake word, 'Hello K2'.

After the system sends a request to the pipertts server with the query 'Hello what can i do for you' if English or plays 'Hello what can i do for you.wav' file (pre-recorded translation) if Twi.

After the user can say one of these commands to change modes:

- reading: 
    THe system goes into ocr mode. It captures the current frame, extracts text via OCR, and reads it by sending a request to the pipertts server and playing the audio.

- stop: Pauses all models, the system enters a normal camera mode.

- start: The system enters object detection mode. In object detection mode, when an object is detected, the depth of the object is estimated to see is an object with a threshold of less than 200 falls withing the bounding box of the object. If so, the object is labelled as close and the label is sent to pipertts and the audio response is said aloud to the user.

### Language Selection
On first run, system prompts user to say their preferred language. Recognized languages are:

- English

- Twi

Language is saved in a sqlite and reused for future sessions.

Flow Summary
- Startup:
    - Play turn on sound
    - Check database to see it language has already been selected.
        - If not, send a request to pipertts to ask for language in english and play corresponding translated twi audio. Take in input and using the language_selector.keras, predict the users language and save in a database. Store the language in the global variable SELECTED_LANGUAGE
        - If stored, get the saved language from the database and store it in the global variable SELECTED_LANGUAGE
    - Create a thread and connect to the wake word socket.
    - Load the object_detection, depth estimation and audio classifier models.
    - set current_mode to 'start'

- Start Mode:
    - In start mode, detect objects in the surrounding using object detection model.
    - If objects are found, create a depth map using depth estimation model.
    - Check if the bounding boxes of the objects contain a threshold < 200 and label them as close
    - Pass all close objects into pipertts to say them aloud if english else take their correponding .wav files, combine them into a single .wav file and play the wav file.

- Stop Mode:
    - In stop mode, turn off all models and switch to normal camera live feed mode.

- Read Mode:
    - In read mode, capture the existing frame and extract text from the frame.
    - Pass the text into pipertts and play the audio response aloud for the user.

## Wake Word
The system connects to a socket wake word server via a thread. The thread constantly runs alongside the main process and listens for the wake word.
The wake word currenlty is _Hello K2_

When the wake word is said and detected. If english it tells the user, "Hi, what can i do for you" but in twi it plays the corresponding .wav file to prompt the user to say a command. This prompt has priority over all other audio outputs.

## Command Recognition
Immediately after the wake word has been activated.Listens for user command.

- start: Switch current_mode variable to start and use object detection and depth estimaton

- reading: Capture frame and extract text using ocr. Read text aloud using pipertts.

- stop: Switch to normal camera output.

## Development stage
- Install dependencies
- Setup opencv camera
- Create wake word socket server
- Create global variables for state management
- Connect to wake word socket server in main application
- Create funciton to play audio files
- Test wake wake word
- Create function to handle audio command classification and test
- Implement object detection and depth estimation functions and setup to run in start mode
    - Implement piper_tts function to send text to piper tts
- Test start mode
- Implement stop mode
- Using wake word and audio classifier test switching to stop mode
- Implement reading mode and test
- Setup database
- Let user input language on start up and store in database
- Test language selector
- Create translated audio files
- Create conditional audio outputs depending on language
- Create funcition to combine multiple files
- Test system in twi mode

Reading mode currently supports only english mode.