#!/usr/bin/env python3


import io
import os
import zipfile as zf
import numpy as np
import pandas
import cv2 as cv
from skimage.external import tifffile


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

class CMuPaMovie(object):
    """
    Base class represents a MultiPart Movie.
    The MultiPart Movie constructed from a tuple of video file names.
    The file names in the tuple must be in correct temporal order.
    """
    def __init__(self, t_file_names):
        self.t_file_names = t_file_names
        self.df_info = pandas.DataFrame( \
            index = np.arange(len(self.t_file_names)), \
            columns = ['file_name', 'start', 'end', 'duration', 'frames', 'frame_rate', 'width', 'height', 'format'] \
        )
        self.t_vid_files   = None
        self.t_vid_streams = None
        self.na_ends  = None # [1000, 2000, 3000, 4000, 4963], read only!
        self.na_frame = None # the frame (as Numpy array)
        self.i_curr_file_idx  = 0     # read only!
        self.i_curr_rel_frame_num = 0 # read only!
        self.i_curr_abs_frame_num = 0 # read only!
        self.i_next_abs_frame_num = 0 # read only!
        # For convenience only. Calculated from self.df_info
        # Note that instead of self.dtype we use self.na_frame.dtype
        self.shape = None
        self.t_frame_hw = None
        self.i_nframes = None
    #
    def abs2rel(self, i_abs):
        # if requested i_abs is before the start - return (first_file, first_frame)
        if i_abs < 0: return (0,0)
        # if requested i_abs is after the end - return (last_file, last_frame)
        if i_abs >= self.na_ends[-1]: return ( self.na_ends.shape[0] - 1, self.na_ends[-1] - 1 )
        # find an index of the first edge bigger than requested i_abs
        i_1st_bigger_edge = np.argmax(self.na_ends > i_abs)
        # if requested i_abs is within the first bin - return it as is
        if i_1st_bigger_edge == 0:
            return (0, i_abs)
        else:
            return (i_1st_bigger_edge, i_abs - self.na_ends[i_1st_bigger_edge - 1])
        #
    #
    def rel2abs(self, file_idx, frame_num):
        if file_idx < 0: return 0
        if file_idx == 0: return frame_num
        if file_idx >= self.na_ends.shape[0]: return self.na_ends[-1] - 1
        if frame_num >= self.na_ends[file_idx]:
            raise ValueError("Wrong input: %s" % repr((file_idx, frame_num)) )
        #
        # i_abs, absolute frame number 0 ~ self.na_ends[-1]
        return self.na_ends[file_idx - 1] + frame_num
    #
#

