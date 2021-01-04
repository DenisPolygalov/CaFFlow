#!/usr/bin/env python3


import numpy as np


# Representation of an array as a set of sub-arrays in moving sliding window.
# See also: https://github.com/numpy/numpy/issues/7753
# https://numpy.org/doc/stable/reference/generated/numpy.lib.stride_tricks.as_strided.html


# Adapted from here: https://gist.github.com/nils-werner/9d321441006b112a4b116a8387c2280c
# Features of this implementation:
# - slides over one axis only
# - allows setting windowsize and stepsize
# - returns array with dimension n+1
# - sliding over several axes requires two calls (which come for free as there is no memory reordered)
# - has a superfluous copy parameter that can be removed and replaced by appending .copy() after the call

def sliding_window_1d(data, size, stepsize=1, axis=-1, copy=False):
    """
    Calculate a sliding window over a signal

    Parameters
    ----------
    data : numpy array
        The array to be slided over.
    size : int
        The sliding window size
    stepsize : int
        The sliding window step size. Defaults to 1.
    axis : int
        The axis to slide over. Defaults to the last axis.
    copy : bool
        Return strided array as copy to avoid side effects when manipulating the
        output array.


    Returns
    -------
    data : numpy array
        A matrix where row in last dimension consists of one instance
        of the sliding window.

    Notes
    -----

    - Be wary of setting `copy` to `False` as undesired side effects with the
      output values may occur.

    Examples
    --------

    >>> a = numpy.array([1, 2, 3, 4, 5])
    >>> sliding_window(a, size=3)
    array([[1, 2, 3],
           [2, 3, 4],
           [3, 4, 5]])
    >>> sliding_window(a, size=3, stepsize=2)
    array([[1, 2, 3],
           [3, 4, 5]])

    See Also
    --------
    pieces : Calculate number of pieces available by sliding

    """
    if axis >= data.ndim:
        raise ValueError(
            "Axis value out of range"
        )

    if stepsize < 1:
        raise ValueError(
            "Stepsize may not be zero or negative"
        )

    if size > data.shape[axis]:
        raise ValueError(
            "Sliding window size may not exceed size of selected axis"
        )

    shape = list(data.shape)
    shape[axis] = np.floor(data.shape[axis] / stepsize - size / stepsize + 1).astype(int)
    shape.append(size)

    strides = list(data.strides)
    strides[axis] *= stepsize
    strides.append(data.strides[axis])

    strided = np.lib.stride_tricks.as_strided(
        data, shape=shape, strides=strides
    )

    if copy:
        return strided.copy()
    else:
        return strided
#


# Adapted from  here: https://gist.github.com/teoliphant/96eb779a16bd038e374f2703da62f06d
# Features of this implementation:
# - slides over all axes simultaneously, window lengths are given as tuple parameter
# - assumes a stepsize one in all directions
# - returns array with dimension n*2
# - stepsize not equal to one requires slicing of output data (unsure if this implies copying data)
# - disabling sliding over axis[n] requires you set argument wshape[n] = 1 or wshape[n] = a.shape[n]

def array_for_sliding_window(x, wshape):
    """
    Build a sliding-window representation of x.

    The last dimension(s) of the output array contain the data of
    the specific window. The number of dimensions in the output is
    twice that of the input.

    Parameters
    ----------
    x : ndarray_like
       An array for which is desired a representation to which sliding-windows
       computations can be easily applied.
    wshape : int or tuple
       If an integer, then it is converted into a tuple of size given by the
       number of dimensions of x with every element set to that integer.
       If a tuple, then it should be the shape of the desired window-function

    Returns
    -------
    out : ndarray
        Return a zero-copy view of the data in x so that operations can be
        performed over the last dimensions of this new array and be equivalent
        to a sliding window calculation.  The shape of out is 2*x.ndim with
        the shape of the last nd dimensions equal to wshape while the shape
        of the first n dimensions is found by subtracting the window shape
        from the input shape and adding one in each dimension. This is
        the number of "complete" blocks of shape wshape in x.

    Raises
    ------
    ValueError
        If the size of wshape is not x.ndim (unless wshape is an integer).
        If one of the dimensions of wshape exceeds the input array.

    Examples
    --------
    >>> x = np.linspace(1,5,5)
    >>> x
    array([ 1.,  2.,  3.,  4.,  5.])

    >>> array_for_rolling_window(x, 3)
    array([[ 1.,  2.,  3.],
           [ 2.,  3.,  4.],
           [ 3.,  4.,  5.]])

    >>> x = np.arange(1,17).reshape(4,4)
    >>> x
    array([[ 1,  2,  3,  4],
           [ 5,  6,  7,  8],
           [ 9, 10, 11, 12],
           [13, 14, 15, 16]])

    >>> array_for_rolling_window(x, 3)
    array([[[[ 1,  2,  3],
             [ 5,  6,  7],
             [ 9, 10, 11]],

            [[ 2,  3,  4],
             [ 6,  7,  8],
             [10, 11, 12]]],

           [[[ 5,  6,  7],
             [ 9, 10, 11],
             [13, 14, 15]],

            [[ 6,  7,  8],
             [10, 11, 12],
             [14, 15, 16]]]])
    """
    x = np.asarray(x)

    try:
        nd = len(wshape)
    except TypeError:
        wshape = tuple(wshape for i in x.shape)
        nd = len(wshape)
    if nd != x.ndim:
        raise ValueError("wshape has length {0} instead of "
                         "x.ndim which is {1}".format(len(wshape), x.ndim))
    
    out_shape = tuple(xi - wi + 1 for xi, wi in zip(x.shape, wshape)) + wshape
    if not all(i > 0 for i in out_shape):
        raise ValueError("wshape is bigger than input array along at "
                         "least one dimension")

    out_strides = 2 * x.strides
    return np.lib.stride_tricks.as_strided(x, out_shape, out_strides)
