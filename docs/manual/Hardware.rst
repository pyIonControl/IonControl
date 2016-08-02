.. include:: inlineImages.include

.. _Hardware:

Hardware
========

The program is able to control a number of different pieces of hardware, in addition to the main FPGA. Relatively simple hardware, with a small number of inputs and outputs, is controlled via the :ref:`ExternalParameters` interface. More complex hardware requires its own dedicated interface, which is documented here.

.. _VoltageControl:

Voltage Control
---------------

As of this writing (Nov. 2 2015), there are two voltage controllers which the program can control:

- The National Instruments 6733 series DACs

   To use this, add it to the project experiment config file via the experiment config GUI (see :ref:`Projects`), add "Voltages" to the software features, and set the hardware to be the NI Chassis.

- The 100 channel Duke designed DAC board, controlled by an Opal Kelly FPGA

The voltage control files are as follows:

- Electrode Mapping

- Voltage Definition

- Global Adjust

The voltage windows are:

- Global Adjust

- Local Adjust

- Control

   - Line

   - Line Gain

   - Global Gain

   - Shuttling

.. _AWG:

AWG
---