class CMuPaMovieCV(CMuPaMovie):
    """
    Class represents a MultiPart Movie (OpenCV-based backend).
    The MultiPart Movie constructed from a tuple of video file names.
    The file names in the tuple must be in correct temporal order.
    For details refer to documentation for the base class CMuPaMovie()
    """
    def __init__(self, t_file_names, b_verbose=False):
        super().__init__(t_file_names)

        # to be turned into tuples at the end of this constructor
        l_vid_files = []
        l_vid_streams = []

        for idx in range(len(self.t_file_names)):
            self.df_info.loc[idx, 'file_name'] = self.t_file_names[idx]

            i_read_try_cnt = 0
            hCap = cv.VideoCapture(self.t_file_names[idx])
            while not hCap.isOpened():
                hCap = cv.VideoCapture(self.t_file_names[idx])
                cv.waitKey(1000)
                # print("WARNING: waiting for the cv.VideoCapture()...")
                i_read_try_cnt += 1
                if i_read_try_cnt >= 10:
                    raise ValueError("Unable to read frame from: %s" % self.t_file_names[idx])

            self.df_info.loc[idx, 'duration'] = hCap.get(cv.CAP_PROP_FRAME_COUNT)
            self.df_info.loc[idx, 'frames']   = int(hCap.get(cv.CAP_PROP_FRAME_COUNT))
            self.df_info.loc[idx, 'frame_rate'] = float(hCap.get(cv.CAP_PROP_FPS))
            self.df_info.loc[idx, 'width']  = int(hCap.get(cv.CAP_PROP_FRAME_WIDTH))
            self.df_info.loc[idx, 'height'] = int(hCap.get(cv.CAP_PROP_FRAME_HEIGHT))
            # self.df_info.loc[idx, 'format'] = hCap.get(cv.CAP_PROP_ ... )

            l_vid_files.append( hCap )
            l_vid_streams.append( hCap )

        # check if all video files have the same frame width and height
        if self.df_info['width'].sum() != \
           self.df_info['width'][0] * len(self.df_info['width']):
            raise ValueError("Frame width is not consistent across input video files")
        if self.df_info['height'].sum() != \
           self.df_info['height'][0] * len(self.df_info['height']):
            raise ValueError("Frame height is not consistent across input video files")

        self.df_info['start'] = self.df_info['duration'].cumsum() - self.df_info['duration']
        self.df_info['end']   = self.df_info['duration'].cumsum()
        # self.df_info = self.df_info.set_index(['file_name'], append = True)

        # freeze lists into tuples
        self.t_vid_files = tuple(l_vid_files)
        self.t_vid_streams = tuple(l_vid_streams)

        # [1000, 2000, 3000, 4000, 4963], read only!
        self.na_ends = np.array(self.df_info['end'], dtype=np.int32)

        self.shape = (int(self.df_info['height'][0]), int(self.df_info['width'][0]), int(self.df_info['duration'].cumsum().sum()))
        self.t_frame_hw = (int(self.df_info['height'][0]), int(self.df_info['width'][0]))
        self.i_nframes = int(self.df_info['duration'].cumsum().sum())

        if b_verbose:
            print(self.df_info)

    def _seek_rel(self, file_idx, frame_num):
        b_ret = False
        if file_idx  >= len(self.t_file_names): return b_ret
        if frame_num >= self.df_info.at[file_idx, 'frames']: return b_ret
        return self.t_vid_streams[file_idx].set(cv.CAP_PROP_POS_FRAMES, frame_num)

    def _read_frame(self, file_idx, frame_num, b_do_seek=True):
        b_ret = False
        # set position to read the requested frame from requested video file
        if b_do_seek:
            b_ret = self._seek_rel(file_idx, frame_num)
            if not b_ret: return b_ret

        # try to read the frame
        while True:
            b_ret, self.na_frame = self.t_vid_streams[file_idx].read()
            if b_ret:
                self.i_curr_file_idx = file_idx
                self.i_curr_rel_frame_num = frame_num
                self.i_curr_abs_frame_num = self.rel2abs(self.i_curr_file_idx, self.i_curr_rel_frame_num)
                return b_ret
            else:
                # print("WARNING: waiting for the cv.read()...")
                # cv.waitKey(1000)
                b_ret = self._seek_rel(file_idx, frame_num)
                if not b_ret: return b_ret

        return b_ret

    def seek(self, abs_frame_num):
        b_ret = False
        rel_file_idx, rel_frame_num = self.abs2rel(abs_frame_num)
        if rel_file_idx  >= len(self.t_file_names): return b_ret
        if rel_frame_num >= self.df_info.at[rel_file_idx, 'frames']: return b_ret
        return self.t_vid_streams[rel_file_idx].set(cv.CAP_PROP_POS_FRAMES, rel_frame_num)

    def read_frame(self, abs_frame_num):
        """
        Read particular frame number into self.na_frame
        This method is slow because seek() is called every time.
        """
        rel_file_idx, rel_frame_num = self.abs2rel(abs_frame_num)
        return self._read_frame(rel_file_idx, rel_frame_num, b_do_seek=True)

    def read_next_frame(self):
        """
        Read next frame at the current position.
        This method is fast.
        You can set current position once by using seek(frame_number).
        """
        rel_file_idx, rel_frame_num = self.abs2rel(self.i_next_abs_frame_num)
        b_ret = self._read_frame(rel_file_idx, rel_frame_num, b_do_seek=False)
        if b_ret == True:
            self.i_next_abs_frame_num += 1
            if self.i_next_abs_frame_num > self.na_ends[-1]:
                b_ret = False
        return b_ret

    def get_frame_stat(self):
        return "curr_abs_frame_num: %d\t curr_file_idx: %d\t curr_rel_frame_num: %d" % ( \
            self.i_curr_abs_frame_num, \
            self.i_curr_file_idx, \
            self.i_curr_rel_frame_num \
        )
    #
#


