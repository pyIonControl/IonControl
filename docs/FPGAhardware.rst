Hardware
========

The only FPGAs that can currently be used with this software are the Opal Kelly **XEM6010-LX45** and the **XEM6010-LX150**.
The LX150 is a larger FPGA, but you cannot compile firmware for it without a license. It is therefore a more expensive
option if you need to modify the FPGA firmware itself. However, the firmware as it stands is pushing the capacity limits
of the LX45, and there is very little room for any future modifications.

All firmware can be found in /IonControl/FPGA_Ions

A given bitfile assumes a specific internal hardware configuration, as the FPGA must know what pins are connected to what
DDS/DAC/ADC.

In the following, the standard hardware configuration as well as the differences of the setup-specific hardware
configurations are described.

Standard Configuration
----------------------

The bitfiles *IonControl-firmware-no-div.bit*, *IonControl-firmware-8Counters.bit*, *IonControl-firmware-20MHz-DDS-SCLK.bit* and *IonControl-firmware-LX150.bit* are used for the LX-45 and LX-150 version of the
XEM-6010. All firmwares compiled for LX150 include LX150 in the file name. The firmware is specific to the FPGA and cannot be used with the other FPGA. Thus, please make sure to choose the correct version.
A firmware for the LX45 FPGA is approximately 1450kB, for the LX150 it is approximately 4125kB.

The full functionality of the firmware is slightly too large for the LX45 FPGA. Thus the standard firmware cannot be compiled for LX45 (without timing violations). There are three different firmware files trhat can be used with the LX45 FPGA.
Each has a specific limitation that makes it possible to fit in the LX45.

* *IonControl-firmware-no-div.bit* does *NOT* include the division command in the pulse program. It will *NOT* do any divisions.
* *IonControl-firmware-8Counters.bit* only includes 8 counter channels and 2 timestamping channels. (But includes the division).
* *IonControl-firmware-20MHz-DDS-SCLK.bit* uses a 20MHz serial clock for communication with DDS chips. This means writing the frequency takes about 3us instead of 1.5us.

This standard firmware setup is for use with the Duke breakout board *OpalKellyIonControlBoxFanout_v3b*,
which contains 8 DAC channels, 8 ADC channels, 3x 8 pin TTL input banks, 9x 8 pin TTL output banks,
and 10x SMA TTL outputs (for connecting to RF switches).

* **In1** Input bank 1 is connected to counter channels 0-8.
* **In2** Input bank 2 is connected to counter channels 9-15.
* **In3** Input bank 3 is connected to trigger channels 0-7.

* **Out1** Output bank 1 is connected to shutters 0-7.
* **Out2** bits 0-5 are connected to shutters 8-13, bit 6 is connected to trigger 17 and bit 7 forms a serial interface. This is intended for use with the trap voltage 100 channel DAC system.
* **Out7** Output bank 7 is connected to shutter channels 16-23.

The FPGA is configured to talk to four of the 2 channel AD9912 DDS boards: *DDS-AD9912_r4*, for a total of 8 DDS channels.
The breakout board should be connected to the DDSs as follows:

* **Out3**: Channels 1 and 0 in the opposite order from what's labeled on the DDS board, that is if you look at the board with the rf output connectors facing you and the chip on the top side then the left channel is channel 0, the right channel 1)
* **Out4**: Channels 3 and 2 (same as above)
* **Out5**: Channels 5 and 4
* **Out6**: Channels 7 and 6

SMA switch channels:

* **DDS 0**: JP2-31, shutter 24
* **DDS 1**: JP2-34, shutter 25
* **DDS 2**: JP2-30, shutter 26
* **DDS 3**: JP2-33, shutter 27
* **DDS 4**: JP2-29, shutter 28
* **DDS 5**: JP2-32, shutter 29
* **DDS 6**: JP2-37, shutter 30
* **DDS 7**: JP2-38, shutter 31

A variation of the firmware using 20MHz serial clock to communicate with the DDS chips (instead of 40MHz) is available
as *IonControl-firmware-20MHz-DDS-SCLK.bit*

Setup-specific configurations
-----------------------------
In the following setup-specific configurations only deviations from the standard configuration are described.


DDS10
^^^^^

* **Out7**: DDS channels 8 and 9

