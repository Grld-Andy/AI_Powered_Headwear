import pyttsx3


def speak(text):
    engine = pyttsx3.init()
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate - 10)
    engine.setProperty('volume', 1.0)
    engine.say(text)
    engine.runAndWait()
