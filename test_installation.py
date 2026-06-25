"""
Quick test script to verify all dependencies are installed correctly
"""

print("=" * 60)
print("HoloBuild - Installation Test")
print("=" * 60)
print("\nTesting required libraries...\n")

# Test Python version
import sys
print(f"✓ Python version: {sys.version.split()[0]}")

# Test OpenCV
try:
    import cv2
    print(f"✓ OpenCV version: {cv2.__version__}")
except ImportError:
    print("✗ OpenCV not installed! Run: pip install opencv-python")
    sys.exit(1)

# Test MediaPipe
try:
    import mediapipe as mp
    print(f"✓ MediaPipe version: {mp.__version__}")
except ImportError:
    print("✗ MediaPipe not installed! Run: pip install mediapipe")
    sys.exit(1)

# Test NumPy
try:
    import numpy as np
    print(f"✓ NumPy version: {np.__version__}")
except ImportError:
    print("✗ NumPy not installed! Run: pip install numpy")
    sys.exit(1)

# Test PIL
try:
    from PIL import Image
    print(f"✓ Pillow installed")
except ImportError:
    print("✗ Pillow not installed! Run: pip install Pillow")
    sys.exit(1)

# Test camera access
print("\nTesting camera access...")
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print("✓ Camera accessible")
    ret, frame = cap.read()
    if ret:
        print(f"✓ Camera resolution: {frame.shape[1]}x{frame.shape[0]}")
    cap.release()
else:
    print("✗ Cannot access camera!")
    print("  - Check if camera is connected")
    print("  - Close other apps using the camera")

print("\n" + "=" * 60)
print("Installation test complete!")
print("If all items show ✓, you're ready to run the project!")
print("Run: python holobuild_ar.py")
print("=" * 60)
