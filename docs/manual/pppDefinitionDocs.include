.. py:data:: const

   A constant value, which is typically used for things like DDS Channel numbers, which do not change.

   For example:

      .. code-block:: python

         const DDSDetect = 0
         const DDSCooling = 1

.. py:data:: parameter

   A numerical value that is set by the user or by a scan. This is the main variable type which allows configuring the experiment. When the pulse program is saved, the list of parameters in the parameter window is updated.

   The simplest parameter declaration would be:

   .. code-block:: Python

      parameter CoolingTime

   This initializes a parameter named "CoolingTime," which will show up in the parameter table and as a scan target. You can also type:

   .. code-block:: Python

      parameter CoolingTime = 500 us

   The effect of this will be to set CoolingTime to 500 us when you save the program and CoolingTime is added to the parameter list. However, that is the only time the 500 us value is read! Every subsequent time the program is run, the value of CoolingTime will be set via whatever is typed into the Parameters table, or via a scan. Therefore, this is to be avoided, as it can lead to confusion, and instead parameters should be declared without any value called out in the pulse program code.

   A parameter can also have a device specific *encoding*. An encoding is a way of translating something like "200 MHz" into a frequency tuning word used to program a DDS. An encoding is written like this:

   .. code-block:: Python

      parameter <AD9912_FRQ> CoolingFreq

   This means that :python:`CoolingFreq`, which is in MHz, will be converted appropriately to program an AD9912 DDS. Encodings are only necessary on a frequency that is actually written to a DDS. For example, the following is fine:

   .. code-block:: Python

      const DDSRaman1 = 2
      parameter RamanCarrierFreq
      parameter RamanDetuning
      parameter <AD9912_FRQ> DDSRaman1Freq
      set_dds(channel=DDSRaman1, freq=DDSRaman1Freq)

   where in the parameters table, :python:`DDSRaman1Freq` is set to :python:`RamanCarrierFreq + RamanDetuning`. Only :python:`DDSRaman1Freq` need have the encoding, as it is the only one which is directly written to the DDS, while the others are used indirectly.

.. py:data:: var

   An internal variable. This is something that might change throughout the course of an experiment (unlike **const**), but which is set within the experiment rather than by the user.

   For example:

   .. code-block:: python

      var experimentsleft = 100

   where experimentleft is an internal variable, initialized to 100. The difference between **var** and **parameter** is only in how they are treated by the GUI; **var** variables are not shown in the GUI as something to be scanned or set by the user. Also, normally there are programmatic changes made to **vars**, while **parameters** are not changed by the program unless they are being scanned. This is for clarity, though, not a requirement. As with parameters, vars can have an encoding.

   Unlike parameters, vars normally need to be initialized in the code, as they are not overridden from outside the code.

.. py:data:: shutter

   A shutter specifies the state of every TTL output of the FPGA, whether every PI loop is on or off, and whether the DAC scans are on or off (see :ref:`PILoops` for an explanation of the last two). When a shutter is added to the pulse program, a new line appears in the shutters window.

.. py:data:: counter

   A counter variable. When a counter is added, a new line appears in the counters GUI. Counters are gates to count on input channels or to record ADC channels or PI channels. Results are transmitted to the computer.

.. py:data:: masked_shutter

   As shutter, however it has three states: red: off, green: on, white: do not change

.. py:data:: trigger

   A set of channels to trigger.

.. py:data:: address

   An address is just a parameter which is used specifically as a RAM address.

.. py:data:: exitcode

   Exitcodes are transmitted to the computer when the pulse program stops executing. Exitcodes are 64bit numbers where the most significant bits are 0xfffe.

   For example:

   .. code-block:: Python

      exitcode IonLostExitcode = 0xfffe000000000001
      exitcode SuccessExitcode = 0xfffe000000000000

