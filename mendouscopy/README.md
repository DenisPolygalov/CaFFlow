General concept behind the CaFFlow/mendouscopy framework is a well known idea of
representing video stream as a flow of video frames propagating over a directed graph.
This directory contain a set of Python classes each of which belong to one of 3 categories:

- __frame source__
- __frame processor__
- __frame sink__

A __frame source__ is a Python object binded to a single or multiple video file(s),
image(s), video camera(s) or network socket(s) and provides the next frame upon calling
its `read_next_frame()` method.
In the CaFFLow terminology frame source objects have zero *inputs* and a single *output*
and provide frames for the downstream graph.

A __frame processor__ is a Python object that has a single *input*, one or more *outputs*, and
processes each input frame upon calling its `process_frame()` method.

A __frame sink__ is a Python object that has a single *input* and zero *outputs*, and converts
the input frame into, for example, a file on a disk.

A __pipeline graph__ is a set of Python objects consisting of a single frame source,
zero or more frame processors and at least one frame sink.

In a user-side script all objects of the graph are instantiated, assembled into the pipeline
and executed by pushing frames from the source via processor(s) into sink(s).

The architecture above allows to accomplish a variety of tasks ranging from simple
video format conversion or animal's position detection to dF/F calcium traces extraction
in (well, almost) real time.
By using this user-side/framework-side concept, adapted pipelines can be
built for any set of experiments while keeping a common set of building blocks
consistent across labs, and, therefore, can contribute to reproducible
analysis while keeping flexibility.
In addition, video recordings can be of arbitrary duration without extensive
requirements for PC memory size.

Moreover, CaFFLow uses only field-proven and deterministic image processing
algorithms provided by the OpenCV library, straightforward for re-using in C++
or even re-implementation in FPGA, potentially yielding higher that real-time
performance and the possibility to be used in closed loop applications.
