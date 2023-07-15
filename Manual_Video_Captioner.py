import cv2
import os
import time
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread, Event
from PIL import Image, ImageTk


class VideoReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Manual Video Captioner")
        self.video_files = []
        self.current_file_index = 0
        self.play_video = True
        self.current_frame = 0
        self.total_frames = 0
        self.video_stopped = Event()
        self.latest_frame = None
        self.skip_delay = 3000  # milliseconds
        self.last_skip_time = 0

        self.label = tk.Label(root, text="Enter your prompt for the current video:")
        self.label.pack()

        self.entry = tk.Entry(root, width=50)
        self.entry.pack()

        self.frame_label = tk.Label(root, text="Frame: 0/0")
        self.frame_label.pack()

        self.resolution_label = tk.Label(root, text="Resolution: N/A")
        self.resolution_label.pack()

        self.submit_button = tk.Button(root, text="Submit", command=self._submit, state='normal')
        self.submit_button.pack()

        self.skip_button = tk.Button(root, text="Skip", command=self._skip_video, state='normal')
        self.skip_button.pack()

        self.junk_button = tk.Button(root, text="Junk", command=self._move_to_junk, state='normal')
        self.junk_button.pack()

        self.directory_button = tk.Button(root, text="Select Directory", command=self.load_videos)
        self.directory_button.pack()

        self.video_label = tk.Label(self.root)
        self.video_label.pack()

        self.update_frame_label()

    def enable_buttons(self):
        self.submit_button['state'] = 'normal'
        self.skip_button['state'] = 'normal'
        self.junk_button['state'] = 'normal'

    def disable_buttons_temporarily(self):
        self.submit_button['state'] = 'disabled'
        self.skip_button['state'] = 'disabled'
        self.junk_button['state'] = 'disabled'
        self.root.after(self.skip_delay, self.enable_buttons)

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
            print("No video files found in the selected directory.")
            return

        self.current_file_index = 0
        self.display_current_video()

    def display_current_video(self):
        if self.current_file_index >= len(self.video_files):
            return

        video_file = self.video_files[self.current_file_index]
        print(f"Attempting to open video file: {video_file}")

        self.play_video = True
        self.current_frame = 0
        self.total_frames = 0

        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            print(f"Failed to open video file: {video_file}")
            return
        else:
            print(f"Successfully opened video file: {video_file}")

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.resolution_label.config(text=f"Resolution: {width}x{height}")

        self.cap = cap

        self.latest_frame = None
        Thread(target=self.preview_video).start()
        self.update_video_label()

    def preview_video(self):
        self.video_stopped.clear()
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
            self.latest_frame = ImageTk.PhotoImage(image=Image.fromarray(frame))
            time.sleep(frame_delay / 1000)

        self.video_stopped.set()
        self.cap.release()

    def update_video_label(self):
        if self.latest_frame is not None:
            self.video_label.config(image=self.latest_frame)
            self.video_label.image = self.latest_frame
        self.root.after(10, self.update_video_label)

    def stop_video(self):
        self.play_video = False
        self.video_stopped.wait()
        self.cap.release()

    def _submit(self):
        if not self.video_files:
            print("No video files loaded. Please select a directory first.")
            return

        current_time = time.time()
        if current_time - self.last_skip_time < self.skip_delay / 1000:
            return

        self.last_skip_time = current_time

        self.disable_buttons_temporarily()
        self.stop_video()
        self.submit_prompt()

        if self.current_file_index + 1 < len(self.video_files):
            self.next_video()
        else:
            print("No more videos to process.")
            messagebox.showinfo("Info", "All videos have been processed.")
            self.enable_buttons()

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

        print(f'Prompt output: {prompt} saved at location: {new_output_file}')

    def _skip_video(self):
        if not self.video_files:
            print("No video files loaded. Please select a directory first.")
            return

        current_time = time.time()
        if current_time - self.last_skip_time < self.skip_delay / 1000:
            return

        self.last_skip_time = current_time

        self.disable_buttons_temporarily()
        self.stop_video()

        if self.current_file_index + 1 < len(self.video_files):
            self.next_video()
        else:
            print("No more videos to process.")
            messagebox.showinfo("Info", "All videos have been processed.")
            self.enable_buttons()

    def _move_to_junk(self):
        if not self.video_files:
            print("No video files loaded. Please select a directory first.")
            return

        current_time = time.time()
        if current_time - self.last_skip_time < self.skip_delay / 1000:
            return

        self.last_skip_time = current_time

        self.disable_buttons_temporarily()
        self.stop_video()
        self.move_to_junk()

        if self.current_file_index + 1 < len(self.video_files):
            self.next_video()
        else:
            print("No more videos to process.")
            messagebox.showinfo("Info", "All videos have been processed.")
            self.enable_buttons()

    def move_to_junk(self):
        video_file = self.video_files[self.current_file_index]
        junk_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "junk")

        if not os.path.exists(junk_dir):
            os.makedirs(junk_dir)

        base_name = os.path.basename(video_file)
        output_file_base = os.path.splitext(base_name)[0]
        extension = os.path.splitext(base_name)[1]

        counter = 1
        while True:
            if counter > 1:
                new_base_name = f"{output_file_base}_{counter}"
            else:
                new_base_name = output_file_base

            new_video_file = os.path.join(junk_dir, new_base_name + extension)

            if not os.path.exists(new_video_file):
                break

            counter += 1

        for _ in range(5):
            try:
                shutil.move(video_file, new_video_file)
                break
            except PermissionError:
                time.sleep(1)

    def next_video(self):
        self.play_video = True
        self.current_file_index += 1
        if self.current_file_index >= len(self.video_files):
            self.root.quit()
            return

        self.display_current_video()

    def update_frame_label(self):
        if self.root:
            self.frame_label.config(text=f"Frame: {self.current_frame}/{self.total_frames}")
            self.root.after(1000, self.update_frame_label)


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoReviewApp(root)
    root.mainloop()

