import speech_recognition as sr


def recognize_speech(duration=3):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print(f"Listening for {duration} seconds...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)  # optional noise calibration
        audio = recognizer.listen(source, phrase_time_limit=duration)

    try:
        text = recognizer.recognize_google(audio)
        print("You said:", text)
        return text
    except sr.UnknownValueError as e:
        print("Sorry, could not understand the audio: ", e)
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))

