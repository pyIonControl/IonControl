.. include:: inlineImages.include

.. _Introduction:

Introduction
============

**Note**: Before you can run the program for the first time, you must install all the dependencies listed in :ref:`Installation`.

The main file to run the program is **ExperimentUi.pyw**. This program can be executed directly, or can be run from within an IDE.

Concepts
--------

The IonControl program is based around the following concepts, which will be explained in detail in this manual:

    1) :ref:`PulseProgram`. The pulse program is a "pythonic" text file which is executed by a microcontroller implemented on the FPGA. The pulse program controls:

        1) The timing of all TTL outputs
        2) Counting on TTL inputs
        3) Monitoring of ADC inputs
        4) programming of DDSs
        5) programming of DACs
        6) behavior of FPGA PI loops

    The pulse program can execute standard control structures, such as loops and conditionals, and can do simple math. It can also read data from on-board RAM.

    All of this is implemented in firmware (known as a *bitfile*) which is written to the FPGA. At the moment (10/14/2015), bitfiles have been produced for the following two FPGA modules:

        1) Opal Kelly XEM6010-LX45
        2) Opal Kelly XEM6010-LX150

    Other FPGA modules could in principle be added at some point in the future.

    2) :ref:`Scans`. One dimensional scans are controlled by three separate interfaces:

        1) The **scan** interface allows a one-dimensional scan over any parameter defined in the pulse program, or any other instrument connected to the computer that is defined in the software. At each point in the scan, data is returned by the FPGA. The results of a scan are saved to a text file, and also registered in the :ref:`MeasurementLog`.
        2) The **evaluation** interface determines how that data is plotted. An evaluation is a defined method for taking a set of data and reducing it to a single point for plotting, such as "mean" or "discriminator" or "parity." As many evaluations as needed can be added. The plot windows are completely reconfigurable; you can add as many plot windows as necessary, and each evaluation can be directed to any plot window.
        3) The **analysis** interface determines how the data is fit at the conclusion of the scan. In addition, the analysis interface can push the results of a fit to a global variable, which can in turn be referenced by any part of the program. In this way, calibrations are straightforward.

    3) :ref:`DedicatedCounters`. The dedicated counters interface allows continuous monitoring of the counters, ADCs, and PI Loops controlled by the FPGA. It displays counts whether or not a scan is running, and is therefore useful for continuous monitoring. It also has an interface for automatic ion loading.

    4) :ref:`Scripting`. The scripting interface allows for the creation of extremely complex, automated experiments. It executes Python scripts, but adds a number of commands which allow control over the experiment.

Interface
---------

A few general points about the interface:

Units
~~~~~

Almost all quantities referenced in the program have units. This is for the simple reason that real physical quantities have units, and using them avoids any ambiguity. (It also helps avoid spacecraft crashing into planets.) This means a few things:

- quantities can be typed as 0.365 MHz or as 365 kHz or as 365000 Hz, they are all equivalent.
- in fields which allow mathematical expressions, units are respected -- you could write something like:

   .. code-block:: python

      7 kHz + 1/(100 us)

  which would equal 17 kHz. This can be useful for writing things like:

   .. code-block:: python

      ExpectedPhotonNumber = CoolingTime * ExpectedFluorescenceRate

   Here CoolingTime likely has base unit seconds, ExpectedFluorescenceRate has base unit Hz, and ExpectedPhotonNumber is unitless, as expected. If CoolingTime changes, ExpectedPhotonNumber changes appropriately.

Spin boxes
~~~~~~~~~~

In most boxes that allow entering a number, the value can be changed by either typing in a number, or by using the up and down arrows. When using the up and down arrows, the digit to the left of the cursor will change.

Global Variables
~~~~~~~~~~~~~~~~

Global variables can be used almost everywhere throughout the program. In many cases it is far more useful to reference something to a global, rather than giving it its own value. If the same value will appear in more than one place, you are always better off setting it to a global.

GUI reconfiguring
~~~~~~~~~~~~~~~~~

The GUI is highly reconfigurable. Plot windows and almost all control windows (known as "docks") can be resized, rearranged, tabbed on top of each other, closed, or pulled out as a stand alone window. The GUI configuration is automatically saved to the database. This means that when you close the program and reopen it, the GUI appearance will stay the same. Closed docks can be re-opened via the "view" menu. In the main experiment GUI, they can also be re-opened by right clicking on a dock header bar.

Settings Menus
~~~~~~~~~~~~~~

Many places in the program have *settings menus*, which are drop downs that allow you to save and recall all the settings associated with that particular interface. For example, the scan control settings menu allows you to load different scan settings. To make new saved settings, simply type a new name into a context menu and push enter. You can then edit the new settings.

Data
~~~~

Whenever a scan is run, by default the data is saved to a text file in /<YourProjectDir>/<Year>/<Month>/<Day>/ (see :ref:`Projects`). The saved file has an XML header with all the metadata about the scan (i.e., what all the settings were when this scan was run), followed by a table with all the data. The metadata element *ColumnSpec* (together with *TracePlottingList*) indicates what column is what in the data table.

Information about all scans which have been performed on the project is stored in the database and accessed via the :ref:`MeasurementLog`, which has an absolute path to the data filename. Therefore, it is important that you not delete or move data files, or the measurement log will not work properly (unless you directly change the database entry as well).

This requirement may be removed at some future point by also storing the data itself in the database.