class CMuPaMovieTiff(CMuPaMovie):
    """
    Class represents a MultiPart Movie (tifffile-based backend).
    The MultiPart Movie constructed from a tuple of multi-page tiff file names.
    The file names in the tuple must be in correct temporal order.
    For details refer to documentation for the base class CMuPaMovie()
    """
    def __init__(self, t_file_names, b_verbose=False):
        super().__init__(t_file_names)

        # to be turned into tuples at the end of this constructor
        l_vid_files = []
        l_vid_streams = []

        for idx in range(len(self.t_file_names)):
            self.df_info.loc[idx, 'file_name'] = self.t_file_names[idx]
            oc_tiff_record = tifffile.TiffFile(self.t_file_names[idx])
            if hasattr(oc_tiff_record, 'pages'):
                oc_tiff = oc_tiff_record.pages
            else:
                oc_tiff = oc_tiff_record['pages']
            oc_tmp_frame = oc_tiff[0]
            # TODO we can use this later: print(oc_tmp_frame.tags)

            self.df_info.loc[idx, 'duration'] = len(oc_tiff)
            self.df_info.loc[idx, 'frames']   = len(oc_tiff)
            # frame rate is not available in TIFFs: self.df_info.loc[idx, 'frame_rate'] =
            self.df_info.loc[idx, 'width']  = int(oc_tmp_frame.shape[1]) # this is correct
            self.df_info.loc[idx, 'height'] = int(oc_tmp_frame.shape[0])
            self.df_info.loc[idx, 'format'] = oc_tmp_frame.dtype

            l_vid_files.append( oc_tiff )
            l_vid_streams.append( oc_tiff )

        # check if all video files have the same frame width and height
        if self.df_info['width'].sum() != \
           self.df_info['width'][0] * len(self.df_info['width']):
            raise ValueError("Frame width is not consistent across input video files")
        if self.df_info['height'].sum() != \
           self.df_info['height'][0] * len(self.df_info['height']):
            raise ValueError("Frame height is not consistent across input video files")

        self.df_info['start'] = self.df_info['duration'].cumsum() - self.df_info['duration']
        self.df_info['end']   = self.df_info['duration'].cumsum()
        # self.df_info = self.df_info.set_index(['file_name'], append = True)

        # freeze lists into tuples
        self.t_vid_files = tuple(l_vid_files)
        self.t_vid_streams = tuple(l_vid_streams)

        # [1000, 2000, 3000, 4000, 4963], read only!
        self.na_ends = np.array(self.df_info['end'], dtype=np.int32)

        self.shape = (int(self.df_info['height'][0]), int(self.df_info['width'][0]), int(self.df_info['duration'].cumsum().sum()))
        self.t_frame_hw = (int(self.df_info['height'][0]), int(self.df_info['width'][0]))
        self.i_nframes = int(self.df_info['duration'].cumsum().sum())

        if b_verbose:
            print(self.df_info)

    def _read_frame(self, file_idx, frame_num):
        b_ret = False
        # try to read the frame
        self.na_frame = self.t_vid_files[file_idx][frame_num].asarray()
        self.i_curr_file_idx = file_idx
        self.i_curr_rel_frame_num = frame_num
        self.i_curr_abs_frame_num = self.rel2abs(self.i_curr_file_idx, self.i_curr_rel_frame_num)
        b_ret = True
        return b_ret

    def seek(self, abs_frame_num):
        raise NotImplementedError("To be implemented")

    def read_frame(self, abs_frame_num):
        """
        Read particular frame nubmer into self.na_frame
        This method is slow because seek() is called every time.
        """
        rel_file_idx, rel_frame_num = self.abs2rel(abs_frame_num)
        b_ret = self._read_frame(rel_file_idx, rel_frame_num)
        if b_ret is True:
            self.i_next_abs_frame_num = abs_frame_num + 1
            if self.i_next_abs_frame_num > self.na_ends[-1]:
                b_ret = False
        return b_ret

    def read_next_frame(self):
        """
        Read next frame at the current position.
        This method is fast.
        You can set current position once by using seek(frame_number).
        """
        rel_file_idx, rel_frame_num = self.abs2rel(self.i_next_abs_frame_num)
        b_ret = self._read_frame(rel_file_idx, rel_frame_num)
        if b_ret is True:
            self.i_next_abs_frame_num += 1
            if self.i_next_abs_frame_num > self.na_ends[-1]:
                b_ret = False
        return b_ret

    def get_frame_stat(self):
        return "curr_abs_frame_num: %d\t curr_file_idx: %d\t curr_rel_frame_num: %d" % ( \
            self.i_curr_abs_frame_num, \
            self.i_curr_file_idx, \
            self.i_curr_rel_frame_num \
        )
    #
#


