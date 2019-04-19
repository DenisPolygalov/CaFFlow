#!/usr/bin/env python3


import os
import sys
import inspect
import numpy


def _get_var_name(var):
    """Gets the name of var. Does it from the out most frame inner-wards.
        :param var: variable to get name from.
        :return: string
    """
    for fi in reversed(inspect.stack()):
        l_names = [var_name for var_name, var_val in fi.frame.f_locals.items() if var_val is var]
        if len(l_names) > 0: return l_names[0]
    #
#

def DVAR(var, s_var_name=None, s_tag=None):
    """Describe an arbitrary Python variable.
        The description will be printed.
        :param var: variable to describe.
        :return: None
    """

    if not s_var_name: s_var_name = _get_var_name(var)
    if not s_tag: s_tag = "DVAR:"

    var_type = type(var)

    if var_type == numpy.ndarray:
        print("%s %s:\t%s\t%s\t%.5f\t%.5f" % (s_tag, s_var_name, var.shape, var.dtype, var.min(), var.max()))
    elif var_type == str:
        print("%s %s: %s len: %i" % (s_tag, s_var_name, var_type, len(var)))
    elif var_type == list:
        print("%s %s: %s len: %i" % (s_tag, s_var_name, var_type, len(var)))
    elif var_type == tuple:
        print("%s %s: %s len: %i" % (s_tag, s_var_name, var_type, len(var)))
    else:
        print("%s %s: %s" % (s_tag, s_var_name, var_type))
    #
#
