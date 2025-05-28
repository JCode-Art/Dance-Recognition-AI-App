import tkinter as tk
from tkinter import messagebox, colorchooser
from PIL import Image, ImageTk
import cv2
import mediapipe as mp
import numpy as np
import json
import time
import threading
import requests

API_KEY = "csk-f34ykd8mwr6wpc5rnevt936p3rwtpykr8t2fp3cv4m4kw68k"

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose()

class DanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dance Recognition AI")

        self.skeleton_line_color = (0, 0, 255)  
        self.skeleton_dot_color = (0, 0, 255)  

        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        console_frame = tk.Frame(left_frame, height=100, bg="lightgray")
        console_frame.pack(fill=tk.X, pady=(0,5))
        console_label = tk.Label(console_frame, text="Console Panel")
        console_label.pack(anchor='w')
        self.console_text = tk.Text(console_frame, height=6)
        self.console_text.pack(fill=tk.X, expand=True)

        video_anim_frame = tk.Frame(left_frame)
        video_anim_frame.pack(fill=tk.BOTH, expand=True)

        self.video_label = tk.Label(video_anim_frame, bg='black')
        self.video_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))

        self.animation_canvas = tk.Canvas(video_anim_frame, bg='white', width=320)
        self.animation_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0))

        self.text_output = tk.Text(left_frame, height=10)
        self.text_output.pack(fill=tk.X, pady=(5,0))

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(right_frame, text="Select Camera Source:").pack(anchor="w")
        self.source_var = tk.StringVar(value="Webcam")
        tk.Radiobutton(right_frame, text="Webcam", variable=self.source_var, value="Webcam").pack(anchor="w")
        tk.Radiobutton(right_frame, text="Phone", variable=self.source_var, value="Phone").pack(anchor="w")

        self.start_button = tk.Button(right_frame, text="Start Dance Capture", command=self.run_capture_thread)
        self.start_button.pack(pady=10)

        self.recustomize_button = tk.Button(right_frame, text="Recustomize", command=self.open_recustomize_window)
        self.recustomize_button.pack(pady=10)

        self.start_over_button = tk.Button(right_frame, text="Start Over", command=self.start_over)
        self.start_over_button.pack(pady=10)

       
        self.cap = None
        self.landmark_history = []
        self.running = False
        self.animation_index = 0

    def open_recustomize_window(self):
        win = tk.Toplevel(self.root)
        win.title("Recustomize Skeleton Colors")

        tk.Label(win, text="Select Skeleton Line Color:").pack(pady=5)
        btn_line_color = tk.Button(win, text="Choose Line Color", command=lambda: self.choose_color('line', win))
        btn_line_color.pack(pady=5)

        tk.Label(win, text="Select Skeleton Dot Color:").pack(pady=5)
        btn_dot_color = tk.Button(win, text="Choose Dot Color", command=lambda: self.choose_color('dot', win))
        btn_dot_color.pack(pady=5)

        close_btn = tk.Button(win, text="Close", command=win.destroy)
        close_btn.pack(pady=10)

    def choose_color(self, part, window):
        color = colorchooser.askcolor()[0]  
        if color:

            bgr_color = (int(color[2]), int(color[1]), int(color[0]))
            if part == 'line':
                self.skeleton_line_color = bgr_color
                self.log_console(f"Line color set to {bgr_color}")
            elif part == 'dot':
                self.skeleton_dot_color = bgr_color
                self.log_console(f"Dot color set to {bgr_color}")

    def log_console(self, message):
        self.console_text.insert(tk.END, message + "\n")
        self.console_text.see(tk.END)

    def run_capture_thread(self):
        if self.running:
            return
        self.animation_canvas.delete("all")
        threading.Thread(target=self.capture_dance).start()

    def capture_dance(self):
        self.running = True
        self.text_output.delete(1.0, tk.END)
        self.console_text.delete(1.0, tk.END)

        source = self.source_var.get()
        camera_index = 0 if source == "Webcam" else 1

        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", f"Unable to access camera index {camera_index}.")
            self.running = False
            return

        self.landmark_history.clear()
        self.console_text.insert(tk.END, "Recording dance for 10 seconds...\n")
        start_time = time.time()
        duration = 10

        def update():
            if not self.running:
                return

            ret, frame = self.cap.read()
            if not ret:
                self.stop_capture()
                return

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image)

            if results.pose_landmarks:
                landmark_frame = [(lm.x, lm.y, lm.z) for lm in results.pose_landmarks.landmark]
                self.landmark_history.append(landmark_frame)

                mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing.DrawingSpec(color=self.skeleton_dot_color, thickness=5, circle_radius=3),
                    connection_drawing_spec=mp_drawing.DrawingSpec(color=self.skeleton_line_color, thickness=3, circle_radius=2),
                )

            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

            elapsed = time.time() - start_time
            if elapsed < duration:
                self.root.after(10, update)
            else:
                self.stop_capture()

        self.root.after(0, update)

    def stop_capture(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

        self.console_text.insert(tk.END, "\nRecording complete.\nProcessing...\n")

        summary = self.summarize_motion(self.landmark_history)
        self.console_text.insert(tk.END, f"\nSummary:\n{summary}\n\nSending to AI...\n")
        threading.Thread(target=self.send_to_cerebras, args=(summary,)).start()

        self.animation_index = 0
        self.animate_pose()

    def animate_pose(self):
        self.animation_canvas.delete("all")

        if self.animation_index >= len(self.landmark_history):
            self.console_text.insert(tk.END, "\nAnimation finished.\n")
            return

        landmarks = self.landmark_history[self.animation_index]

        def to_canvas_coords(x, y):
            return int(x * self.animation_canvas.winfo_width()), int(y * self.animation_canvas.winfo_height())

        connections = mp_pose.POSE_CONNECTIONS

        line_color_hex = "#%02x%02x%02x" % (self.skeleton_line_color[2], self.skeleton_line_color[1], self.skeleton_line_color[0])
        dot_color_hex = "#%02x%02x%02x" % (self.skeleton_dot_color[2], self.skeleton_dot_color[1], self.skeleton_dot_color[0])

        for connection in connections:
            start_idx, end_idx = connection
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                x1, y1 = to_canvas_coords(landmarks[start_idx][0], landmarks[start_idx][1])
                x2, y2 = to_canvas_coords(landmarks[end_idx][0], landmarks[end_idx][1])
                self.animation_canvas.create_line(x1, y1, x2, y2, fill=line_color_hex, width=3)

        for (x, y, z) in landmarks:
            cx, cy = to_canvas_coords(x, y)
            self.animation_canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill=dot_color_hex)

        self.animation_index += 1
        self.root.after(33, self.animate_pose)

    def summarize_motion(self, history):
        motions = []
        left_hand = [frame[15] for frame in history if len(frame) > 16]
        right_hand = [frame[16] for frame in history if len(frame) > 16]

        def movement_metric(points):
            return sum(np.linalg.norm(np.array(points[i]) - np.array(points[i-1])) for i in range(1, len(points)))

        if not left_hand or not right_hand:
            return "Not enough data to analyze motion."

        left_move = movement_metric(left_hand)
        right_move = movement_metric(right_hand)

        if left_move > 2 or right_move > 2:
            motions.append("Significant arm movement detected.")
        if max(p[1] for p in left_hand) < 0.5 and max(p[1] for p in right_hand) < 0.5:
            motions.append("Hands raised above shoulders frequently.")
        if left_move < 0.5 and right_move < 0.5:
            motions.append("Arms stayed mostly still.")

        return " ".join(motions)

    def send_to_cerebras(self, summary_text):
        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "qwen-3-32b",
            "stream": True,
            "max_tokens": 16382,
            "temperature": 0.7,
            "top_p": 0.95,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert in identifying dance styles based on human motion."
                },
                {
                    "role": "user",
                    "content": f"I observed the following movements: {summary_text}. What type of dance could this be?"
                }
            ]
        }

        try:
            with requests.post(url, headers=headers, json=payload, stream=True) as response:
                if response.status_code != 200:
                    self.console_text.insert(tk.END, f"Error: {response.status_code}\n{response.text}")
                    return
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data:"):
                            try:
                                data = json.loads(decoded_line[5:])
                                content = data['choices'][0]['delta'].get('content', '')
                                self.console_text.insert(tk.END, content)
                                self.console_text.see(tk.END)
                            except Exception:
                                continue
        except Exception as e:
            self.console_text.insert(tk.END, f"\nException sending request: {e}")

    def start_over(self):
        # Reset app state
        self.log_console("Starting over. Resetting all data and UI.")
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.landmark_history.clear()
        self.animation_index = 0
        self.console_text.delete(1.0, tk.END)
        self.text_output.delete(1.0, tk.END)
        self.animation_canvas.delete("all")
        self.video_label.configure(image='')

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x700")
    app = DanceApp(root)
    root.mainloop()