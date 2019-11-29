#!/usr/bin/env python3


import cv2 as cv


"""
Copyright (C) 2018 Denis Polygalov,
Laboratory for Circuit and Behavioral Physiology,
RIKEN Center for Brain Science, Saitama, Japan.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, a copy is available at
http://www.fsf.org/
"""


def moshow(s_winname, iterable_frame_set):
    """
    Display a sequence of frames (images) as a movie in the specified window.
    s_winname - string, the window name.
    iterable_frame_set - an iterable object (Python list in simplest case).
    Other types of iterable containers (such as tuple) may work too.
    Each member of iterable_frame_set is a movie frame (image) to show
    provided in a format acceptable by cv.imshow() function.
    Note that this function will lock execution and switch into interactive
    mode so you can switch between frames by pressing (n)ext and (p)revious
    keys. Pressing (q)uit will lead to return and continuing code execution.
    """

    i_frame_id = 0
    cv.imshow( s_winname, iterable_frame_set[i_frame_id] )

    while True:
        key = cv.waitKey(0)

        if key == ord('q'):
            break
        elif key == ord('n'):
            if i_frame_id >= len(iterable_frame_set) - 1:
                print("Last frame in the sequence reached. Do nothing.")
                continue
            else:
                i_frame_id += 1
                print("Frame number: %i key: %i" % (i_frame_id, key))
                cv.imshow( s_winname, iterable_frame_set[i_frame_id] )
                continue
        elif key == ord('p'):
            if i_frame_id == 0:
                print("First frame in the sequence reached. Do nothing.")
                continue
            else:
                i_frame_id -= 1
                print("Frame number: %i key: %i" % (i_frame_id, key))
                cv.imshow( s_winname, iterable_frame_set[i_frame_id] )
                continue
        else:
            print("Unknown key pressed. Usage: (p)revious frame, (n)ext frame, (q)uit.")
            continue
#

