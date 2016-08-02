# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui, QtDesigner
from uiModules.FileComboWidget import FileComboWidget

# This class implements the interface expected by Qt Designer to access the
# custom widget.  See the description of the QDesignerCustomWidgetInterface
# class for full details.
class FileComboWidgetPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
    # Initialize the instance.
    def __init__(self, parent=None):
        super(FileComboWidgetPlugin, self).__init__(parent)
        self._initialized = False

    # Initialize the custom widget for use with the specified formEditor
    # interface.
    def initialize(self, formEditor):
        if self._initialized:
            return
        self._initialized = True

    # Return True if the custom widget has been initialized.
    def isInitialized(self):
        return self._initialized

    # Return a new instance of the custom widget with the given parent.
    def createWidget(self, parent):
        return FileComboWidget(parent)

    # Return the name of the class that implements the custom widget.
    def name(self):
        return "FileComboWidget"

    # Return the name of the group to which the custom widget belongs.  A new
    # group will be created if it doesn't already exist.
    def group(self):
        return "IonControl Custom Widgets"

    # Return the icon used to represent the custom widget in Designer's widget
    # box.
    def icon(self):
        return QtGui.QIcon(_logo_pixmap)

    # Return a short description of the custom widget used by Designer in a
    # tool tip.
    def toolTip(self):
        return "Combo box for creating, opening, and saving files"

    # Return a full description of the custom widget used by Designer in
    # "What's This?" help for the widget.
    def whatsThis(self):
        return """Combo box that contains a list of files, together with a button for
                  removing items from the combo box, and button for saving files, a
                  button for opening files, a button for creating files, and a button
                  for reverting the file to the version on disk."""

    # Return True if the custom widget acts as a container for other widgets.
    def isContainer(self):
        return False

    # Return an XML fragment that allows the default values of the custom
    # widget's properties to be overridden.
    def domXml(self):
        return '<widget class="FileComboWidget" name="FileComboWidget">\n' \
               ' <property name="objectName" >\n' \
               '  <string>fileComboWidget</string>\n' \
               ' </property>\n' \
               '</widget>\n'

    # Return the name of the module containing the class that implements the
    # custom widget.  It may include a module path.
    def includeFile(self):
        return "uiModules.FileComboWidget"


