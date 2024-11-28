from pyzbar import pyzbar
import cv2

# Define the file path
file_path = "/home/david/hailo-rpi5-examples/test.jpg"

# Load a test image with a QR code
print(f"Loading image from {file_path}")
img = cv2.imread(file_path)

if img is None:
    print("Failed to load image.")
else:
    print("Image loaded successfully.")
    print(f"Image shape: {img.shape}")

    # Convert the image to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print("Converted image to grayscale.")

    # Increase the contrast of the image
    gray = cv2.equalizeHist(gray)
    print("Increased image contrast.")

    # Threshold the image to white in black then invert it to black in white
    mask = cv2.inRange(img, (0, 0, 0), (200, 200, 200))
    thresholded = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    inverted = 255 - thresholded  # black-in-white
    print("Processed image for better QR code detection.")

    # Detect QR codes
    print("Detecting QR codes...")
    qr_codes = pyzbar.decode(inverted)
    print(f"Detected {len(qr_codes)} QR codes")

    for qr_code in qr_codes:
        qr_data = qr_code.data.decode('utf-8')
        qr_type = qr_code.type
        qr_rect = qr_code.rect
        print(f"QR Code data: {qr_data}")
        print(f"QR Code type: {qr_type}")
        print(f"QR Code position: {qr_rect}")

        # Draw a rectangle around the QR code
        x, y, w, h = qr_rect
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Save the image with detected QR codes
    output_path = "/home/david/hailo-rpi5-examples/test_with_qr.jpg"
    cv2.imwrite(output_path, img)
    print(f"Saved image with QR codes to {output_path}")