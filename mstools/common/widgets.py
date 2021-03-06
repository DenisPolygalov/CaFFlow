#!/usr/bin/env python3


from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


"""
Copyright (C) 2019 Denis Polygalov,
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


class CLabeledComboBox(QtWidgets.QWidget):
    def __init__(self, s_label_text, l_cbox_items=None, *args, **kwargs):
        super(CLabeledComboBox, self).__init__(*args, **kwargs)

        self.cbox = QtWidgets.QComboBox()
        if l_cbox_items is not None: self.cbox.addItems(l_cbox_items)

        self.lbl = QtWidgets.QLabel()
        self.lbl.setText(s_label_text)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.lbl)
        layout.addWidget(self.cbox)

        self.setLayout(layout)
    #
#


class CLabeledPushButton(QtWidgets.QWidget):
    def __init__(self, s_label_text, s_button_text, *args, **kwargs):
        super(CLabeledPushButton, self).__init__(*args, **kwargs)

        self.btn = QtWidgets.QPushButton(s_button_text)
        self.lbl = QtWidgets.QLabel()
        self.lbl.setText(s_label_text)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.lbl)
        layout.addWidget(self.btn)

        self.setLayout(layout)
    #
#


class CLabeledSpinSlider(QtWidgets.QWidget):
    def __init__(self, s_label_text, t_range, i_step, spin_min_w=45, cb_action=None, *args, **kwargs):
        super(CLabeledSpinSlider, self).__init__(*args, **kwargs)
        self.callback_action = cb_action

        self.spin = QtWidgets.QSpinBox()
        self.spin.setKeyboardTracking(False)
        self.spin.setMinimumWidth(spin_min_w) # just enough for showing 3 digits
        self.spin.setRange(t_range[0], t_range[1])
        self.spin.setSingleStep(i_step)
        self.spin.valueChanged.connect(self.__cb_spin_value_changed)

        self.lbl = QtWidgets.QLabel()
        self.lbl.setText(s_label_text)

        self.slider = QtWidgets.QSlider(Qt.Horizontal)
        self.slider.setMinimum(t_range[0])
        self.slider.setMaximum(t_range[1])
        self.slider.setSingleStep(i_step)
        self.slider.valueChanged.connect(self.__cb_slider_value_changed)
        self.slider.sliderReleased.connect(self.__cb_slider_released)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.lbl, 0, 0, 1, 1)
        layout.addWidget(self.spin, 0, 1, 1, 1)
        layout.addWidget(self.slider, 1, 0, 1, 2)

        self.setLayout(layout)

    def __cb_slider_released(self):
        if self.callback_action is not None:
            self.callback_action(self.slider.sliderPosition())

    def __cb_slider_value_changed(self, i_pos):
        self.spin.setValue(i_pos)

    def __cb_spin_value_changed(self, i_pos):
        self.slider.setSliderPosition(i_pos)
        if not self.slider.isSliderDown() and self.callback_action is not None:
            self.callback_action(i_pos)
    #
#


class CTableItemDelegate(QtWidgets.QItemDelegate):
    def createEditor(self, parent, option, index):
        comboBox = QtWidgets.QComboBox(parent)
        comboBox.addItem("disabled")
        comboBox.addItem("ENABLED")
        comboBox.activated.connect(self.emitCommitData)
        return comboBox

    def setEditorData(self, editor, index):
        comboBox = editor
        if not comboBox:
            return

        pos = comboBox.findText(index.model().data(index), Qt.MatchExactly)
        comboBox.setCurrentIndex(pos)

    def setModelData(self, editor, model, index):
        comboBox = editor
        if not comboBox:
            return

        model.setData(index, comboBox.currentText())

    def emitCommitData(self):
        self.commitData.emit(self.sender())
#