#


# Adapted from here: https://gist.github.com/meowklaski/4bda7c86c6168f3557657d5fb0b5395a

def sliding_window_view(arr, window_shape, steps):
    """ Produce a view from a sliding, striding window over `arr`.
        The window is only placed in 'valid' positions - no overlapping
        over the boundary.

        Parameters
        ----------
        arr : numpy.ndarray, shape=(...,[x, (...), z])
            The array to slide the window over.

        window_shape : Sequence[int]
            The shape of the window to raster: [Wx, (...), Wz],
            determines the length of [x, (...), z]

        steps : Sequence[int]
            The step size used when applying the window
            along the [x, (...), z] directions: [Sx, (...), Sz]

        Returns
        -------
        view of `arr`, shape=([X, (...), Z], ..., [Wx, (...), Wz])
            Where X = (x - Wx) // Sx + 1

        Notes
        -----
        In general, given
          `out` = sliding_window_view(arr,
                                      window_shape=[Wx, (...), Wz],
                                      steps=[Sx, (...), Sz])

           out[ix, (...), iz] = arr[..., ix*Sx:ix*Sx+Wx,  (...), iz*Sz:iz*Sz+Wz]

         Examples
         --------
         >>> import numpy as np
         >>> x = np.arange(9).reshape(3,3)
         >>> x
         array([[0, 1, 2],
                [3, 4, 5],
                [6, 7, 8]])

         >>> y = sliding_window_view(x, window_shape=(2, 2), steps=(1, 1))
         >>> y
         array([[[[0, 1],
                  [3, 4]],

                 [[1, 2],
                  [4, 5]]],


                [[[3, 4],
                  [6, 7]],

                 [[4, 5],
                  [7, 8]]]])
        >>> np.shares_memory(x, y)
         True

        # Performing a neural net style 2D conv (correlation)
        # placing a 4x4 filter with stride-1
        >>> data = np.random.rand(10, 3, 16, 16)  # (N, C, H, W)
        >>> filters = np.random.rand(5, 3, 4, 4)  # (F, C, Hf, Wf)
        >>> windowed_data = sliding_window_view(data,
        ...                                     window_shape=(4, 4),
        ...                                     steps=(1, 1))

        >>> conv_out = np.tensordot(filters,
        ...                         windowed_data,
        ...                         axes=[[1,2,3], [3,4,5]])

        # (F, H', W', N) -> (N, F, H', W')
        >>> conv_out = conv_out.transpose([3,0,1,2])
         """

    in_shape = np.array(arr.shape[-len(steps):])  # [x, (...), z]
    window_shape = np.array(window_shape)  # [Wx, (...), Wz]
    steps = np.array(steps)  # [Sx, (...), Sz]
    nbytes = arr.strides[-1]  # size (bytes) of an element in `arr`

    # number of per-byte steps to take to fill window
    window_strides = tuple(np.cumprod(arr.shape[:0:-1])[::-1]) + (1,)
    # number of per-byte steps to take to place window
    step_strides = tuple(window_strides[-len(steps):] * steps)
    # number of bytes to step to populate sliding window view
    strides = tuple(int(i) * nbytes for i in step_strides + window_strides)

    outshape = tuple((in_shape - window_shape) // steps + 1)
    # outshape: ([X, (...), Z], ..., [Wx, (...), Wz])
    outshape = outshape + arr.shape[:-len(steps)] + tuple(window_shape)
    return np.lib.stride_tricks.as_strided(arr, shape=outshape, strides=strides, writeable=False)
#