# Define the image used for the icon, in XPM format
_logo = [
"26 26 122 2",
"   c #000000",
".  c #04070F",
"X  c #0B0B0B",
"o  c #070912",
"O  c #0B0D15",
"+  c #0B1019",
"@  c #0D1119",
"#  c #11141C",
"$  c #10141E",
"%  c #14171E",
"&  c #141921",
"*  c #161A22",
"=  c #171B25",
"-  c #191D26",
";  c #1C202C",
":  c #21242D",
">  c #23262F",
",  c #222631",
"<  c #282B34",
"1  c #2A2D36",
"2  c #2D3038",
"3  c #2E313A",
"4  c #32343B",
"5  c #373A42",
"6  c #363844",
"7  c #3A3D46",
"8  c #3B3E48",
"9  c #424347",
"0  c #47484C",
"q  c #434850",
"w  c #484B51",
"e  c #4F4F52",
"r  c #494D57",
"t  c #505255",
"y  c #545558",
"u  c #53565E",
"i  c #57595C",
"p  c #5B5D62",
"a  c #5D5E63",
"s  c #62656A",
"d  c #63666B",
"f  c #646669",
"g  c #66686D",
"h  c #616770",
"j  c #656B74",
"k  c #666A74",
"l  c #6B6E74",
"z  c #6D7076",
"x  c #717274",
"c  c #72747C",
"v  c #79797B",
"b  c #7D7D7D",
"n  c #787B82",
"m  c #7A7C84",
"M  c #808185",
"N  c #86878A",
"B  c #81848C",
"V  c #8C8C8D",
"C  c #919191",
"Z  c #989899",
"A  c #9B9B9B",
"S  c #9E9E9E",
"D  c #9EA4AF",
"F  c #A3A2A0",
"G  c #A3A3A3",
"H  c #A7A7AA",
"J  c #ACACAB",
"K  c #ADADB0",
"L  c #AEB0B3",
"P  c #AEB5BD",
"I  c #B2B3B5",
"U  c #B5B5B7",
"Y  c #B8B8B7",
"T  c #B4B5B8",
"R  c #B6B8BB",
"E  c #B8B8BB",
"W  c #BDBDBD",
"Q  c #BEBEBF",
"!  c #B5BAC1",
"~  c #BFC3C9",
"^  c #99D9EA",
"/  c #C1C0C0",
"(  c #C2C1C1",
")  c #C3C3C2",
"_  c #C3C3C3",
"`  c #C5C5C5",
"'  c #C6C6C6",
"]  c #C6C6C7",
"[  c #C4C8CB",
"{  c #C8C8C8",
"}  c #C9CACB",
"|  c #CBCDCF",
" . c #CCCCCC",
".. c #CECECE",
"X. c #C1C9D3",
"o. c #CCCED0",
"O. c #CCCED1",
"+. c #C7CED8",
"@. c #C8CFDA",
"#. c #CFD2D6",
"$. c #CCD3DD",
"%. c #D4D7DB",
"&. c #D5D8DD",
"*. c #D8D8D8",
"=. c #DADADA",
"-. c #DDDDDD",
";. c #D4DBE3",
":. c #DAE0E6",
">. c #DCE2E9",
",. c #DFE5ED",
"<. c #E1E6EC",
"1. c #E3E8EE",
"2. c #E9EBEC",
"3. c #EDEDED",
"4. c #E8ECF2",
"5. c #EEEFF0",
"6. c #EFF0F3",
"7. c #F3F3F4",
"8. c #F3F5F7",
"9. c #F5F7FA",
"0. c #FBFCFD",
"q. c #FDFEFF",
"^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ",
"^ &.U E E R E E E E E E E E E E E E E E E E R R ..^ ",
"^ ` ( ( _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ( _ ( ( ~ ^ ",
"^ ` ( ` _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ( ^ ",
"^ ] _ _ _ _ _ _ _ _ _ _ _ _ _ _ ) ( ) ) ) ) ) / W ^ ",
"^ ] ( _ _ _ _ _ _ _ _ _ _ _ _ _ (  .*.-.-.*.) ) ( ^ ",
"^ ] ( _ _ _ _ _ _ _ _ _ _ _ _ _ ..b         *.) ~ ^ ",
"^ ] ` ( _ _ _ _ _ _ _ _ _ _ _ _ ) ..W   X 3./ ) ( ^ ",
"^ ] _ _ _ _ _ _ _ _ _ _ _ _ _ _ ( _ | S E ` ` / / ^ ",
"^ ` ( _ _ _ _ _ _ _ _ _ _ _ _ _ _ / ( { ` ) ` ! / ^ ",
"^ ` ~ W ( ~ ( ( / W / ( ( ( ~ ( ( ~ ( ( ( ( ( ~ ! ^ ",
"^ %. . . .| o.o...#...o.#.o.|  .o.o. .o...o. .o.#.^ ",
"^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ [ i  .7.5.5.3.6.5.5.2.B H ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ R > [ q.0.0.0.q.0.q.8.r m ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ R ; ~ 9.6.6.6.6.6.6.3.r m ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ R = ! 4.,.<.<.<.<.4.:.q m ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ T @ P ,.;.:.:.:.;.,.;.8 c ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ T + D @.+.+.+.@.+.@.X.6 z ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ I @ p h d j j j h h d 1 l ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ L & < 3 5 5 7 7 7 3 < > j ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ K @ > v N w ` E ( d 4 & g ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ K . - l f & U F J a 2 # d ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ H   X d i @ F C A t : o p ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ O.e 0 v Z V S Z F x y 9 M ^ ^ ^ ^ ^ ^ ^ ",
"^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ "
]
_logo_pixmap = QtGui.QPixmap(_logo)