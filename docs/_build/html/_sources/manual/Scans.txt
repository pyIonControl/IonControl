.. include:: inlineImages.include

.. _Scans:

Scans
=====

The scan controls allow performing a one dimensional scan of any parameter, with a specified method of evaluating the returning data, and analyzing the resulting curve. This shows the sequence of a scan:

.. figure:: ../images/OneDimensionalScan.png
   :scale: 100 %

An analysis is able to push fit results to global variables. Since pulse program parameters can depend on global variables, this can determine the parameter values used for the next scan.

The scan is controlled and examined by the following docks:

Scan Control
------------

.. figure:: ../images/ScanControl.png
   :scale: 50 %

The scan control determines how the scan runs. The controls are:

- scan settings menu
   Allows you to save and load different scan configurations. Works the same as the :ref:`PulseProgram` settings menu.

- scan mode
   Allows you to choose from:

   - Parameter scan
      one dimensional scan of the specified parameter

   - Step in place
      Repeatedly run the same experiment without changing anything

   - Gate Sequence Scan
      See :ref:`GateSequences`

   - Free Running
      Freerunning is a mode where the pulse program can trigger the end of a point and the beginning of the next point. No data is provided via the pipe to the pulse program at that point boundary.
      The pulse program can insert a point separator as follows:

      .. code-block:: Python

         write_pipe( nextPointMarker )  # where nextPointMarker = 0xfffc000000000000
         write_pipe( counter )

- scan target
   (Parameter scan only) Choose what type of parameter to scan:

   - Internal
      A parameter controlled by the FPGA and defined in the pulse program

   - External
      An external instrument, see :ref:`ExternalParameters`.

   - Voltage
      A voltage control gain.

   - AWG
      An AWG parameter.

- scan parameter
   What parameter to scan

- scan table
   Defines what points to scan. The fields are linked, meaning you can type value into center/span, or into start/stop, and the other will change. Steps and stepsize are similarly linked. The |add| and |remove| symbols next to the scan parameter drop down allows you to run a scan with multiple segments. The fields can also be set to an expression involving a global variable. This can be useful to create calibrations that stay centered. For example, if you have a global named 'resonanceGlobal', and you regularly scan a parameter 'myFreq' to determine the value of 'resonanceGlobal', you can set the center of that scan to be equal to 'resonanceGlobal'. The scan will then always be centered on the last known value. You can also create an analysis to automatically push the results of that scan to resonanceGlobal, see below.

- Max Points (step-in-place only)
   For step-in-place, The max points field determines the maximum number of points to display at one time while running step in place. Set it to zero to display all points.

   .. note:: This does not determine when to stop the scan. Step in place runs until explicitly stopped. If you want to do step in place for a fixed number of points, create a "dummy" parameter in the pulse program that does not control anything, and scan the dummy parameter for the desired number of points.

- x-axis
   Defines how to display and save the scan points.

   - unit
      The unit to use for the x-axis (e.g. us, ms, s). If this is blank or inconsistent with the scan, the program will just pick something.

   - expression
      Allows a transformation of the x-axis. For example, if you type in `x-5 MHz`, the x-axis will have a 5 MHz offset relative to the scan parameter value.

      .. tip:: Rather than using this functionality, you are often better off using pulse program parameters to accomplish the same thing. For example, if you have a parameter "myFreq," and you wish to scan it from 40 MHz to 50 MHz, but you want to display it from -5 MHz to +5 MHz, create a parameter "offset = 45 MHz" and a parameter "shiftedFreq" and set "myFreq = offset + shiftedFreq." Then scan "shiftedFreq" from -5 MHz to 5 MHz. This will have the same effect as using an x-axis expression, but it will be much more transparent what's going on.

- direction
   Define the order in which the scan proceeds.

- Load PP
   If this is checked, the pulse program configuration specified in the drop down box will be loaded whenever this scan starts.

- Filename
   If this is checked, scan data will automatically be saved to using the specified filename template. By default the filename is the same as the settings name. You can change this by right clicking anywhere and unchecking "Use default filename."

   .. tip:: Just leave this checked and save everything. You will very rarely regret it.

- Histogram file
   If this is checked, all histograms will be saved to the filename specified.

- Raw data
   If this is checked, all raw, unevaluated data transmitted by the FPGA will be saved. For most simple experiments, this will contain no new information that is not already in the standard data file.

