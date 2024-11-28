import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import cv2
import numpy as np
from pylibdmtx.pylibdmtx import decode  # Import DMC decoding library
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

    def increment(self):
        self.frame_count += 1

    def get_count(self):
        return self.frame_count

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
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

    # Detect Data Matrix Codes in the frame
    decoded_objects = decode(frame)
    for obj in decoded_objects:
        # Extract Data Matrix Code data and bounding box
        dmc_data = obj.data.decode('utf-8')
        x, y, w, h = obj.rect.left, obj.rect.top, obj.rect.width, obj.rect.height

        # Draw a rectangle around the DMC
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Write DMC content onto the frame
        cv2.putText(frame, dmc_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        print(f"Frame {frame_count}: Detected DMC with data: {dmc_data}")

    # Save the frame with annotations
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

    # Caps filter to enforce 640x640 resolution
    capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
    caps = Gst.Caps.from_string("video/x-raw, width=640, height=640, format=RGB")
    capsfilter.set_property("caps", caps)
    pipeline.add(capsfilter)
    source.link(capsfilter)
    capsfilter.link(videoconvert)

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

