#!/usr/bin/env python3


import os
import sys
import time
import configparser


"""
Copyright (C) 2018, 2019 Denis Polygalov,
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


"""
*ABOUT THIS FILE*

The final product of this file is 2 videos of a mouse (LED light)
moving in a linear track playing side by side, one without processing,
and one with a white cross showing the position (pixel number) of the
mouse at each frame.

When the video is closed, an additional graph is made using the x and y
coordinates of the white cross seen in the video (the position of the
mouse per frame number).

This can be generalised with any video of a mouse moving with a clearly
visible LED light which can be tracked.
"""


class CSideBySidePlayer(object):
    def __init__(self, fig_size=(15,5), desired_fps=60):
        self.fig = plt.figure(figsize=fig_size)
        # https://matplotlib.org/api/_as_gen/matplotlib.figure.SubplotParams.html#matplotlib.figure.SubplotParams
        self.fig.subplots_adjust(wspace=0.01, hspace=0.01, left=0.01, right=0.99, bottom=0.01, top=0.99)

        self.f_timeout = 1.0/float(desired_fps)
        self.f_prev_frame_time = 0
        self.f_fps = 0

        self.axL = self.fig.add_subplot(1,2,1)
        plt.setp(self.axL, xticks=[], yticks=[])

        self.axR = self.fig.add_subplot(1,2,2)
        plt.setp(self.axR, xticks=[], yticks=[])

        self.imgL = None
        self.imgR = None

        self.fig.canvas.mpl_connect('key_press_event', self._cb_on_key_press_event)
        self.fig.canvas.mpl_connect('resize_event', self._cb_on_resize_event)

    def _cb_on_key_press_event(self, event):
        try:
            key_code = hex(ord(event.key))
        except TypeError:
            key_code = event.key
        print("key_press_event: key_code=%s key=%s" % (key_code, repr(event.key)) )
        sys.stdout.flush()

    def _cb_on_resize_event(self, event):
        fs_w, fs_h = float(event.width)/float(self.fig.dpi), float(event.height)/float(self.fig.dpi)
        print( "resize_event: %d %d figsize=(%.2f, %.2f)" % \
            (event.width, event.height, fs_w, fs_h) \
        )
        sys.stdout.flush()

    def set_Lframe_data(self, na_frame):
        """
        Sets the image to be shown on the left frame
        :param na_frame: image
        :return: no return, changes self.imgL
        """
        if self.imgL == None:
            self.imgL = self.axL.imshow(na_frame)
        else:
            self.imgL.set_data(na_frame)

    def set_Rframe_data(self, na_frame):
        """
        Sets the image to be shown on the right frame
        :param na_frame: image
        :return: no return, changes self.imgR
        """
        if self.imgR == None:
            self.imgR = self.axR.imshow(na_frame)
        else:
            self.imgR.set_data(na_frame)

    # def set_data(self, na_Lframe, na_Rframe):  # commented out because same matplotlib function name
    #     self.set_Lframe_data(na_Lframe)
    #     self.set_Rframe_data(na_Rframe)

    def drawait(self):
        self.fig.canvas.draw_idle()
        f_curr_frame_time = time.time()
        self.f_fps = 1.0/(f_curr_frame_time - self.f_prev_frame_time)
        self.f_prev_frame_time = f_curr_frame_time
        return plt.waitforbuttonpress(timeout=self.f_timeout)
    #
#


def main():
    # file in "examples" folder
    t_input_files = ("CW2003_H14_M57_S54_behavCam1_frame0to179.avi",) # notice the comma

    # load local configuration file
    oc_rec_cfg = configparser.ConfigParser()
    oc_rec_cfg.read("position_detection.ini")

    # create a multi-part movie object
    oc_movie = CMuPaMovieCV(t_input_files)
    print(oc_movie.df_info)

    # create a side by side movie player
    oc_player = CSideBySidePlayer()

    # create position detector
    oc_pos_det = CBehavPositionDetector(oc_rec_cfg["behavior"])

    i_frame_id = 0
    while(oc_movie.read_next_frame()):
        # makes a copy of the frame, which it will modify by drawing a cross on it
        na_frame_out = oc_movie.na_frame.copy()

        # prints detection success rate every 10 frames
        if i_frame_id % 10 == 0: print("Detection success rate: %.2f" % oc_pos_det.get_success_rate())

        # draw a cross at coordinates of LED directly onto na_frame_out
        t_cross_pos = oc_pos_det.detect_position(na_frame_out, b_verbose=True)
        oc_pos_det.draw_cross(t_cross_pos, na_frame_out)

        # set the frame data
        # left frame: original movie
        oc_player.set_Lframe_data(oc_movie.na_frame)
        # right frame: movie with detected LED
        oc_player.set_Rframe_data(na_frame_out)

        if oc_player.drawait(): break
        i_frame_id += 1

    # plot detected (X,Y) position values over frame number
    fig = plt.figure()
    ax = plt.subplot(1, 1, 1)
    ax.plot(np.array(oc_pos_det.l_position))
    plt.xlabel("Frame #")
    plt.ylabel("Animal's position (X,Y)")
    plt.legend(("X", "Y"))
    plt.show()
#


if __name__ == '__main__':
    s_base_dir, _ = os.path.split(os.getcwd())
    sys.path.append(s_base_dir)
    from mendouscopy.ioutils import enum_video_files
    from mendouscopy.mupamovie import CMuPaMovieCV
    from mendouscopy.behavior import CBehavPositionDetector
    import numpy as np
    import cv2 as cv
    import matplotlib.pyplot as plt
    main()
#


