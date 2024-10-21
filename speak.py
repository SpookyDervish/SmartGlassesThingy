import sys
import pyttsx3

def init_engine():
    engine = pyttsx3.init()

    voices = engine.getProperty("voices")
    engine.setProperty("voice", voices[14].id)
    return engine

def say(s):
    #engine.setProperty("rate", r)
    engine.say(s)
    engine.runAndWait() #blocks

engine = init_engine()
say(str(sys.argv[1]))