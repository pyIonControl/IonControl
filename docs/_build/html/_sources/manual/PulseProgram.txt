.. include:: inlineImages.include

.. _PulseProgram:

Pulse Program
=============

Once the configuration files have been setup, the main program opens. The first time the program runs, the pulse program window will also open. On subsequent runs, it will return to whatever state it was in when it was closed last. To open the pulse program window, click |pulses| .

.. figure:: ../images/PulseProgram.png
   :scale: 100 %

   The pulse program interface

The pulse program window consists of the following docks:

   - Pulse Program
      This is the primary dock, which is the text file itself. Ideally this is changed rarely, i.e. only when some sort of fundamental change to the experiment structure is needed. Generally different pieces of the experimental sequence can be included or omitted simply based on whether their duration is non-zero, i.e.:

      .. code-block:: Python

         if PumpTime > 0:
            pump()

      By using conditionals this way, you do not need to modify the pulse program itself when you want to turn off pumping. Instead, just set PumpTime to zero, which can be done using the checkboxes in the parameters dock (see below).

   - Parameters
      This is an interface for setting parameters which are declared in the pulse program. Any expression can be typed in here, and the result will be shown under "evaluated." Expressions can reference global variables, and can also reference other pulse program parameters. If parameter *A* depends on parameter *B*, and parameter *B* is scanned, parameter *A* is scanned too. This allows things like this:

      .. figure:: ../images/parameterDependenciesExample.png
         :scale: 100 %
         :align: center

         Example of pulse program dependencies. If *GateDetuning* is now scanned, *detuning* will be scanned as well (because it depends on *GateDetuning*), as will *RamanGateDDSFreq1* and *RamanGateDDSFreq2* (because they depend on detuning). The code will not allow circular dependencies.

      All parameters can be scanned in the scan control, see :ref:`Scans`. If the checkbox next to a parameter is unchecked, the parameter is set to zero. Unchecking the checkbox is equivalent to typing '0' into the value field, without losing the contents of the value field.

      .. important:: Scanning a parameter overrides the checkbox. If a parameter which is unchecked is subsequently scanned, it will be changed to a non-zero value by the scan.

   - Shutters
      Interface for defining shutters. When a `shutter` or `masked_shutter` is declared in the pulse program, a new line will show up here to define that shutter. The columns correspond to individual TTL lines, with names set in the main GUI shutters interface. A shutter sets every TTL bit, while a masked_shutter only sets specified bits.

         - **Green:** TTL High
         - **Red:** TTL Low
         - **White:** No change

      The last 16 bits are internal control lines for turning on and off the PI Loops, and turning on and off the DAC scans.

   - Triggers
      Interface for defining triggers. A trigger is an internal signal that goes high for one clock cycle (= 10 ns) before going low again. There are trigger lines for updating the DDSs, updating the DACs, and resetting the PI Loops. When a `trigger` is declared in the pulse program, a line is added.

   - Counters
      Interface for defining specific counters to gate, or other types of measurements done by the FPGA. The counters interface has the following columns:

         - Count<n>:
            TTL input line <n>

         - TS<n>:
            Timestamp line for TTL input <n>, see :ref:`Timestamps`

         - ADC<n>:
            Voltage on ADC<n>

         - PI<n>:
            line for monitoring output of PI<n>.

            .. important:: This is not to be confused with the PI<n> enable lines in the shutters interface! Those lines are for turning PI loops on and off, while these lines are for monitoring the output of PI loops.

         - timeTick:
            On rising edge of counter, inserts the current time tick into the stream to the computer. It is saved in the raw data and results file, and can be used as an x-axis in plots. It is intended to give absolute hardware timestamps to experiments to check for things like 60 Hz noise.

         - id:
            Assigning a counter line an id allows using the same physical counter in multiple roles. For example, suppose you want to monitor fluorescence during cooling and during detection, and you have a single PMT connected to channel 0. You would have two lines for creating the counters, `counter CoolingCounters` and `counter DetectionCounters`. Both would have *channel 0* selected, but one with *id 0* and one with *id 1*. The two counters can then be treated as if they were different physical counters.

   - RAM Control
      Interface for selecting a file to directly write to the RAM on the FPGA board. If the checkbox is checked, the RAM will be written.

      .. important:: This overwrites the RAM values set by the :ref:`GateSequences` interface.

      The RAM Control file is a YAML file, with a line for each entry in the RAM specifying a value, unit, and encoding. An example can be found in \\IonControl\\config\\RAMFiles\\RamExample.yml. These can then be read out in the program using the `read_ram()` command. This file must be generated by you. One application would be something like sideband cooling with unequal red sideband pi times. The RAM file could specify a list of pi times to use as the sideband cooling progresses.

When a pulse program is saved (CTRL-S in the editor, or click |save|), the program attempts to compile it. If it fails, it indicates where and why it failed. If it is successful, it updates the parameters, shutters, triggers, and counters displays to match the pulse program.