- Gate Sequences
   Click to open :ref:`GateSequences` control.

Evaluation Control
------------------

.. figure:: ../images/EvaluationControl.png
   :scale: 100 %

The evaluation control determines what traces are generated by the scan. The controls are:

- evaluation settings menu
   As before, the evaluation settings can be saved/loaded via this menu.

- Histogram bins
   How many histogram bins to display on histograms.

- Integrate checkbox
   If this is checked, histograms will be integrated throughout the scan as one histogram. i.e., each scan point's histogram will simply add to the existing histogram.

- Evaluations table
   This is where all evaluations are specified. Each evaluation will generate one trace. To add (remove) an evaluation, click |add| (|remove|). The columns are:

   - Type
      The type of evaluation -- counter or result. "Counter" refers to the counter table in the pulse program counters dock. "Result" refers to a result sent back by the pulse program using the write_result command.

   - ID/channel
      Specifies which counter channel to plot. The ID is the same ID specified in the pulse program counters dock. If the type is a counter, the channel will be a drop down with the available counter channels. If the type is a result, it will be a spin box, as result can be any 8 bit number (0-255).

   - Evaluation
      Specifies how to evaluate the counts on the specified channel. A number of evaluations are available. To add new evaluations, see :ref:`ExtendingTheCode`. Each evaluation has a set of configuration options. When you click a line in the evaluation table, the bottom of the evaluation control will show a set of configuration options for that specific evaluation.

   - Name
      Assign a name to the evaluation. This name will appear in the list of traces, and is used in the analysis control.

   - Hist
      Whether to display a histogram for the specified channel.

   - Plot
      What plot window to use for the trace.

   - Abszisse
      What to use for x-axis in plot.

      - x: scan value
      - index: enumerates the points as taken
      - time: software timestamp (time the computer added the point to the trace)
      - fist: hardware timetick of first data in this point (in seconds since epoch)
      - last: hardware timetick of last data in this point (in seconds since epoch)

      These alternative x axes are useful if a scan is being done with randomized points while simultaneously a PI lock is being run during the scan. The evaluation looking at the scan itself will need to be plotted a function of the scan value, but the evaluation monitoring the PI lock is more informative if it plots as a function of time.

Analysis Control
----------------

.. figure:: ../images/AnalysisControl.png
   :scale: 100 %

The analysis control determines what fits (if any) are run at the conclusion of the scan. The controls are:

- Settings menu
   As above.

- Analysis table
   Specify all fits to perform. Columns:

   - Enable
      If checked, this fit will run when the scan ends.

   - Name
      A name for the analysis.

   - Evaluation
      What evaluation from the evaluation control to perform the fit on.

   - Fit function
      What fit function to use. To add new fit functions, see :ref:`ExtendingTheCode`.

   When an analysis in the table is clicked, the bottom of the analysis control window populates. The following is shown:

   - fit function
      The equation for the fit function selected.

   - fit variables table
      The fit variables table has the following columns:

      - Fit
         Whether or not the specified variable should be fitted. If it is unchecked, the value specified in "start" is used.

      - Var
         The name of the fit variable

      - Start
         The best guess value to use to start the fitting, or the value to use if the variable is not to be fitted.

         .. note:: If "Use Smart Start Values" is checked, these values are overridden for all fitted variables.

      - min/max
         bounds for the specified parameter

         .. note:: Avoid using min and max for fit variables unless your fits aren't working, as it changes the fit library used and coerces the fit.

      - Fit
         The best fit value

   - fit information table
      Information about the fit

- Push table
   This enables pushing results of the fit to global variables. To add (remove) a global push, click |add| (|remove|) in the lower right hand corner. Columns:

   - Push
      If this is clicked, push will be attempted after analysis is performed.

   - Destination
      What space to push the results to (e.g. Globals).

   - Variable
      What global variable to push the results to.

   - Definition
      An expression relating a fit variable to the global. This can be any expression involving the fit variable or globals.

      .. note:: Fit variables are unfortunately unitless. This means that if you have a fit value of "C=42" but the global should be "42 MHz," definition must be set to "C * (1.000 MHz)."

   - Value
      The resultant value

   - Min/Max Accept
      The range of acceptable resultant values. If the result is outside of this range, the push will not occur. Putting a bound here is important to avoid analyses from bad fits wreaking havoc. You can also use a global here, which is useful for repeated calibrations, as it means that the push range could be set to the old value +/- 50 kHz.