class CMuPaMovieZF(CMuPaMovie):
    def __init__(self, t_file_names, b_verbose=False):
        super().__init__(t_file_names)
        self.d_name_lists = {}
        self.oc_bstream = io.BytesIO()

        # to be turned into tuples at the end of this constructor
        l_vid_files = []
        l_vid_streams = []

        for idx in range(len(self.t_file_names)):
            self.df_info.loc[idx, 'file_name'] = self.t_file_names[idx]
            hZipFile = zf.ZipFile(self.t_file_names[idx], mode='r')
            self.d_name_lists[self.t_file_names[idx]] = hZipFile.namelist().copy()

            self.oc_bstream.seek(0)
            self.oc_bstream.write(hZipFile.read(self.d_name_lists[self.t_file_names[idx]][0]))
            self.oc_bstream.seek(0)
            oc_tmp_frame = tifffile.imread(self.oc_bstream)

            self.df_info.loc[idx, 'duration'] = len(self.d_name_lists[self.t_file_names[idx]])
            self.df_info.loc[idx, 'frames']   = len(self.d_name_lists[self.t_file_names[idx]])
            # frame rate is not available in TIFFs: self.df_info.loc[idx, 'frame_rate'] =
            self.df_info.loc[idx, 'width']  = int(oc_tmp_frame.shape[1]) # this is correct
            self.df_info.loc[idx, 'height'] = int(oc_tmp_frame.shape[0])
            self.df_info.loc[idx, 'format'] = oc_tmp_frame.dtype

            l_vid_files.append( hZipFile )
            l_vid_streams.append( hZipFile )

        # check if all video files have the same frame width and height
        if self.df_info['width'].sum() != \
           self.df_info['width'][0] * len(self.df_info['width']):
            raise ValueError("Frame width is not consistent across input video files")
        if self.df_info['height'].sum() != \
           self.df_info['height'][0] * len(self.df_info['height']):
            raise ValueError("Frame height is not consistent across input video files")

        self.df_info['start'] = self.df_info['duration'].cumsum() - self.df_info['duration']
        self.df_info['end']   = self.df_info['duration'].cumsum()
        # self.df_info = self.df_info.set_index(['file_name'], append = True)

        # freeze lists into tuples
        self.t_vid_files = tuple(l_vid_files)
        self.t_vid_streams = tuple(l_vid_streams)

        # [1000, 2000, 3000, 4000, 4963], read only!
        self.na_ends = np.array(self.df_info['end'], dtype=np.int32)

        self.shape = (int(self.df_info['height'][0]), int(self.df_info['width'][0]), int(self.df_info['duration'].cumsum().sum()))
        self.t_frame_hw = (int(self.df_info['height'][0]), int(self.df_info['width'][0]))
        self.i_nframes = int(self.df_info['duration'].cumsum().sum())

        if b_verbose:
            print(self.df_info)

    def _read_frame(self, file_idx, frame_num):
        b_ret = False

        # try to read the frame
        self.oc_bstream.seek(0)
        self.oc_bstream.write(
            self.t_vid_streams[file_idx].read(
                self.d_name_lists[self.t_file_names[file_idx]][frame_num]
            )
        )
        self.oc_bstream.seek(0)
        self.na_frame = tifffile.imread(self.oc_bstream)

        self.i_curr_file_idx = file_idx
        self.i_curr_rel_frame_num = frame_num
        self.i_curr_abs_frame_num = self.rel2abs(self.i_curr_file_idx, self.i_curr_rel_frame_num)
        b_ret = True
        return b_ret

    def seek(self, abs_frame_num):
        raise NotImplementedError("To be implemented")

    def read_frame(self, abs_frame_num):
        """
        Read particular frame nubmer into self.na_frame
        This method is slow because seek() is called every time.
        """
        rel_file_idx, rel_frame_num = self.abs2rel(abs_frame_num)
        b_ret = self._read_frame(rel_file_idx, rel_frame_num)
        if b_ret == True:
            self.i_next_abs_frame_num = abs_frame_num + 1
            if self.i_next_abs_frame_num > self.na_ends[-1]:
                b_ret = False
        return b_ret

    def read_next_frame(self):
        """
        Read next frame at the current position.
        This method is fast.
        You can set current position once by using seek(frame_number).
        """
        rel_file_idx, rel_frame_num = self.abs2rel(self.i_next_abs_frame_num)
        b_ret = self._read_frame(rel_file_idx, rel_frame_num)
        if b_ret == True:
            self.i_next_abs_frame_num += 1
            if self.i_next_abs_frame_num > self.na_ends[-1]:
                b_ret = False
        return b_ret

    def get_frame_stat(self):
        return "curr_abs_frame_num: %d\t curr_file_idx: %d\t curr_rel_frame_num: %d" % ( \
            self.i_curr_abs_frame_num, \
            self.i_curr_file_idx, \
            self.i_curr_rel_frame_num \
        )
    #
#


class CSingleTiffWriter(object):
    def __init__(self, s_fname_out, b_delete_existing=False):
        if os.path.isfile(s_fname_out) and not b_delete_existing:
            raise ValueError("Requested output file already exist. Die in order to prevent data loss.")
        self.s_fname_out = s_fname_out
        self.oc_tiff = tifffile.TiffWriter(self.s_fname_out, bigtiff=True, software="mendouscopy")
    def write_next_frame(self, na_in):
        if na_in.dtype == np.uint16:
            self.oc_tiff.save(na_in, compress=6)
        else:
            self.oc_tiff.save(cv.normalize(na_in, None, alpha=0, beta=(2**16-1), norm_type=cv.NORM_MINMAX, dtype=cv.CV_16U), compress=6)
        return True
    def close(self):
        self.oc_tiff.close()
    def write_last_frame(self, na_in):
        self.write_next_frame(na_in)
        self.close()
    #
#
