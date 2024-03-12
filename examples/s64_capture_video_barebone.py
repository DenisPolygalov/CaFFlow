#!/usr/bin/env python3


import sys
import cv2 as cv


def main(i_cam_idx):
    cap = cv.VideoCapture(i_cam_idx)
    if not cap.isOpened():
        print("ERROR: Cannot open camera #", i_cam_idx)
        sys.exit()
    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        # if frame is read correctly ret is True
        if not ret:
            print("ERROR: Can't receive frame (stream end?). Exiting ...")
            break
        # Display the resulting frame
        cv.imshow('frame', frame)
        if cv.waitKey(1) == ord('q'):
            break
    cap.release()
#


if __name__ == '__main__':
    # Try to launch this script with main(0)
    # then main(1), main(2) etc and check how
    # video output correspond to the camera number.
    # USE 'q' KEY TO EXIT THIS SCRIPT.
    # Don't use 'X' close button to close
    # the video preview window.
    main(0)
    cv.destroyAllWindows()
#
