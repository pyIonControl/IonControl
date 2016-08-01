.. include:: inlineImages.include

.. _MeasurementLog:

Measurement Log
===============

.. figure:: ../images/MeasurementLog.png
   :scale: 100 %

Whenever you run any scan, an entry is created in the measurement log. These entries are stored in the postgres database, and can be accessed here. The measurement log contains the entire history of all scans that have been performed on this experiment, since the project was first created. From here, old data can be easily viewed, and long term trends can be studied.

At the top of the measurement log window is the control that determines what range of dates you would like to see displayed. Click the drop down to select a range (or a custom range), and then click |refresh|. The table of measurements will be updated.

You can also filter by the name of the scan using the interface indicated in the image. Select the scans you wish to see, and then click |filter|. Right click to choose select or deselect all.

Click the checkbox next to a measurement to plot that measurement. This will plot the traces associated with that measurement, and create an entry in the trace dock. It is equivalent to opening an old trace via the |open| button on the trace dock. If the measurement occurred since the last time the program started, so that the traces are already in the trace dock, the checkbox is equivalent to the checkbox in the trace dock.

The columns of the measurement log show information about that scan. When you click on a measurement, the parameters table will display all of the parameters that were present when that measurement was taken. The results table will show all analysis results associated with that scan. When you right click an anything in the parameters or fit results tables, you can select "add as column to measurement." This will add a new column on the right hand side of the measurement with the selected element. Any measurement which has that element will display its value. This allows you to quickly see the value from any measurement of any individual parameter or fit result.

When you right click in the Parameters table, you can also select "add manual parameter." This will add a new line to the parameters table, which you can edit to record the value of anything you'd like to record associated with that measurement.

In the bottom left corner is a plot control, which allows you to create meta-measurement plots based on your measurement history. Your options for x- and y-axes are the time the plot was created, together with any column you have added by right clicking in the parameters or results windows. For example, suppose you have a set of scans each of which has a parameter "MicrowaveResonance," which may have been drifting around over the past few weeks. To plot the drift, first right click "MicrowaveResonance" in the Parameters window and select "add as column to measurement." Then in the plot section, choose "Started" for x-axis and "MicrowaveResonance" for y-axis, and the window in which you would like the plot to appear. Then click "plot," and you will get the desired plot. If you wish to see if there has been any correlation between "MicrowaveResonance" and "MoonPhase," add "MoonPhase" as a column and choose it as the x-axis.

Added columns can be removed by right clicking in the table and selecting "remove selected column."

.. warning:: The database stores all the meta-data associated with a scan, but it does NOT stores the data itself. That is stored in the text file in the data directory. The database only stores the path to that file. An entry is created in the measurement log whenever a scan is started, whether or not auto-save is on. If you choose to disable auto-save, and subsequently close the program without saving the scan, you will lose the data. The entry in the measurement log will still be there, but you will not be able to plot the data via the checkbox. Similarly, if you move (or delete) the saved file, the measurement log checkbox will not work unless you manually alter the entry in the database.

.. TODO: Studies -- not implemented
.. TODO: Re-analyzed -- not implemented