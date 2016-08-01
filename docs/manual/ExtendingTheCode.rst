.. include:: inlineImages.include

.. _ExtendingTheCode:

Extending the Code
==================

Adding Hardware
---------------

External Parameters
~~~~~~~~~~~~~~~~~~~

Add new instruments in \\IonControl\\externalParameter\\StandardExternalParameter.py. Each instrument is a class that inherits from ExternalParameterBase, and must specify its name and output channels (and associated unit). It must provide three methods: __init__, setValue, and close. It can also provide a getValue method if the instrument can report its value. For a simple example, see the class HP6632B.

If the new instrument is part of an existing category of instruments (like a VISA instrument), then no change to the experiment configuration is necessary; just add your class under the "if visaEnabled" statement.

If the new instrument is a new category which requires its own libraries/DLLs/etc., you will need to add this as an option in the experiment config file. To do that, do the following:

   1) Open \\IonControl\\config\\ExptConfigGuiTemplate.yml
   2) Add a new entry under hardware for your new instrument. Give it a description, and any necessary fields, in the same way that the other instruments are specified. Note that configuration options for specific instances of instrument can be specified in the params selection GUI. THe configuration options in the expt config file are more for the entire category of instrument, i.e. things like DLLs.

These two steps will make your piece of hardware appear as an option in the experiment config GUI.

   3) In StandardExternalParameter.py, add a line of the form:

      .. code-block:: python

         yourInstrumentEnabled = project.isEnabled('hardware', 'yourInstrument')

   4) Create your class inside of an if statement "if yourInstrumentEnabled." Read in any configuration data by looking in the project dictionary.

You should now be able to select your instrument from the Params Selection GUI.

Voltage Controllers
~~~~~~~~~~~~~~~~~~~

AWGs
~~~~

Adding Evaluations
------------------

The evaluations are defined in \\IonControl\\scan\\CountEvaluation.py, and listed in \IonControl\scan\EvaluationAlgorithms.py. Each evaluation is a class which inherits from EvaluationBase, and is listed in EvaluationAlgorthms.py. An evaluation class must provide:

   - A name
   - A tooltip
   - Any settings that define the evaluation, and their type (defined in the method "children")
   - the method "evaluate" that takes in the data, and returns a 3-tuple:

      (evaluated value, (upper error bar size, lower error bar size), raw value)

      Raw value is typically the value not scaled by the number of experiments, i.e. if 100 experiments were performed and in 43 of them the ion is bright, the evaluated value would be 0.43 and the raw value would be 43.

See ThresholdEvaluation for a relatively simple example.

Adding Fits
-----------

The fits are defined in \\IonControl\\fit\\FitFunctions.py. Each fit is a class which inherits from FitFunctionBase. At a bare minimum, the fit must provide:

    - a name
    - a function string to display
    - a list of parameters
    - default values
    - the method "functionEval" which defines how to evaluate the function.

See SinSqGaussFit for a relatively simple example.

Fits can also provide:

    - an 'update' method for updating other variables which are not fit variables
    - a 'smartStartValues' method for guessing good start values based on the data

see the existing fit functions for more examples.