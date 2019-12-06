[![DOI](https://zenodo.org/badge/181430093.svg)](https://zenodo.org/badge/latestdoi/181430093)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/d2e2151689ba496c807eea1f194e95ca)](https://www.codacy.com/manual/DenisPolygalov/CaFFlow?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=DenisPolygalov/CaFFlow&amp;utm_campaign=Badge_Grade)

# CaFFlow

CaFFlow is a Python framework for acquisition and analysis of single-,
two-photon calcium imaging and experimental subject's behavior data.
This project was originally intended to be used for acquisition of video data stream(s) generated
by [Miniscope](http://miniscope.org) miniature fluorescence microscope and subsequent
(offline and/or online) analysis of the acquired data.
Currently however, it can be used for processing of wider range of frame streams,
such as subject's behavior only, batch image/video editing etc.

## Limitations

As an open architecture system CaFFlow can be extended to fit various needs,
but it's current implementation have certain limitations. Such as:

-   ROI shape expected to be more or less circular. Detecting ring-shaped ROIs is not supported.
-   ROI expected to be a cell body. Detecting Ca++ transients in dendrites/spines etc. is not supported.
-   matching ROIs across recording sessions is not __yet__ supported.
-   post-processing of the _dF/F_ traces is not __yet__ implemented.

### Repository layout

CaFFlow consist of two main parts - framework-side and user-side scripts.
The framework-side part is a self-contained set of Python classes/functions representing
building blocks common for all recordings/experiments conducted in a Lab.
The user-side part is a set of Python scripts adapted for each experiment.
The framework is extended by developer(s), and never changed by user(s);
it has a strict set of external dependencies and guarantied backward compatibility.

-   __examples__ - examples of the user-side scripts. Each script demonstrate usage of particular set of features provided by the mendouscopy framework.
-   __mendouscopy__ - framework-side code related to analysis of the acquired calcium imaging and behavior data.
-   __mstools__ - framework-side GUI applications for video stream(s) preview and recording of video frames generated by [Miniscope](http://miniscope.org) hardware and/or common video cameras.
-   __unit_test__ - scripts for testing readiness of your Python environment to be used with the CaFFlow.

### Supported OS

-   Windows (primarily).
-   Any OS for which Python and all required packages available (optionally).

### Installation

#### Prerequisite software installation

_Feel free to skip this section if you already familiar with git/git-lfs/conda._

Make sure you have decent text editor (such as for example [Notepad++](https://notepad-plus-plus.org/) ) installed.
Download and install a command line interface based `git` client, such as
[Git for Windows](https://git-scm.com/download/win) if you do not already have it installed.
The `git` client software is offered in multiple packages. If you not familiar with git choose
the default package (32/64 bit installer type) which is usually offered automatically
from the link above. During installation make sure to check
[Git Large File Storage](https://git-lfs.github.com/) support checkbox.
If you had installed the Notepad++ earlier choose it as the default text
editor for the git client. All other options may be left default.

Activate the Git LFS extension.

Windows:

-   launch the `git` client application and run: `$ git lfs install`

MacOS:

-   if you use Homebrew, open terminal and run: `$ brew install git-lfs`
-   if you use MacPorts, open terminal and run: `$ port install git-lfs`

FreeBSD:

-   Open terminal and run: `$ pkg install git-lfs && git lfs install`

Change directory `(cd)` to the place where you plan to keep CaFFlow and clone this repository:

`$ git clone https://github.com/DenisPolygalov/CaFFlow.git`

Download and install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) if you don't have it installed already.
Note that if you plan to use GUI-based (PyQt) applications included into CaFFlow then it might be better to choose
32-bit version of the Miniconda due to a bug in 64-bit version preventing import of the PyQt.QtMultimedia module.

#### CaFFlow installation

Create and activate new 'Conda environment':

Windows:

Launch 'Anaconda Prompt' from Windows Start Menu and type:

`(base)> conda create -n cafflow`

`(base)> conda activate cafflow`

MacOS:

Launch the 'Terminal' application and type:

`$ source miniconda3/bin/activate`

`(base)$ conda create -n cafflow`

`(base)$ source activate cafflow`

Install necessary Python packages (the command syntax is common across Windows/MacOS/FreeBSD):

`(cafflow)> conda install opencv numpy pandas scipy scikit-image`

The set of packages above is sufficient to run analysis without visualization (on a headless server for example) and GUI applications.

For GUI-based applications - install PyQt package:

`(cafflow)> conda install pyqt`

For video encoding/decoding support the lossless video codec (FFV1)
must be installed and registered globally, at your operating system level
(i.e. as a COM DLL in the case of Windows). FFV1 video __encoding__ is supported by
OpenCV distributed via the `conda` installer. FFV1 video __decoding__ support
might be already available on your PC (installed for example by a third-party
application) so it is necessary to check it's presence.
In order to do so run the `examples/sXX_capture_video.py` script:

`(cafflow)> cd CaFFlow\examples`

`(cafflow)> python sXX_capture_video.py`

and examine it's output. The script will try to capture a chunk of video
stream from default video camera (must be connected in advance obviously),
encode the video by using FFV1 codec provided by OpenCV and write encoded video
into a file called _'captured_lossless_video.avi'_ located in the same directory.
If the file was created, have non-zero size and you can play it's content
by using common video-player software then you have FFV1 decoding support already installed.
If the file is broken or not created at all you can try to install 
[LAV Filters](https://github.com/Nevcairiel/LAVFilters) - 
Open-Source DirectShow Media Splitter and Decoders binary package
for Windows __**__
from [here](https://github.com/Nevcairiel/LAVFilters/releases)
, then restart your PC and repeat the test.

__**__ Installing FFV1 video encoding/decoding support for other OSes is outside of the scope of this project.

The next step is to test your Python environment:

`(cafflow)> cd CaFFlow`

`(cafflow)> python -m unittest discover unit_test`

While running command above you may see warning messages such as
"RuntimeWarning: numpy.ufunc size changed, may indicate binary incompatibility."
which is caused by numpy package and known to be harmless. Any error messages however
indicate problems with your Python environment.

Read Python scripts located in the __examples__ directory, execute them and adjust for your purpose.
Note that all example scripts are intended to be executed from __inside__ of the __examples__ directory.
