"""
Created on 02 Nov 2015 at 3:34 PM

author: jmizrahi

Home-spun auto-doc that's a little more specific to what we want to document
"""

modulesToDocument = [
    'AWG',
    'ProjectConfig',
    'dedicatedCounters',
    'digitalLock',
    'externalParameter',
    'fit',
    'gateSequence',
    'gui',
    'logicAnalyzer',
    'modules',
    'mylogging',
    'persist',
    'pppCompiler',
    'pulseProgram',
    'pulser',
    'scan',
    'scripting',
    'trace',
    'uiModules',
    'voltageControl'
]

filesToDocument = [
    'DigitalLockUi.py',
    'InstrumentLoggingUi.py',
    'ExperimentUi.pyw'
]

import os

IonControlDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '../..'))
for name in os.listdir(IonControlDir):
    if name in modulesToDocument:
        subdir = os.path.realpath(os.path.join(IonControlDir, name))
        docName = name + '-doc.rst'
        with open(docName, 'w') as f:
            f.write(name+'\n')
            f.write('='*len(name) + '\n\n')
            for subname in os.listdir(subdir):
                if subname.endswith('.py') and subname != '__init__.py':
                    subnameOnly = os.path.splitext(subname)[0]
                    f.write(subnameOnly + '\n' + '-'*len(subnameOnly) + "\n\n.. automodule:: {0}.{1}\n   :members:\n   :undoc-members:\n\n".format(name, subnameOnly))
    if name in filesToDocument:
        nameOnly = os.path.splitext(name)[0]
        docName = nameOnly + '-doc.rst'
        with open(docName, 'w') as f:
            f.write(nameOnly+'\n')
            f.write('='*len(nameOnly) + '\n\n')
            f.write(nameOnly + '\n' + '-'*len(nameOnly) + "\n\n.. automodule:: {0}\n   :members:\n   :undoc-members:\n\n".format(nameOnly))

codeDocsName='codeDocs.rst'
with open(codeDocsName, 'w') as f:
    f.write("""
Code Documentation
==================

   Contents:

   .. toctree::
      :maxdepth: 2

The code is written in Python 2.7. The GUI uses the PyQt5 library, which is a Python port of the Qt framework. Heavy use is made of the Qt model/view architecture, and Qt signals and slots. The plotting is all done using the pyqtgraph library, which is especially good at rapid plot updates.

""")
    for name in modulesToDocument:
        docName = name + '-doc'
        f.write('   '+docName+'\n')
    for name in filesToDocument:
        nameOnly = os.path.splitext(name)[0]
        docName = nameOnly + '-doc'
        f.write('   '+docName+'\n')


