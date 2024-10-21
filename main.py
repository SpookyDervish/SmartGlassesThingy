from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Tree, Rule, Markdown
from textual import work

from widgets.banner import Banner
from widgets.chat_box import ChatBox

from rich_pixels import Pixels

from glasses import Glasses

from threading import Thread
from PIL import Image

import random, datetime, time, sys

glasses = Glasses()


class GlassesApp(App):
    """A Textual app to manage stopwatches."""

    BINDINGS = []
    TITLE = "Glasses"
    CSS_PATH = "assets/style.tcss"

    def delete_photos_loop(self):
        glasses.say("Are you sure you would like to delete your photos?")

        spoken_text = glasses.recognize_speech_real_time()

        if spoken_text in ["yes", "sure"]:
            glasses.say("Deleting photos...")

            glasses.del_photos()

            glasses.say("Done.")
        elif spoken_text[1] in ["no", "cancel"]:
            glasses.say("Ok.")
        else:
            glasses.say("That is not an option, try again.")
            self.delete_photos_loop(glasses)

    def delete_videos_loop(self):
        glasses.say("Are you sure you would like to delete your videos?")

        spoken_text = glasses.recognize_speech_real_time()

        if spoken_text in ["yes", "sure"]:
            glasses.say("Deleting videos...")

            glasses.del_videos()

            glasses.say("Done.")
        elif spoken_text[1] in ["no", "cancel"]:
            glasses.say("Ok.")
        else:
            glasses.say("That is not an option, try again.")
            self.delete_photos_loop(glasses)

    @work(thread=True)
    def main_loop(self):
        chat = self.query_one(RichLog)
        #glasses.say("This is a test of the TTS (Text to Speech) for the glasses!")

        self.app.notify("Glasses ready!", title="Ready!")

        try:
            glasses.say("Ready!\n")

            while True:
                #print("Listening...")
                """with console.status("[bold white]Listening..."):
                    glasses.record()"""

                #print("Thinking...\n")
                #chosen_text_dict = glasses.recognize_speech("recording0.wav")
                spoken_text = glasses.recognize_speech_real_time(chat)
                
                self.notify(str(spoken_text))

                if not spoken_text:
                    continue

                spoken_text: list[str] = spoken_text.lower().split()

                if len(spoken_text) == 0:
                    glasses.say("Sorry, I didn't catch that. Please say that again.")
                    continue

                split_text = spoken_text
                spoken_text = ' '.join(spoken_text)

                """if glasses.debug_mode:
                    print(f"Spoken text: {chosen_text_dict}")"""



                if spoken_text in ["bye", "goodbye"]:
                    glasses.say("Goodbye!")
                    glasses.cleanup()
                    self.app.exit()
                    break
                elif spoken_text in ["hakuna matata"]:
                    glasses.say("What a wonderful phrase!")
                    glasses.say("It means now worries, for the rest of your days.")
                elif spoken_text in ["i hate you"]:
                    glasses.say("That wasn't very nice. :(")
                elif spoken_text in ["i love you"]:
                    glasses.say("Thats very flaterring, but sadly I'm an AI. :)")
                elif split_text[:3] == ["do", "you", "like"]:
                    responses = ["I like lots of things! And thats one of the things I like. :)", "Of course!", "Yep!", "Not really.", "Its alright.", "No, sorry."]
                    glasses.say(random.choice(responses))
                elif split_text[0] == "say":
                    split_text.pop(0)
                    
                    if len(split_text) == 0:
                        glasses.say("What do you want me to say?")

                        speech = glasses.recognize_speech_real_time()
                        if speech:
                            split_text = speech.lower().split()
                        else:
                            continue



                    if split_text[0] in ["hi", "hello"]:
                        glasses.say("Greetings, all!")
                    else:
                        glasses.say(' '.join(split_text))
                elif spoken_text in ["hi", "hello", "sup", "what's good"]:
                    glasses.say(f"Hello, {glasses.config.get('personalization', 'name')}!")
                elif spoken_text in ["how are you", "how's it going"]:
                    choices = ["I'm good.", "I'm great, thanks.", "I'm feelling good, thanks for asking."]
                    glasses.say(random.choice(choices))
                elif spoken_text in ["self-destruct", "activate self-destruct sequence", "activate-self destruct", "self-destruct sequence"]:
                    glasses.say("Warning, self destruct sequence activated.")
                    glasses.say("Self destruct in 3. 2. 1.")
                    time.sleep(2)
                    glasses.say("Hmm, nothing happened.")
                    self.app.exit()
                    sys.exit()
                elif "time" in split_text:
                    now = datetime.datetime.now()
                    formatted_time = datetime.datetime.strptime(f"{now.hour}:{now.minute}", "%H:%M")

                    glasses.say(f"It is currently {formatted_time.strftime('%I:%M %p')}")
                elif spoken_text in ["take a photo of me", "take a photo", "take a picture", "take a photo", "take photo", "take picture", "take photo of me", "take picture of me"]:
                    name = glasses.take_photo()

                    glasses.say("Showing you the photo...")

                    if glasses.debug_mode:
                        print("Showing the photo in default image viewer...")

                    image = Image.open(f"photos/{name}")
                    image.show()
                elif split_text[0] in ["search", "research"]:
                    prompt = ' '.join(split_text[1:])
                    search = glasses.search(prompt)

                    if search != None: # If we got a result
                        glasses.say(search)
                    else:
                        glasses.say("Sorry, I couldn't find anything.")
                elif split_text[0] == "delete" and split_text[1] in ["photos", "pictures"]:
                    self.delete_photos_loop(glasses)
                elif split_text[0] == "delete" and split_text[1] in ["videos", "recordings"]:
                    self.delete_videos_loop(glasses)
                elif spoken_text in ["read"]:
                    glasses.take_photo("image.png")

                    glasses.say("Reading...")

                    text_list = glasses.get_text_in_image("image.png")

                    if len(text_list) > 0:
                        glasses.say("The text in the photo is")

                        joined_words = ', '.join(text_list)
                        glasses.say(joined_words)
                    else:
                        glasses.say("There is no text in the photo I took, or I couldn't find any.")
                elif len(split_text) >= 2 and ((split_text[0] == "change" and split_text[1] == "your" and split_text[2] == "voice") or split_text[0] == "change" and split_text[1] == "voice"):
                    found_voice = False
                    number = None

                    if glasses.debug_mode:
                        print()

                    for word in split_text:

                        #try:

                        if glasses.debug_mode:
                            print("Checking " + word, end=' | ')

                        try:
                            number = int(word)
                        except ValueError:
                            try:
                                number = glasses.text2int(word)
                            except:
                                if glasses.debug_mode:
                                    print("Invalid word")

                        if glasses.debug_mode:
                            print(f"Number: {number}")

                        if number:
                            if glasses.debug_mode:
                                print("\n=== FINAL NUMBER ===")
                                print(number)

                            found_voice = True
                            glasses.change_voice(number)
                            break

                    if not found_voice:
                        if type(number) != int:
                            #print(type(number))
                            glasses.say("That is not a valid voice id.")
                        else:
                            glasses.change_voice(number)
                elif len(split_text) >= 2 and split_text[0] == "start" and split_text[1] == "recording":
                    glasses.start_recording_video()
                elif len(split_text) >= 2 and split_text[0] == "stop" and split_text[1] == "recording":
                    glasses.stop_recording_video()
                elif spoken_text in ["change my name", "i want to change my name", "changw my name please", "please change my name", "i would like to change my name", "i have a new name", "my name has changed"]:
                    glasses.say("What should I call you?")

                    spoken_text = glasses.recognize_speech_real_time(chat, False)

                    glasses.say(f"Ok. Your new name is {spoken_text}")
                    glasses.config.set("personalization", "name", spoken_text)
                    
                    with open("glasses_config.ini", "w") as f:
                        glasses.config.write(f)
                elif "note" in split_text and not "delete" in split_text:
                    glasses.say("What note would you like to make?")
                    speech = glasses.recognize_speech_real_time(chat, False)

                    glasses.new_note(speech)
                    self.notes_tree.clear()
                    for note in glasses.get_notes():
                        self.notes_tree.root.add_leaf(str(note))
                else:
                    possible_messages = [
                        "I can't do that, sorry.",
                        "I do not understand, I apolagise.",
                        "I do not believe I understand.",
                        "That is not something I can do, sorry."
                    ]

                    message = random.choice(possible_messages)

                    glasses.say(message)
                
        except KeyboardInterrupt:
            glasses.say("Stopping...")
            glasses.cleanup()
            glasses.clear_console()

    def on_ready(self) -> None:
        glasses.chat = self.query_one(RichLog)

        self.main_loop()

        """thread = Thread(target=self.main_loop)
        thread.start()"""

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)

        banner = Banner()
        banner.set_text("Hello, " + glasses.config.get("personalization", "name") + "!")
        yield banner

        self.notes_tree = Tree("[bold magenta]Notes List", id="notes-list")
        
        for note in glasses.get_notes():
            self.notes_tree.root.add_leaf(str(note))

        self.notes_tree.root.expand()
        yield self.notes_tree
        
        yield Markdown("# Below is your conversation.")

        yield ChatBox()

        yield Footer()


if __name__ == "__main__":
    glasses.clear_console()

    app = GlassesApp()
    app.run()