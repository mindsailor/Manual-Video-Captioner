import os
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import vlc
import cv2
from pathlib import Path
import pathlib

class CustomPathEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Path):
            # Convert the path to a string and replace forward slashes with backslashes for Windows compatibility
            return str(obj.resolve()).replace("/", "\\")
        return super().default(obj)


def dict_to_object(dct):
    if "video_path" in dct:
        dct["video_path"] = Path(dct["video_path"])

    if "frame_index" in dct:
        try:
            dct["frame_index"] = int(dct["frame_index"])
        except ValueError:
            pass

    if "prompt" in dct:
        if not isinstance(dct["prompt"], dict):
            dct["prompt"] = {"prompt": dct["prompt"]}

    return dct


class VideoPlayerWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Video Player")
        self.geometry("800x600")
        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()

        self.embed = tk.Frame(self, width=800, height=600)
        self.embed.pack()
        self.vlc_player.set_hwnd(self.embed.winfo_id())

        self.resolution_label = tk.Label(self, text="Resolution: N/A")
        self.resolution_label.pack()

    def set_media(self, media_path, prompts):
        self.media_path = media_path
        self.prompts = prompts
        self.media = self.vlc_instance.media_new(str(media_path))  # Convert Path object to string
        self.vlc_player.set_media(self.media)
        self.vlc_player.play()  # Start playing to get video resolution
        self.loop_video = True

    def play_video(self):
        if self.loop_video and not self.vlc_player.is_playing():
            self.vlc_player.play()

        self.after(100, self.play_video)

        # Create frame index entries for each frame
        self.create_frame_index_entries()

        self.update_resolution_label()

    def get_total_frames(self, media_path):
        try:
            cap = cv2.VideoCapture(media_path)
            if cap.isOpened():
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                return total_frames
        except cv2.error:
            pass
        return 0

    def create_frame_index_entries(self):
        self.frame_prompts = {}
        for frame_index in range(1, self.total_frames + 1):
            prompt = ""
            if self.media_path in self.prompts:
                if frame_index in self.prompts[self.media_path]:
                    prompt = self.prompts[self.media_path][frame_index]
            self.frame_prompts[frame_index] = prompt

    def update_resolution_label(self):
        if self.vlc_player.get_length() > 0:
            frame_width, frame_height = self.get_video_resolution(self.media.get_mrl())
            if frame_width and frame_height:
                self.resolution_label.config(text=f"Resolution: {frame_width}x{frame_height}")
            else:
                self.resolution_label.config(text="Resolution: N/A")

        # If the video is not yet ready, schedule the resolution update after 100ms
        if not self.vlc_player.get_length():
            self.after(100, self.update_resolution_label)

    def get_video_resolution(self, media_path):
        try:
            cap = cv2.VideoCapture(media_path)
            if cap.isOpened():
                frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                return frame_width, frame_height
        except cv2.error:
            pass
        return None, None

    def stop(self):
        self.loop_video = False
        self.vlc_player.stop()

    def start_looping(self):
        self.loop_video = True

class VideoReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Manual Video Captioner")
        self.video_files = []
        self.current_file_index = 0
        self.current_frame_index = 1
        self.options = []  # A list to store the checkbox variables and their associated texts
        self.create_option_checkboxes()  # Create checkboxes for user options

        self.total_frames = 0
        self.prompts = {}
        self.skip_delay = 0  # milliseconds DISABLED
        self.video_player_window = VideoPlayerWindow()

        self.label = tk.Label(root, text="Enter your prompt for the current video:")
        self.label.pack()

        self.entry = tk.Entry(root, width=50)
        self.entry.pack()

        self.frame_label = tk.Label(root, text="Frame: 1/1")
        self.frame_label.pack()

        self.resolution_label = tk.Label(root, text="Resolution: N/A")
        self.resolution_label.pack()

        self.submit_button = tk.Button(root, text="Submit", command=self._submit, state='normal')
        self.submit_button.pack()

        self.skip_button = tk.Button(root, text="Skip", command=self._skip_video, state='normal')
        self.skip_button.pack()

        self.junk_button = tk.Button(root, text="Junk", command=self._move_to_junk, state='normal')
        self.junk_button.pack()

        self.restart_button = tk.Button(root, text="Replay clip", command=self._restart_video, state='normal')
        self.restart_button.pack()

        self.directory_button = tk.Button(root, text="Select Directory", command=self.load_videos)
        self.directory_button.pack()

        self.master_json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "VIDEO_PROMPTS",
                                             "video_prompts.json")
        self.load_prompts_from_json()

        self.update_frame_label()

        self.total_frames_label = tk.Label(root, text="Total Frames: 0")
        self.total_frames_label.pack()


    def create_option_checkboxes(self):
        option_frame = tk.Frame(self.root)
        option_frame.pack()

        # Sample options for motion and categories
        motion_options = [
            "Zooming In", "Zooming Out", "Panning Left", "Panning Right", "Tilting Up", "Tilting Down",
            "Steady Shot", "Handheld Camera", "Fast Motion", "Slow Motion", "Time-lapse",
            "Fade In", "Fade Out", "Split Screen", "Visual Effects",
            "CGI/3D Animation", "Stop Motion",
        ]

        categories_options = [
            "People", "Landscapes", "Characters", "Animals", "Food", "Travel", "Sports", "Music", "Documentary",
            "News", "Fashion", "Comedy", "Art", "Nature", "Science", "Technology",
            "Architecture", "Transportation",
        ]

        other_options = [
            "Underwater Footage", "Aerial Footage", "Low Light Conditions", "Night Scene", "Day Scene", "Indoor",
            "Outdoor", "Close-up Shots", "Wide-angle Shots", "High-speed Action", "Slow-paced Scenes",
             "B-roll Footage", "Crowd Shots", "Product Shots",
        ]



        # Create checkboxes for motion options in two columns
        motion_label = tk.Label(option_frame, text="Motion:")
        motion_label.pack(anchor='w')
        num_motion_options = len(motion_options)
        num_columns = 8
        num_rows = (num_motion_options + num_columns - 1) // num_columns
        for i in range(num_rows):
            motion_column_frame = tk.Frame(option_frame)
            motion_column_frame.pack(side='left')
            for j in range(num_columns):
                index = i + j * num_rows
                if index < num_motion_options:
                    option_text = motion_options[index]
                    option_var = tk.IntVar()
                    checkbox = tk.Checkbutton(motion_column_frame, text=option_text, variable=option_var)
                    checkbox.pack(anchor='w')
                    self.options.append((option_var, option_text))

        # Create checkboxes for categories options in two columns
        categories_label = tk.Label(option_frame, text="Categories:")
        categories_label.pack(anchor='w')
        num_categories_options = len(categories_options)
        num_columns = 8
        num_rows = (num_categories_options + num_columns - 1) // num_columns
        for i in range(num_rows):
            categories_column_frame = tk.Frame(option_frame)
            categories_column_frame.pack(side='left')
            for j in range(num_columns):
                index = i + j * num_rows
                if index < num_categories_options:
                    option_text = categories_options[index]
                    option_var = tk.IntVar()
                    checkbox = tk.Checkbutton(categories_column_frame, text=option_text, variable=option_var)
                    checkbox.pack(anchor='w')
                    self.options.append((option_var, option_text))

        # Create checkboxes for other options in two columns
        other_label = tk.Label(option_frame, text="Other:")
        other_label.pack(anchor='w')
        num_other_options = len(other_options)
        num_columns = 8
        num_rows = (num_other_options + num_columns - 1) // num_columns
        for i in range(num_rows):
            other_column_frame = tk.Frame(option_frame)
            other_column_frame.pack(side='left')
            for j in range(num_columns):
                index = i + j * num_rows
                if index < num_other_options:
                    option_text = other_options[index]
                    option_var = tk.IntVar()
                    checkbox = tk.Checkbutton(other_column_frame, text=option_text, variable=option_var)
                    checkbox.pack(anchor='w')
                    self.options.append((option_var, option_text))

                

    def update_prompt_for_frame(self, prompt):
        video_file = self.video_files[self.current_file_index]
        frame_index = self.current_frame_index

        if video_file not in self.prompts:
            self.prompts[video_file] = {}

        self.prompts[video_file][frame_index] = {"prompt": prompt}
        self.save_to_json()  # Save the updated prompts to the JSON file
        self.video_player_window.set_media(video_file, self.prompts)  # Update the video player window with the new prompt

    def on_closing(self):
        self.save_to_json()
        self.withdraw()

    def create_frame_index_entries(self):
        self.frame_prompts = {}
        video_file = self.video_files[self.current_file_index]
        if video_file in self.prompts:
            self.frame_prompts = self.prompts[video_file]

    def save_to_json(self):
        data = {"name": "My Videos", "data": []}
        for video_file, frame_prompts in self.prompts.items():
            data_item = {"video_path": str(video_file), "num_frames": len(frame_prompts), "data": []}  # Convert Path object to string
            for frame_index, prompt in frame_prompts.items():
                data_item["data"].append(prompt)  # Append the inner dictionary directly
            data["data"].append(data_item)

        master_json_dir = Path(self.master_json_path).parent
        master_json_dir.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist

        with open(self.master_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, cls=CustomPathEncoder)  # Use the custom path encoder



    def load_prompts_from_json(self):
        if os.path.exists(self.master_json_path):
            with open(self.master_json_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f, object_hook=dict_to_object)

                    for item in data["data"]:
                        video_path = item["video_path"]
                        frame_prompts = {}
                        for frame_data in item["data"]:
                            if "frame_index" in frame_data and "prompt" in frame_data:
                                frame_index = frame_data["frame_index"]
                                prompt = frame_data["prompt"]
                                frame_prompts[frame_index] = prompt
                        self.prompts[video_path] = frame_prompts
                except json.JSONDecodeError:
                    messagebox.showwarning("Warning", "Invalid JSON format in the video prompts file.")
        else:
            messagebox.showinfo("Info", "No video prompts file found. Starting with an empty prompt list.")


    def enable_buttons(self):
        self.submit_button['state'] = 'normal'
        self.skip_button['state'] = 'normal'
        self.junk_button['state'] = 'normal'
        self.restart_button['state'] = 'normal'

    def disable_buttons_temporarily(self):
        self.submit_button['state'] = 'disabled'
        self.skip_button['state'] = 'disabled'
        self.junk_button['state'] = 'disabled'
        self.restart_button['state'] = 'disabled'
        self.root.after(self.skip_delay, self.enable_buttons)

    def load_videos(self):
        directory = filedialog.askdirectory(title="Select directory")
        if not directory:
            messagebox.showinfo("Info", "No directory selected.")
            return

        self.video_files = self.walk_directory_for_videos(directory)
        if len(self.video_files) == 0:
            messagebox.showinfo("Info", "No video files found in the selected directory and its subdirectories.")
            return

        self.current_file_index = 0
        self.current_frame_index = 1
        self.total_frames = 0

        self.display_current_video()

    def walk_directory_for_videos(self, directory):
        video_files = set()
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.mp4', '.avi')):
                    video_files.add(os.path.join(root, file))
        return list(video_files)

    def get_current_video_prompt(self):
        video_file = self.video_files[self.current_file_index]
        if video_file in self.prompts and 1 in self.prompts[video_file]:
            return self.prompts[video_file][1]["prompt"]
        return ""

    def display_current_video(self):
        if self.current_file_index < len(self.video_files):
            video_file = self.video_files[self.current_file_index]
            self.video_player_window.set_media(video_file, self.prompts)
            self.total_frames = self.video_player_window.get_total_frames(video_file)
            self.update_frame_label()

            # Get the prompt for the current video frame
            video_file = self.video_files[self.current_file_index]
            frame_index = self.current_frame_index
            if video_file in self.prompts and frame_index in self.prompts[video_file]:
                prompt = self.prompts[video_file][frame_index]
                self.entry.delete(0, 'end')  # Clear the prompt entry
                self.entry.insert(0, prompt)  # Set the prompt for the current video frame
            else:
                # No prompt found for the current frame, set the entry to an empty string
                self.entry.delete(0, 'end')  # Clear the prompt entry

            self.entry.focus_set()  # Set focus to the prompt entry

    def _submit(self):
        video_file = self.video_files[self.current_file_index]
        prompt = self.entry.get()

        # Get the selected options from the GUI
        selected_options = []
        for option_var, option_text in self.options:
            if option_var.get() == 1:
                selected_options.append(option_text)

        # Concatenate the user-entered prompt with the selected options, separated by commas
        if selected_options:
            prompt += ", " + ", ".join(selected_options)

        if video_file not in self.prompts:
            self.prompts[video_file] = {}

        for frame_index in range(1, self.total_frames + 1):
            if frame_index not in self.prompts[video_file]:
                frame_prompt = {
                    "frame_index": frame_index,
                    "prompt": prompt
                }
                self.prompts[video_file][frame_index] = frame_prompt

        self.entry.delete(0, 'end')
        self.clear_options()  # Clear the selected options
        self.save_to_json()  # Write data to the JSON file after submitting the prompt
        self.video_player_window.set_media(video_file, self.prompts)  # Update the video player window with the new prompt
        self.next_video()
        

    def _skip_video(self):
        self.disable_buttons_temporarily()
        self.video_player_window.stop()
        self.next_video()

    def _move_to_junk(self):
        video_file = self.video_files[self.current_file_index]

        # Convert the video_file to a Path object
        video_file_path = pathlib.Path(video_file)

        # Stop the video player window if it's currently playing the video.
        self.video_player_window.stop()

        # Wait for a short delay to ensure the video player is fully stopped.
        self.root.after(200)

        # Move the video file to the junk folder.
        self.copy_to_junk_folder(video_file_path)

        # Update the video_files list and remove the moved video from the list.
        self.video_files.pop(self.current_file_index)

        # Continue with the next video if there are more videos to review.
        if self.current_file_index < len(self.video_files):
            self.display_current_video()
            self.current_frame_index = 1  # Reset the current_frame_index when moving to the next video
        else:
            # Show a message when all videos have been reviewed.
            messagebox.showinfo("Info", "All videos have been reviewed.")
            self.root.destroy()  # Close the application window when all videos have been reviewed

        # Enable buttons after moving to the next video.
        self.enable_buttons()

    def update_frame_index(self):
        # This method is called after the prompt is submitted or when the VideoPlayerWindow advances to the next frame.
        self.current_frame_index += 1

        if self.current_frame_index <= self.total_frames:
            self.update_frame_label()

            # Get the prompt for the current video frame
            video_file = self.video_files[self.current_file_index]
            if video_file in self.prompts and self.current_frame_index in self.prompts[video_file]:
                prompt = self.prompts[video_file][self.current_frame_index]["prompt"]
                self.entry.delete(0, 'end')  # Clear the prompt entry
                self.entry.insert(0, prompt)  # Set the prompt for the current video frame
        else:
            self.current_frame_index = 1
            self.current_file_index += 1
            self.display_current_video()

    def next_video(self):
        self.current_file_index += 1
        if self.current_file_index < len(self.video_files):
            self.display_current_video()
            self.current_frame_index = 1  # Reset the current_frame_index when moving to the next video
        else:
            messagebox.showinfo("Info", "All videos have been reviewed.")
            self.current_file_index = len(self.video_files) - 1
            self.display_current_video()

    
    def update_frame_label(self):
        self.frame_label.config(text=f"Frame: {self.current_frame_index}/{self.total_frames}")

    def _restart_video(self):
        self.video_player_window.stop()
        self.display_current_video()

    def copy_to_junk_folder(self, video_file):
        junk_folder = Path(self.master_json_path).parent / "junk"
        junk_folder.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist

        filename = video_file.name
        filename_no_ext = video_file.stem

        # Check if the file already exists in the junk folder
        file_number = 1
        new_filename = filename
        while (junk_folder / new_filename).exists():
            new_filename = f"{filename_no_ext}_{file_number}{video_file.suffix}"
            file_number += 1

        # Move the video file to the junk folder with the new filename
        new_file_path = junk_folder / new_filename
        try:
            # Use shutil.move to move the file (allows moving between different disk drives)
            import shutil
            shutil.move(video_file, new_file_path)

            # Update the video_files list and the total_frames for the current video
            self.total_frames = 0  # Reset the total_frames
            for i, file in enumerate(self.video_files):
                if file == video_file:
                    self.video_files[i] = new_file_path
                    self.total_frames = self.video_player_window.get_total_frames(new_file_path)
                    break
        except OSError as e:
            messagebox.showerror("Error", f"Failed to move the video file to junk: {e}")


    def clear_options(self):
        # Clear the selected options by resetting each IntVar associated with the checkboxes to 0 (unchecked state)
        for option_var, _ in self.options:
            option_var.set(0)

        def previous_video(self):
            self.save_to_json()

            self.current_file_index -= 1
            if self.current_file_index >= 0:
                self.display_current_video()
                self.current_frame_index = 1  # Reset the current_frame_index when moving to the previous video
            else:
                messagebox.showinfo("Info", "This is the first video.")
                self.current_file_index = 0
                self.display_current_video()

        


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoReviewApp(root)
    app.video_player_window.master = app  # Set the VideoReviewApp as the master of the VideoPlayerWindow
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    # Destroy the VideoPlayerWindow properly after the main application is closed.
    app.video_player_window.destroy()
