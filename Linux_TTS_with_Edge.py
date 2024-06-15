#!/usr/bin/env python3


import asyncio
import edge_tts
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
import ffmpeg
from ffmpeg import Error as FFmpegError
import pygame
import os
import curses
import curses.textpad

VOICE = "en-GB-SoniaNeural"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Edge TTS GUI")
        self.geometry("400x500")
        
        self.file_label = tk.Label(self, text="Select Input File:")
        self.file_label.pack(pady=10)
        
        self.file_path = tk.StringVar()
        self.file_entry = tk.Entry(self, textvariable=self.file_path, width=40)
        self.file_entry.pack()
        
        # Create a frame for the Browse and Process buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        self.browse_button = tk.Button(button_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=10)

        self.process_button = tk.Button(button_frame, text="Process Input File", command=self.process_file)
        self.process_button.pack(side=tk.LEFT, padx=10)

        self.clipboard_button = tk.Button(self, text="Process Clipboard Text", command=self.process_clipboard)
        self.clipboard_button.pack(pady=10)

        self.progress_label = tk.Label(self, text="")
        self.progress_label.pack()
        
        self.progress_bar = Progressbar(self, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress_bar.pack(pady=10)
        
        # Create a frame for the Play and Reset buttons
        button_frame1 = tk.Frame(self)
        button_frame1.pack(pady=10)
        
        self.play_button = tk.Button(button_frame1, text="Play", command=self.toggle_play_pause)
        self.play_button.pack(side=tk.LEFT, pady=10)

        self.reset_button = tk.Button(button_frame1, text="Reset", command=self.reset_audio)
        self.reset_button.pack(side=tk.LEFT, pady=10)

        self.exit_button = tk.Button(self, text="Exit", command=self.exit_program)
        self.exit_button.pack(pady=10)
        
        pygame.mixer.init()
        self.is_playing = False
        self.is_paused = False
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            self.file_path.set(file_path)
    
    def process_file(self):
        input_file = self.file_path.get()
        if not input_file:
            messagebox.showerror("Error", "Please select an input file.")
            return

        # Delete previous output files if they exist
        if os.path.exists("output.wav"):
            os.remove("output.wav")
        if os.path.exists("output_speed_adjusted.wav"):
            os.remove("output_speed_adjusted.wav")
        
        self.progress_label.config(text="Processing...")
        self.progress_bar['value'] = 0
        self.progress_bar.update()
        
        try:
            # Execute processing asynchronously
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.process_audio_from_file(input_file))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        self.progress_label.config(text="Processing complete")
        self.progress_bar['value'] = 100

    def process_clipboard(self):
        self.reset_audio()
        try:
            clipboard_text = self.clipboard_get()
        except tk.TclError:
            messagebox.showerror("Error", "No text found in clipboard.")
            return

        # Delete previous output files if they exist
        if os.path.exists("output.wav"):
            os.remove("output.wav")
        if os.path.exists("output_speed_adjusted.wav"):
            os.remove("output_speed_adjusted.wav")
        
        self.progress_label.config(text="Processing clipboard text...")
        self.progress_bar['value'] = 0
        self.progress_bar.update()
        
        try:
            # Execute processing asynchronously
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.process_audio_from_text(clipboard_text))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        self.progress_label.config(text="Processing complete")
        self.progress_bar['value'] = 100

        self.toggle_play_pause()


    def get_highlighted_text(self):
        try:
            stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)

            # Initialize textpad
            pad = curses.newpad(500, 500)
            pad.refresh(0, 0, 0, 0, 500, 500)

            # Let the user highlight text
            box = curses.textpad.Textbox(pad)
            box.edit()
            return box.gather()
        finally:
            curses.nocbreak()
            stdscr.keypad(False)
            curses.echo()
            curses.endwin()

    async def process_audio_from_file(self, input_file):
        # Read the text from the input file
        with open(input_file, 'r', encoding='utf-8') as file:
            text = file.read()
        await self.process_audio_from_text(text)

    async def process_audio_from_text(self, text):
        # Initialize the Edge TTS client with the text and voice
        communicate = edge_tts.Communicate(text, VOICE)

        # Open the output file in write-binary mode
        output_file = "output.wav"
        with open(output_file, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])

        # Post-processing: Adjust speed using ffmpeg-python
        try:
            # Use ffmpeg.input() correctly to create a stream object
            input_stream = ffmpeg.input(output_file)
            output_stream = ffmpeg.output(input_stream, 'output_speed_adjusted.wav', filter='atempo=1.5')
            ffmpeg.run(output_stream)
        except FFmpegError as e:
            raise RuntimeError(f"ffmpeg error: {str(e)}")
    
    def toggle_play_pause(self):
        try:
            if not self.is_playing:
                pygame.mixer.music.load("output_speed_adjusted.wav")
                pygame.mixer.music.play()
                self.play_button.config(text="Pause")
                self.is_playing = True
                self.is_paused = False
            elif not self.is_paused:
                pygame.mixer.music.pause()
                self.play_button.config(text="Play")
                self.is_paused = True
            else:
                pygame.mixer.music.unpause()
                self.play_button.config(text="Pause")
                self.is_paused = False
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while trying to play/pause the audio: {str(e)}")

    def reset_audio(self):
        try:
            pygame.mixer.music.stop()
            self.play_button.config(text="Play")
            self.is_playing = False
            self.is_paused = False
            if os.path.exists("output.wav"):
                os.remove("output.wav")
            if os.path.exists("output_speed_adjusted.wav"):
                os.remove("output_speed_adjusted.wav")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while resetting: {str(e)}")

    def exit_program(self):
        try:
            pygame.mixer.music.stop()
            if os.path.exists("output.wav"):
                os.remove("output.wav")
            if os.path.exists("output_speed_adjusted.wav"):
                os.remove("output_speed_adjusted.wav")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while exiting: {str(e)}")
        finally:
            self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()