The pulse program is run on the FPGA. It is compiled to a machine code that contains microcontroller instructions that are understood by the FPGA. A moderately complex pulse program, with lots of comments, can be seen in /IonControl/config/PulseProgramsPlus/Example.ppp.

The pulse program configuration (which includes everything in the pulse program window) can be saved using the drop down menu in the parameters dock. This allows rapidly switching between different pulse program configurations. To make a new configuration set, just type a new name in the drop down menu and hit enter. By default, all changes made to any aspect of the pulse program window are saved to the currently selected configuration. If you do not want that behavior, right click anywhere in the pulse program window and de-select "Automatically Save Configuration." Do so at your own peril. If you do disable autosaving, you can save a configuration by clicking the |save| icon next to the drop down menu.

Pulse Program Syntax
--------------------

Introduction
~~~~~~~~~~~~

update
``````

The most important pulse program command to understand is the `update(duration)` command. Most pulse program commands to not effect any physical change to the FPGA behavior until the next `update`. When the program reaches an `update`, it has two effects: First, it simultaneously triggers all the commands since the last update, and second, it starts a timer of length equal to the argument of the update command. The effect of the timer is to prevent any subsequent `update` command from executing until the timer has elapsed. For example, consider the following code:

   .. code-block:: Python

       set_shutter( DetectOn )         # Get ready to set shutter DetectOn at the next update
       set_counter( DetectCounters )   # Get ready to count on counter DetectCounters at the next update
       update( DetectTime )            # simultaneously trigger previous two commands, and start counter of length DetectTime
       set_inv_shutter( DetectOn )     # Get ready to set inverse shutter of DetectOn
       set_shutter( CoolingOn )        # Get ready to set shutter CoolingOn
       clear_counter()                 # Get ready to stop counting on previously set counter, and transmit result to the computer
       update()                        # Simultaneously trigger previous three commands. This does not execute until DetectTime has elapsed since the last update

The effect of this code is to simultaneously turn on the `DetectOn` shutter and count on the `DetectCounters` counter for a time `DetectTime`. After `DetectTime` has elapsed, it will simultaneously reverse the `DetectOn` shutter, turn on the `CoolingOn` shutter, stop counting, and transmit the count results to the computer.

.. note:: The commands executed between update commands take a finite amount of time to execute. Many commands take about 50 ns (= 1 microcontroller cycle = 5x 100 MHz clock cycles). Some commands, such as `set_dds`, can take as much as 2 us if all possible bits are sent to the DDS. Therefore, in the example above, if DetectTime is set to be extremely short, it is possible that DetectTime will elapse *before* the next update is reached, the result being that the detect shutter and counter are on longer than was likely intended. When this happens, the FPGA will tell the computer and the program will report a timing violation warning.

.. note:: DDS 9912 amplitude changes happen *immediately*, not with the next trigger.

running scans
`````````````

When running a scan, the computer has a deep pipe to the FPGA which it populates with scan values. The overall structure of a pulse program is typically something like this:

   .. code-block:: Python

      while not pipe_empty():
         apply_next_scan_point()

         #<...all your code goes here...>

      exit( endLabel )

The `pipe_empty()` command checks whether there are still scan values in the pipe. The `apply_next_scan_point()` command sets all parameters that being scanned (i.e., the scan parameter and all its dependencies) to the new value pulled off the pipe. Once the pipe is empty, the program ends.

Typically a pulse program also has an inner loop to execute an experiment multiple times, which might look something like this:

   .. code-block:: Python

      while not pipe_empty():
         apply_next_scan_point()

         #<...code that runs before experiment loop goes here...>

         currentexperiment = 0 #currentexperiment is a var (an internal variable) that keeps track of how many repetitions have been done

         while currentexperiment < experiments: # experiments is a parameter defining how many times to repeat each point

            #<...code for each experiment goes here...>

            currentexperiment += 1

         #<...code that runs after experiment loop goes here...>

      exit( endLabel )

Functions
`````````

Functions defined in the pulse program are macros rather than true functions. They cannot take arguments. The code defined in a function is substituted in-line in the location where the function is called.

Minimal example
```````````````

Below is a complete bare bones example of a very simple pulse program, which turns on four different shutters for times given by a parameter, set one DDS, and counts during detection. A more complex pulse program, with comments, can be found in \\IonControl\\config\\Example.ppp.

.. literalinclude:: ../../config/PulseProgramsPlus/barebones.ppp
   :language: Python

control structures
~~~~~~~~~~~~~~~~~~

The following control structures are supported:

- while loops

   .. code-block:: Python

      experimentsleft = 100
      while experimentsleft>0:
         experimentsleft -= 1

- if then else conditionals

   .. code-block:: Python

      if photonsfound>0:
         experimentsleft -= 1
      else:
         exit( IonLostExitcode )

Variable Types
~~~~~~~~~~~~~~

.. include:: pppDefinitionDocs.include

Encodings
~~~~~~~~~

.. include:: pppEncodingDocs.include

Commands
~~~~~~~~

   .. automodule:: Builtins
      :members:
      :exclude-members: exit_
