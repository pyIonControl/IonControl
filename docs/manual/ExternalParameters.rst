.. include:: inlineImages.include

.. _ExternalParameters:

External Parameters
===================

External parameters are instruments not directly controlled by the FPGA, which are not sufficiently complex so as to require their own GUI (like a voltage controller or an AWG). These are things like a microwave frequency source or a motorized micrometer, where a small number of control parameters determine the behavior of the device.

In the experiment config GUI (see :ref:`Projects`), categories of hardware can be selected (such as "Conex controllers" or "VISA instruments"). This will determine what hardware can be added via External Parameters.

To add instruments which are not currently available in the software, see :ref:`ExtendingTheCode`.

Params Selection
----------------

In the Params Selection dock, you add pieces of equipment. In the drop down, select the type of instrument. Under "Instrument," type the address of the instrument. For COM instruments, this might be something like "COM13." For VISA instruments, this might be something like "GPIB0::12::INSTR," or a name set in NIMAX. Under "Name," give the instrument whatever name you want to use. Then click |add|. The instrument will appear in the table. When you click on the instrument, any configuration options associated with that piece of hardware will appear in the lower table.

To use the instrument, click the "Enable" checkbox. The program will try to connect to the instrument. If it is successful, the box will be checked. The instrument is now enabled.

Params Control
--------------

In the Params Control dock, all enabled instrument channels are shown. You can set the value of a channel by typing a value into "Control." Global variables and expressions can be used here. If the instrument reports back its value, or if it is measured in some other way, then the measured value is shown in the "External" column. If it is not, this column will simply be a duplicate of "Control."

Each channel has a set of configuration options. In addition to options specific to each channel, all channels have the following options:

- jump, stepsize, and delay:
   If *jump* is checked, the channel will instantly moved to the new value whenever a new value is typed in. If *jump* is unchecked, the channel will move by an amount *stepsize*, wait a time *delay*, move by *stepsize* again, etc., until it reaches the specified value. This allows control over how fast an external parameter's value changes.

- persistDelay:
   How long the channel should hold a value before that value is committed to the database.

Params Reading
--------------

If an instrument has readings that it reports back to the computer (in addition to the reported values of channels), they will be displayed here. This is configured in the code associated with the instrument.