- Use Smart Start Values checkbox
   Certain fits have a "smart start" programmed in to attempt to determine what start values to use for the fit by looking at the data being fit. If your data more or less looks like a Gaussian, the smart start will do an extremely good job of finding start parameters that will result in a good fit. If this checkbox is checked, the smart start values will be used instead of the start values specified in the fit variables table.

- Smart to Start button
   Clicking this button will replace the values in the "start" column of the fit variables table with the smart start values.

- Use Errorbars checkbox
   If this is checked, the fit will be weighted by the errorbars on the points, i.e. lower error points will be given more weight. Use this if you trust that your error bars are an accurate reflection of your confidence in each point.

- Other buttons along the bottom:

   |arrowLeft| - copy the values from the "fit" column to the "start" column

   |add| - add a global push

   |remove| - remove a global push

   *Manual fit control buttons:*

   |continue| - push global manually

   |abort| - remove the fit from the selected trace

   |eyedropper| - copy the fit from the selected trace onto the fit variables table

   Fit -

   Plot -


Traces
------

.. figure:: ../images/Traces.png
   :scale: 100 %

Whenever a scan is run, each evaluation in the evaluations table generates a trace. These traces appear in the traces dock. Columns:

- Name
   The name of the trace from the evaluation control. They are categorized under the filename to which the traces are all saved. Checking/unchecking the checkbox determines if that trace is plotted.

- Pen
   What color to use to draw the trace.

- Window
   What plot window to show the trace on. Existing traces can be moved around.

- Comment
   Add a comment to the saved file.

Right clicking anywhere in the traces dock will show three checkable options:

- Unplot last trace set
   If this is checked, whenever a scan is started, the previous set of traces will be unplotted.

- Collapse last trace set
   If this is checked, whenever a scan is started, the previous set of traces will be collapsed to just the filename line.

- Expand new traces
   If this is checked, new traces will be created expanded.

Clicking on any trace will show when it was created and when it was finalized. The button "Open in Measurement Log" will open the corresponding entry in the :ref:`MeasurementLog` for the selected trace. Hitting CTRL-M with the trace selected will have the same effect.

The buttons on the top do the following:

|collapse| - collapse all trace sets (CTRL-UP)

|expand| - expand all trace sets (CTRL-DOWN)

|selectAll| - select all traces (CTRL-A)

|clear| - unplot selected traces (equivalent to checkbox)

|plot| - plot selected traces (equivalent to checkbox)

|save| - save selected trace (CTRL-S). By default, assuming the traces are being automatically saved, the traces are saved when they are created and they are finalized. If you are running a long scan and wish to save the current status of a trace that hasn't yet been finalized, you can do so with this button.

|open| - open an existing trace.

.. note:: It's recommended to do this via the :ref:`MeasurementLog` if possible, rather than via this button.

|remove2| - remove the selected trace from the list (DEL). This has no effect on the file on disk. Only finalized traces can be removed.

|applyStyle| - Apply the style in the drop down menu to the selected traces.

style drop down menu - Determines what style to use for plotting the trace (lines, points, linespoints, etc.)

|magicWand| - Show only last dataset.

Traces can be moved around in the dock using the PG-UP and PG-DOWN keys. Hitting CTRL-B on a trace will bold the text in that line. This has no effect on the trace, it is to make it easier to find a specific trace in a long list.

Fit
---

The fit interface allows fitting to traces outside of the context of fitting at the end of a scan via an analysis. The interface is the same as the Analysis control.

Progress
--------

The progress dock shows the progress of the current scan, and what scan/evaluation/analysis are currently selected.

Average
-------

Shows averaging information for the current scan.

Todo List
---------

The Todo List allows a simple GUI interface for queueing up a list of scans/evaluations/analyses, and then running through the sequence.

.. note:: This same functionality is available via the :ref:`Scripting` interface, which is considerably more powerful.

.. _Timestamps:

Timestamps
----------

.. Todo: Do we try and document this? I've never used this, and it certainly doesn't work right now.

This feature must be enabled in the experiment config file to be visible. It is intended to allow viewing a histogram of timestamps of detected photons, with 10 ns resolution. It is currently non-functional, although could be made functional if necessary with a bit of effort.