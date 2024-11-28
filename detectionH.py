import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import cv2
import numpy as np
import zxing  # ZXing wrapper
import time  # Added for timestamp management
from hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from detection_pipeline import GStreamerDetectionApp

# -----------------------------------------------------------------------------------------------
# User-defined callback class
# -----------------------------------------------------------------------------------------------
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame_count = 0
        self.last_processed_time = 0  # For limiting to 1 frame per second

    def increment(self):
        self.frame_count += 1

    def get_count(self):
        return self.frame_count

    def can_process_frame(self):
        current_time = time.time()
        if current_time - self.last_processed_time >= 1:  # Check if 1 second has passed
            self.last_processed_time = current_time
            return True
        return False

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Limit processing to 1 frame per second
    if not user_data.can_process_frame():
        return Gst.PadProbeReturn.OK

    # Increment frame count
    user_data.increment()
    frame_count = user_data.get_count()

    # Extract frame information
    format, width, height = get_caps_from_pad(pad)
    frame = get_numpy_from_buffer(buffer, format, width, height)
    if frame is None:
        print(f"Frame {frame_count}: Unable to retrieve frame.")
        return Gst.PadProbeReturn.OK

    # Ensure the frame is in RGB format for processing
    if len(frame.shape) == 3 and frame.shape[2] == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # QR Code Detection with OpenCV
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(frame)

    detected_qr = []
    if points is not None:
        for i in range(points.shape[0]):
            x_min = int(min(points[i][:, 0]))
            y_min = int(min(points[i][:, 1]))
            x_max = int(max(points[i][:, 0]))
            y_max = int(max(points[i][:, 1]))
            detected_qr.append({"x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max})

        print(f"Frame {frame_count}: Detected QR Code Data: {data}")
    else:
        print(f"Frame {frame_count}: No QR code detected.")

    # Process each detected QR code
    for idx, bbox in enumerate(detected_qr):
        # Extract bounding box
        x_min, y_min, x_max, y_max = bbox["x_min"], bbox["y_min"], bbox["x_max"], bbox["y_max"]

        # Crop the QR code from the frame
        cropped = frame[y_min:y_max, x_min:x_max]

        # Save the cropped image to a temporary directory
        temp_dir = "/tmp/qrcodes"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f"qr_code_{frame_count}_{idx}.jpg")
        cv2.imwrite(temp_file_path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))

        # Process the cropped image with ZXing
        try:
            reader = zxing.BarCodeReader()
            qr_code = reader.decode(temp_file_path)
            if qr_code:
                qr_data = qr_code.raw
                print(f"Frame {frame_count}, QR {idx}: {qr_data}")

                # Draw bounding box and QR data on the frame
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                cv2.putText(frame, qr_data, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                print(f"Frame {frame_count}, QR {idx}: No data decoded")
        except Exception as e:
            print(f"Error decoding QR code on frame {frame_count}, QR {idx}: {e}")

    # Save the annotated frame
    save_dir = "/home/david/detection/"
    os.makedirs(save_dir, exist_ok=True)
    frame_path = os.path.join(save_dir, f"frame_{frame_count}.jpg")
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    cv2.imwrite(frame_path, frame_bgr)

    return Gst.PadProbeReturn.OK

# -----------------------------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------------------------
class GStreamerDetectionAppWithAnnotations(GStreamerDetectionApp):
    def __init__(self, callback, user_data):
        super().__init__(callback, user_data)

    def build_pipeline(self):
        pipeline = Gst.Pipeline()

        # Source element
        source = Gst.ElementFactory.make("v4l2src", "source")
        source.set_property("device", "/dev/video0")

        # Video scaler for resolution
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        caps = Gst.Caps.from_string("video/x-raw, width=640, height=640, format=RGB")
        capsfilter.set_property("caps", caps)

        # Video converter
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")

        # Appsink for callback
        appsink = Gst.ElementFactory.make("appsink", "appsink")
        appsink.set_property("emit-signals", True)
        appsink.set_property("sync", False)
        appsink.connect("new-sample", self.on_new_sample)

        # Display sink
        sink = Gst.ElementFactory.make("xvimagesink", "xvimagesink")

        if not pipeline or not source or not capsfilter or not videoconvert or not appsink or not sink:
            print("Failed to create GStreamer pipeline elements")
            return None

        # Add and link elements
        pipeline.add(source)
        pipeline.add(capsfilter)
        pipeline.add(videoconvert)
        pipeline.add(appsink)
        pipeline.add(sink)
        source.link(capsfilter)
        capsfilter.link(videoconvert)
        videoconvert.link(appsink)

        return pipeline

if __name__ == "__main__":
    # Initialize GStreamer
    Gst.init(None)

    # User data and application
    user_data = user_app_callback_class()
    app = GStreamerDetectionAppWithAnnotations(app_callback, user_data)
    app.run()
