import easyocr
import pyttsx3.voice
import pygame
import pygame.camera
import pyttsx3
import cv2
import os
import datetime
import configparser
import time
import sys
import playsound
import socket
import shutil
import json

# STT modules
import pvporcupine
import pvcheetah
from pvrecorder import PvRecorder

import speech_recognition as sr
import sounddevice as sd
import numpy as np

from scrape import get_top_search, SearchEngine
from better_microphone import DuckTypedMicrophone

from threading import Thread
from scipy.io.wavfile import write, read
from rich.console import Console
from rich.traceback import install

from subprocess import call

from textual.app import App
from textual.widgets import RichLog

# Object recognition
import cvlib as cv
from cvlib.object_detection import draw_bbox


console = Console()
print = console.print

class Glasses:
    def __init__(self, activation_word : str = "glasses", language : str = "en", voice_id : int = None, debug_mode : bool = None) -> None:
        start_loading = time.time()
        
        print("Loading...")

        if not os.path.isfile("glasses_config.ini"):
            print("`glasses_config.ini` was not found!")
            sys.exit(1)

        self.config = configparser.ConfigParser()
        self.config.read("glasses_config.ini")

        self.debug_mode = debug_mode if debug_mode is not None else bool(int(self.config.get("general","debug_enabled")))

        if self.debug_mode:
            print("Loaded config.")

        if self.debug_mode:
            print("Starting debugging helper..")
            install()

        self.activation_word = self.config.get("stt", "activation_word")
        self.language = language
        self.voice_id = voice_id if voice_id is not None else int(self.config.get("tts", "default_voice"))

        if self.debug_mode:
            print("Configuration accepted.")

        self.recording_video = False

        self.cameras: list[str] = []
        self.recorder = None
        self.microphones = None
        self.transcriber = None

        if self.debug_mode:
            print("Loading core modules..")

        self.init_camera()

        if self.debug_mode:
            print("Detecting microphones..")

        self.init_microphone()

        use_tts = bool(int(self.config.get("tts", "use_tts")))
        if self.debug_mode:
            print("... done.")
            if use_tts:
                print("Setting up TTS (Text To Speech)..")

        if use_tts:
            self.engine = pyttsx3.init()

        """if self.debug_mode:
            print("Checking for active internet connection..")
        if self.internet_available() == False:
            sys.exit(1)
        if self.debug_mode:
            print("Internet available!")"""

        
        if use_tts:
            if self.debug_mode:
                print("Loading TTS voices..")
            self.voices = self.engine.getProperty("voices")

            if self.debug_mode:
                print("Voices:")
                for i, voice in enumerate(self.voices):
                    if voice.languages[0].startswith(self.language):
                        print(f"    - {i} | {voice.name}")

            if self.debug_mode:
                print("Configuring TTS voice..")
            self.engine.setProperty("voice", self.voices[self.voice_id].id)

        if self.debug_mode:
            print("Preparing STT..")
        api_key = self.config.get("stt", "api_key")
        activation_word = self.config.get("stt", "activation_word")
        self.porcupine = pvporcupine.create(api_key, keywords=[activation_word])

        if self.debug_mode:
            print(f"    [bold blue]→[/bold blue] [bold][green]Porcupine[/green] | [white]{self.porcupine.version}[/white][/bold]")

        self.cheetah = pvcheetah.create(
            access_key=api_key,
            endpoint_duration_sec=1.0,
            enable_automatic_punctuation=False)
        
        if self.debug_mode:
            print(f"    [bold blue]→[/bold blue] [bold][green]Cheetah[/green] | [white]{self.cheetah.version}[/white][/bold]\n")

        if self.debug_mode:
            print("Setting up object recognition..\n\n")
        self.showing_objects = False

        print("[bold]=== Loading done! ===[/bold]")
        time_taken_to_load = time.time() - start_loading
        print(f"Loading took {round(time_taken_to_load, 1)} seconds.\n")

        if self.debug_mode:
            console.input("Press enter to continue.", password=True)

    def new_note(self, text: str):
        try:
            with open("notes.json", "r") as f:
                notes = json.load(f)
            notes["notes"].append(text)
            with open("notes.json", "w") as f:
                json.dump(notes, f)

            self.say(f"Done! I added the note \"{text}\".")
        except Exception as e:
            self.say("Sorry, there was a problem creating that note for you.")
            if self.debug_mode == True:
                self.say(str(e))

    def get_notes(self):
        with open("notes.json", "r") as f:
            notes = json.load(f)
        return notes["notes"]

    def object_vision(self):
        video = cv2.VideoCapture(0)

        while self.showing_objects:
            ret, frame = video.read()
            bbox, label, conf = cv.detect_common_objects(frame)
            output_image = draw_bbox(frame, bbox, label, conf)

            cv2.imshow("Glasses Vision", output_image)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    def stop_object_vision(self):
        self.showing_objects = False

    def text2int(self, textnum, numwords={}):
        if not numwords:
            units = [
                "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
                "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
                "sixteen", "seventeen", "eighteen", "nineteen",
            ]

            tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

            scales = ["hundred", "thousand", "million", "billion", "trillion"]

            numwords["and"] = (1, 0)
            for idx, word in enumerate(units):    numwords[word] = (1, idx)
            for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
            for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

        current = result = 0
        for word in textnum.split():
            if word not in numwords:
                raise Exception("Illegal word: " + word)

            scale, increment = numwords[word]
            current = current * scale + increment
            if scale > 100:
                result += current
                current = 0

        return result + current

    def search(self, prompt: str, engine: SearchEngine = SearchEngine.GOOGLE):
        self.say(f"Searching the web for \"{prompt}\"..")

        if self.debug_mode:
            print(f"Searching {engine.name} for {prompt}..")
        top_result = get_top_search(prompt, engine, 2)

        return top_result

    def change_voice(self, new_voice_id : int):
        self.say(f"Changing voice to number {new_voice_id}...")

        self.voice_id = new_voice_id
        self.engine.setProperty("voice", self.voices[self.voice_id].id)

        self.say("done.")

    def is_audio_loud(self, file_name, threshold: int = None):
        threshold = threshold if threshold is not None else int(self.config.get("microphone", "threshold"))

        # Read the recorded audio
        _, audio_data = read(file_name)

        # Convert the audio data to floating point numbers for easier processing
        audio_data_float = audio_data.astype(np.float32)
        average_volume = np.sqrt(np.mean(audio_data_float**2))/100 # The average volume of the audio file

        average_volume = min(max(average_volume, 0), 100) # Limit it from 0-100

        if self.debug_mode:
            print("\nAverage Volume:", average_volume)
            print("Threshold:", threshold)

        return average_volume>=threshold

    def record(self, frequency = 44100, max_wait_time=5):        
        first_recording = True

        combined_audio = np.array([], dtype=np.int16)  # Combined audio data

        try:
            while True:
                # Record 1 second of audio
                recording = sd.rec(
                    int(2.5 * frequency),
                    samplerate=frequency,
                    channels=1,
                    dtype=np.int16
                )
                sd.wait()
                write("temp_recording.wav", frequency, recording)

                if not self.is_audio_loud("temp_recording.wav") and first_recording == True:
                    continue

                recording = np.squeeze(recording)
                combined_audio = np.concatenate((combined_audio, recording), axis=0, dtype=np.int16)

                first_recording = False
                if not self.is_audio_loud("temp_recording.wav"):
                    break
        except KeyboardInterrupt:
            pass # Do nothing because this is our way of stopping the recording.


        #final_recording = np.concatenate((first_recording, second_recording), axis=0)

        write("recording0.wav", frequency, combined_audio)

    def init_microphone(self):
        self.microphones = sd.query_devices(kind="input")

        if self.debug_mode:
            print("Microphones:")
            for microphone in self.microphones.values():
                print(f"    - {microphone}")

    def say(self, text: str, rate: int = 150, should_print : bool = True):
        if should_print:
            self.chat.write(f"[bold][[blue]GLASSES[/blue]][/bold] {text}")
            #print(f"[bold][[blue]GLASSES[/blue]][/bold] {text}")
        if bool(int(self.config.get("tts", "use_tts"))) == True:
            call(["python3", "speak.py", text])

    def init_camera(self):
        """
        Should only be called once.
        """
        if self.debug_mode:
            print("Starting camera...")

        pygame.camera.init()

        cameras = pygame.camera.list_cameras()

        if self.debug_mode:
            print("Cameras:")
            for camera in cameras:
                print("    - " + str(camera))

        self.cameras = cameras

    def cleanup(self):
        self.recording_video = False
        self.stop_object_vision()

        if os.path.isfile("image.png"):
            os.remove("image.png")
        if os.path.isfile("recording0.wav"):
            os.remove("recording0.wav")
        if os.path.isfile("temp_recording.wav"):
            os.remove("temp_recording.wav")

    def del_photos(self):
        if os.path.isdir("photos"):
            shutil.rmtree("photos")

    def del_videos(self):
        if os.path.isdir("recordings"):
            shutil.rmtree("recordings")

    def stop_recording_video(self):
        self.recording_video = False
        self.say("Done recording.")
        
    def start_recording_video(self):
        if not os.path.isdir("recordings"):
            os.mkdir("recordings")

        self.recording_video = True

        file_name = datetime.datetime.now()

        self.say("Starting recording...")

        def the_thread():
            cam = cv2.VideoCapture(0)

            cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            fourcc = cv2.VideoWriter_fourcc("m", "p", "4", "v")
            writer = cv2.VideoWriter(f"recordings/{file_name}.mp4", fourcc, 30.0, (1280, 720))

            while self.recording_video:
                ret, frame = cam.read()

                if ret:
                    #cv2.imshow("video", frame)
                    writer.write(frame)

            cam.release()
            writer.release()
            cv2.destroyAllWindows()
        thread = Thread(target=the_thread)
        thread.start()

    def take_photo(self, image_path : str = None, camera : str = None):
        if self.recording_video:
            self.say("You can't take a photo right now, you are recording a video.")
            return
        
        name = image_path

        if not image_path:
            name = f"{datetime.datetime.now()}.png"
            image_path = f"photos/{name}"
            if not os.path.isdir("photos"):
                os.mkdir("photos")

        if not camera:
            camera = self.cameras[0]

        self.say("Taking photo... ")

        # initialize the camera
        cam = pygame.camera.Camera(camera,(1280,720))
        cam.start()

        time.sleep(1) # Give the camera time to 

        img = cam.get_image()

        pygame.image.save(img,image_path)

        self.say("done.")
        return name

    def get_text_in_image(self, image_path : str):
        reader = easyocr.Reader([self.language])
        result = reader.readtext(image_path)

        return [text for _, text, _ in result]
    
    def clear_console(self):
        if os.name == "nt":
            os.system("cls")
        elif os.name == "posix":
            os.system("clear")
    
    def internet_available(self, host="8.8.8.8", port=53, timeout=3):
        """
        Host: 8.8.8.8 (google-public-dns-a.google.com)
        OpenPort: 53/tcp
        Service: domain (DNS?TCP)
        """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error as ex:
            self.say("Your glasses require an active internet connection to work, please connect them to WIFI and restart.")
            return False

    def recognize_speech_real_time(self, chat: RichLog, wait_for_word: bool = True):
        #api_key = self.config.get("stt", "api_key")
        #activation_word = str(self.config.get("stt", "activation_word"))

        wake_word_detected = not wait_for_word
        if wait_for_word == False:
            chat.write("[bold][[green]YOU[/green]][/bold]     \r")
            playsound.playsound("assets/sounds/activation.wav")

        endpoint_reached = False
        user_request = ''

        # Connect microphone
        mic = PvRecorder(self.porcupine.frame_length)
        mic.start()

        while True:
            if not wake_word_detected:
                pcm = mic.read()
                wake_word_detected = self.porcupine.process(pcm) == 0
                
                if wake_word_detected:
                    chat.write("[bold][[green]YOU[/green]][/bold]     \r")
                    playsound.playsound("assets/sounds/activation.wav")
            elif not endpoint_reached:
                pcm = mic.read()
                partial_transcript, endpoint_reached = self.cheetah.process(pcm)
                partial_transcript = partial_transcript.lower()

                if partial_transcript.strip() != "":
                    chat.write(partial_transcript + "\r")

                user_request += partial_transcript

                if endpoint_reached:
                    remaining_transcript = self.cheetah.flush()

                    user_request += remaining_transcript.lower()
                    chat.write(remaining_transcript + "\r")
                    
                    break
        
        return user_request


    def recognize_speech(self):
        """
        ! This is the old way of doing things. Use the other method of this which is real time and much better.
        """

        """data, samplerate = soundfile.read(recording)
        soundfile.write(recording, data, samplerate, subtype='PCM_16')"""

        r = sr.Recognizer()

        """audio_file = sr.AudioFile(recording)
        with audio_file as source:
            audio = r.record(source)"""
        
        try:
            with DuckTypedMicrophone() as source:
                r.adjust_for_ambient_noise(source)
                max_time = float(self.config.get("microphone", "max_speaking_time"))

                try:
                    with console.status("[bold white]Listening..."):
                        playsound.playsound("assets/sounds/listening.wav", block=False)
                        audio = r.listen(source, timeout=max_time, phrase_time_limit=max_time)
                except KeyboardInterrupt:
                    playsound.playsound("assets/sounds/error.wav", block=False)
                    return None

            try:
                with console.status("[bold white]Thinking..."):
                    speech = r.recognize_google(audio)
            except sr.RequestError:
                self.say("Hmm, it appears you have lost nternet connection while using the glasses. Plkease restart your glasses and try again.")
                sys.exit(1)
        except sr.WaitTimeoutError:
            if self.debug_mode:
                print(f"\n[bold white on red]EXCEPTION:[/bold white on red] [bold red]Timed out.[/bold red]")

            return None
        except sr.UnknownValueError as e:
            #self.say("Sorry, I didn't catch that.")
            playsound.playsound("assets/sounds/error.wav", block=False)

            if self.debug_mode:
                print(f"\n[bold white on red]EXCEPTION:[/bold white on red] [bold red]{e}[/bold red]")

            return None
        
        #chosen_text_dict = speech["alternative"][0]
        return speech