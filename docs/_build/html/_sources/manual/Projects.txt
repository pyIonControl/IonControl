.. include:: inlineImages.include

.. _Projects:

Projects
========

All of the program settings, GUI configuration, data, etc. are attached to a specific *project*. Oftentimes only a single project is necessary for a given lab. However, if for whatever reason you need to be able to switch between totally different configurations of the program, the project functionality will allow this.

Project Selection
-----------------

When you start the program for the very first time, you will be asked to select a base directory. This will be the directory under which will be the individual project directories. Once you select a base directory, the project selection GUI will appear:

.. figure:: ../images/ProjectSelection.png
   :scale: 100 %

   Project selection GUI.

Existing projects can be selected in the table, or a new project can be added by typing a name into the editor and clicking "create." If "Set as default" is checked, the GUI will not be shown the next time the program opens. Instead, the selected project will be used. A different base directory can also be selected via this GUI.

This GUI creates a configuration file in the source directory: *\\IonControl\\config\\ProjectConfig.yml*. This file contains three lines, specifying the base directory, the project name, and whether or not to show the project selection GUI the next time the program starts. The GUI can be bypassed entirely by editing this file directly. The GUI is simply an interface for editing the config file.

If you wish to see the project selection GUI the next time the program starts up, you can do so via the main control program by selecting File > Project. This will display the currently selected project along with its configuration, and give you the option to show the selection GUI on next startup. Alternatively, you can directly edit ProjectConfig.yml, and change *showGui* to *True*.

Experiment Configuration
------------------------

Once a project is selected, the experiment configuration GUI will appear:

.. figure:: ../images/ExptConfig.png
   :scale: 100 %

   Experiment configuration GUI.

This GUI allows you to select what pieces of hardware or types of hardware are connected to the computer, and how it is configured. It also allows you to selectively enable or disable specific software features and establishes the connection to the database. For example, select *Opal Kelly FPGA: Pulser* from the "Available Hardware" drop down menu, then click |add|. This will add that item to the list of available hardware. A tab will appear with configuration data specific to that item. For the FPGA, click "Scan" to scan for Opal Kelly FPGA devices connected to the computer, which will populate the device drop down menu. Select from that menu which FPGA to use. Click "Upload" to upload the selected bitfile to the selected FPGA. Click "uploadOnStartup" to have the program automatically upload the bitfile whenever the program starts (this is normally not necessary).

"Software Features" works the same way as does the hardware. Under "Software Features," select *Pulser* and click |add| . This has one configuration field, which is what piece of hardware to use for the pulser. Select *Opal Kelly FPGA: Pulser* from the dropdown. Other hardware/software features can be added similarly.

Each hardware and software item has an enable checkbox next to it. Unchecking this disables that item, and is functionally equivalent to removing that item completely by clicking |remove| . The only difference is that if an item is removed, its configuration data is deleted. If an item is unchecked, its configuration data remains. Therefore, use the enable checkbox for items you wish to remove only temporarily.

Under "Database connection," type in the password you set up during :ref:`Installation`.

If "Set as default" is checked, the GUI will not be shown the next time the program starts.

This GUI creates a configuration file in the project directory: *\\YourBaseDirectory\\YourProjectName\\config\\ExptConfig.yml*. This file contains a list of hardware, software, the configuration of each, and the database connection. As with the project selection GUI, the experiment configuration GUI is a front end for editing this file. The GUI can be bypassed by editing the file directly. As with the project configuration file, if you wish to see the experiment configuration GUI on next program start after it was already set to default, you can do so via the main control program by selecting File > Project. Alternatively, you can edit ExptConfig.yml and change *showGui* to *True*.