Duke
^^^^
Is currently not available. PLease let me know if it is needed.
* **Out2** bits 0-5 are connected to shutters 8-13, bit 6 is connected to trigger 17 and bit 7 forms a serial interface. This is intended for use with the trap voltage 100 channel DAC system.
* **Out7** is connected to two AD9910 boards, DDS channels 7 and 8
* **Out6** is connected to Magiq pulser, DDS channel 9
* Scanning of DAC channels is not included

QGA
^^^

* **Out2** bits 0-5 are connected to shutters 8-13, bit 6 is connected to trigger 17 and bit 7 forms a serial interface. This is intended for use with the trap voltage 100 channel DAC system.
* **Out7** is unconnected.
* SMA switch channels are active low and have a different channel assignment:

* **DDS 0**: JP2-31, shutter 24
* **DDS 1**: JP2-34, shutter 25
* **DDS 2**: JP2-30, shutter 26
* **DDS 3**: JP2-33, shutter 27
* **DDS 4**: JP2-29, shutter 28
* **DDS 5**: JP2-32, shutter 29
* **DDS 6**: JP2-39, shutter 30
* **DDS 7**: JP2-37, shutter 31



QGA-ExtClk
^^^^^^^^^^

* **Out2** bits 0-5 are connected to shutters 8-13, bit 6 is connected to trigger 17 and bit 7 forms a serial interface. This is intended for use with the trap voltage 100 channel DAC system.
* **Out7** is unconnected.
* SMA switch channels are active low and have a different channel assignment:

* **DDS 0**: JP2-31, shutter 24
* **DDS 1**: JP2-34, shutter 25
* **DDS 2**: JP2-30, shutter 26
* **DDS 3**: JP2-33, shutter 27
* **DDS 4**: JP2-29, shutter 28
* **DDS 5**: JP2-32, shutter 29
* **DDS 6**: JP2-39, shutter 30
* **DDS 7**: JP2-37, shutter 31

* An external 100MHz clock can be supplied on the SMA connector JP2-38. If the supplied clock is phase locked to the 1GHz reference used for the DDS clock, all DDS channels can updated phase synchronous. To achieve phase synchronous operation, the channels have to be reset first.

Wiggely-line box
^^^^^^^^^^^^^^^^

* Uses the Sandia breakout board version 1
* There are only 6 DDS channels present.

* **In1** is connected to counter channels 0-7 and 8-15.
* **In2** bits 0-5 are connected to trigger channels 0-5. Bits 6 and 7 are not present.
* **Out2** bits 0-6 are connected to shutters 8-14, bit 7 is a fanout for in1
* SMA switch channels are active low and have a different channel assignment:

* **DDS 2**: JP2-31, shutter 26
* **DDS 5**: JP2-34, shutter 29
* **DDS 1**: JP2-30, shutter 25
* **DDS 4**: JP2-33, shutter 28
* **DDS 0**: JP2-29, shutter 24
* **DDS 3**: JP2-32, shutter 27
* **DDS 6**: JP2-39, shutter 30
* **DDS 7**: JP2-37, shutter 31


Breakout Boards
---------------


Sandia v1
^^^^^^^^^

Original breakout board. 6x 8 bit 50 Ohm driven outputs, 2x 8bit 50 Ohm terminated inputs.
 4 channel ADC, 4 channel DAC.

**Problems:**

* After a power up of the board and without writing the firmware, all output bits are high.
* 2 bits on In2 and 2 bits on Out6 are not functional.

.. figure:: images/SandiaBreakoutv1brd.png
   :scale: 100 %
   :alt: map to buried treasure

Sandia v2
^^^^^^^^^

6x 8 bit 50 Ohm driven outputs, 2x 8bit 50 Ohm terminated inputs. 4x 8bit direct connections.
 4 channel ADC, 4 channel DAC.

**Problems:**

* After a power up of the board and without writing the firmware, all output bits are high.

.. figure:: images/SandiaBreakoutv2brd.png
   :scale: 100 %
   :alt: map to buried treasure


Duke v1
^^^^^^^

**Problems:**

* After a power up of the board and without writing the firmware, all output bits are high.


Duke v2
^^^^^^^

This version of the breakout board uses enable bits for the 50 Ohm drivers that are only enabled once the firmware is uploaded.
Thus there is no unintended high output after a power failure.

.. figure:: images/DukeBreakoutv3b.png
    :scale: 50%