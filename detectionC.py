import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import cv2
import hailo
from hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from detection_pipeline import GStreamerDetectionApp
from pyzbar import pyzbar
import json

# Initialize GStreamer
Gst.init(None)

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42  # New variable example

    def new_function(self):  # New function example
        return "The meaning of life is: "

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------
# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    print("Callback function called-__-C")
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    if buffer is None:
        print("Buffer is None")
        return Gst.PadProbeReturn.OK

    # Using the user_data to count the number of frames
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)
    print(f"Caps: format={format}, width={width}, height={height}")

    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        # Get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)
        if frame is not None:
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            elif len(frame.shape) == 2:
                # Frame is already in grayscale
                pass
            else:
                # Invalid frame format
                frame = None

    if frame is not None:
        print("Frame is not None")
        # Detect QR codes in the frame
        qr_codes = pyzbar.decode(frame)
        print(f"Detected {len(qr_codes)} QR codes")
        for qr_code in qr_codes:
            qr_data = qr_code.data.decode('utf-8')
            qr_type = qr_code.type
            string_to_print += f"QR Code detected: {qr_data} (Type: {qr_type})\n"
            # Save the QR code content to a file
            with open("/home/david/qr_codes.txt", "a") as file:
                file.write(f"Frame {user_data.get_count()}: {qr_data} (Type: {qr_type})\n")

    print(string_to_print)
    return Gst.PadProbeReturn.OK

# -----------------------------------------------------------------------------------------------
# Pipeline Setup and Execution
# -----------------------------------------------------------------------------------------------
class GStreamerDetectionAppWithSink(GStreamerDetectionApp):
    def __init__(self, callback, user_data):
        super().__init__(callback, user_data)

    def build_pipeline(self):
        pipeline = Gst.Pipeline()

        # Source element
        source = Gst.ElementFactory.make("v4l2src", "source")
        source.set_property("device", "/dev/video0")

        # Convert to a format suitable for xvimagesink
        videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")

        # Sink for display
        sink = Gst.ElementFactory.make("xvimagesink", "sink")

        if not pipeline or not source or not videoconvert or not sink:
            print("Failed to create pipeline elements")
            return None

        # Add elements to the pipeline
        pipeline.add(source)
        pipeline.add(videoconvert)
        pipeline.add(sink)

        # Link elements
        source.link(videoconvert)
        videoconvert.link(sink)

        return pipeline

if __name__ == "__main__":
    import sys

    # Initialize the callback user data class
    user_data = user_app_callback_class()

    # Create and run the application with xvimagesink
    app = GStreamerDetectionAppWithSink(app_callback, user_data)
    app.run()
