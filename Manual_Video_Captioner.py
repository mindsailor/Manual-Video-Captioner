import cv2
import os
import time
import shutil
import tkinter as tk
from tkinter import filedialog
from threading import Thread
from PIL import Image, ImageTk

class VideoReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Caption App")
        self.video_files = []
        self.current_file_index = 0
        self.play_video = True
        self.current_frame = 0
        self.total_frames = 0
        self.video_stopped = False

        self.label = tk.Label(root, text="Enter your prompt for the current video:")
        self.label.pack()

        self.entry = tk.Entry(root, width=50)
        self.entry.pack()

        self.frame_label = tk.Label(root, text="Frame: 0/0")
        self.frame_label.pack()

        self.submit_button = tk.Button(root, text="Submit", command=self.submit_and_next)
        self.submit_button.pack()

        self.skip_button = tk.Button(root, text="Skip", command=self.skip_video)
        self.skip_button.pack()

        self.junk_button = tk.Button(root, text="Junk", command=self.move_to_junk)
        self.junk_button.pack()

        self.directory_button = tk.Button(root, text="Select Directory", command=self.load_videos)
        self.directory_button.pack()

        self.video_label = tk.Label(self.root) # move this line to here
        self.video_label.pack()

        self.update_frame_label()

    def load_videos(self):
        self.video_files = []
        dir_path = filedialog.askdirectory(title="Select directory")
        if not dir_path:
            return

        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower().endswith((".mp4", ".mkv", ".webm", ".gif")):
                    self.video_files.append(os.path.join(root, file))

        if not self.video_files:
            return

        self.current_file_index = 0
        self.display_current_video()

    def display_current_video(self):
        if self.current_file_index >= len(self.video_files):
            return

        video_file = self.video_files[self.current_file_index]
        self.play_video = True
        self.current_frame = 0
        self.total_frames = 0
        self.cap = cv2.VideoCapture(video_file)
        Thread(target=self.preview_video).start()

        Thread(target=self.preview_video, args=(video_file,)).start()

    def preview_video(self):
        self.video_stopped = False
        try:
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            frame_delay = int(1000 / fps)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

            while self.play_video and self.cap.isOpened():
                ret, frame = self.cap.read()
                self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

                if not ret or self.current_frame == self.total_frames:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)

                self.video_label.config(image=imgtk)
                self.video_label.image = imgtk

                time.sleep(frame_delay / 1000)

            self.video_stopped = True
        finally:
            self.cap.release()

    def stop_video(self):
        self.play_video = False
        while not self.video_stopped:
            time.sleep(0.1)
        self.cap.release()  # release cap here

    def submit_prompt(self):
        prompt = self.entry.get()
        video_file = self.video_files[self.current_file_index]
        base_name = os.path.basename(video_file)
        output_file_base = os.path.splitext(base_name)[0]
        extension = os.path.splitext(base_name)[1]

        processed_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "PROCESSED_VIDEO_CAPTIONS")

        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir)

        counter = 1
        while True:
            if counter > 1:
                new_base_name = f"{output_file_base}_{counter}"
            else:
                new_base_name = output_file_base

            new_video_file = os.path.join(processed_dir, new_base_name + extension)
            new_output_file = os.path.join(processed_dir, new_base_name + ".txt")

            if not os.path.exists(new_video_file) and not os.path.exists(new_output_file):
                break

            counter += 1

        shutil.copy(video_file, new_video_file)
        with open(new_output_file, "w") as f:
            f.write(prompt)
        self.entry.delete(0, 'end')

    def submit_and_next(self):
        self.stop_video()
        self.submit_prompt()
        self.next_video()

    def skip_video(self):
        self.stop_video()
        self.next_video()

    def move_to_junk(self):
        self.stop_video()
        video_file = self.video_files[self.current_file_index]
        junk_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "junk")

        if not os.path.exists(junk_dir):
            os.makedirs(junk_dir)

        for _ in range(5):
            try:
                shutil.move(video_file, os.path.join(junk_dir, os.path.basename(video_file)))
                break
            except PermissionError:
                time.sleep(1)

        self.next_video()

    def next_video(self):
        self.play_video = True
        self.current_file_index += 1
        if self.current_file_index >= len(self.video_files):
            self.root.destroy()
            return

        self.display_current_video()

    def update_frame_label(self):
        self.frame_label.config(text=f"Frame: {self.current_frame}/{self.total_frames}")
        self.root.after(1000, self.update_frame_label)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoReviewApp(root)
    root.mainloop()

