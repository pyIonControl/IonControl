# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5.Qsci import QsciScintilla, QsciLexerPython
from PyQt5.QtGui import QFont, QFontMetrics, QColor, QPixmap


class MyPythonLexer(QsciLexerPython):
    def __init__(self, parent=None, extraKeywords1=[], extraKeywords2=[]):
        """Initialize lexer with extra keywords set."""
        super(MyPythonLexer, self).__init__(parent)
        self.extraKeywords1 = extraKeywords1 #keywords to join to keyset 1
        self.extraKeywords2 = extraKeywords2 #keywords for keyset 2
        
    def keywords(self, keyset):
        """return standard keywords and extra keywords."""
        if keyset == 1:
            return ' '.join(self.extraKeywords1) + ' ' + QsciLexerPython.keywords(self, keyset)
        elif keyset == 2:
            return ' '.join(self.extraKeywords2)
        return QsciLexerPython.keywords(self, keyset)


class QPPPEditor(QsciScintilla):
    ARROW_MARKER_NUM = 8

    def __init__(self, parent=None, extraKeywords1=[], extraKeywords2=[]):
        super(QPPPEditor, self).__init__(parent)

        # Set the default font
        self.myfont = QFont()
        self.myfont.setFamily('Courier')
        self.myfont.setFixedPitch(True)
        self.myfont.setPointSize(10)
        self.setFont(self.myfont)
        self.setMarginsFont(self.myfont)
        
        self.myboldfont = QFont(self.myfont)
        self.myboldfont.setBold(True)

        # Margin 0 is used for line numbers
        fontmetrics = QFontMetrics(self.myfont)
        self.setMarginsFont(self.myfont)
        self.setMarginWidth(0, fontmetrics.width("00000") + 6)
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(QColor("#cccccc"))

        # Clickable margin 1 for showing markers
        self.setMarginSensitivity(1, True)
        self.marginClicked.connect(self.on_margin_clicked)
        self.markerDefine(QsciScintilla.RightArrow, self.ARROW_MARKER_NUM)
        self.setMarkerBackgroundColor(QColor("#ee1111"), self.ARROW_MARKER_NUM)

        # Brace matching: enable for a brace immediately before or after
        # the current position
        #
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)

        # Current line visible with special background color
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#ffe4e4"))

        # Set Python lexer
        # Set style for Python comments (style number 1) to a fixed-width
        # courier.
        #
        lexer = MyPythonLexer(extraKeywords1=extraKeywords1, extraKeywords2=extraKeywords2)
        lexer.setDefaultFont(self.myfont)
        #lexer.setColor( QColor('red'), lexer.SingleQuotedString )
        lexer.setFont( self.myboldfont, lexer.Keyword)
        lexer.setFont( self.myboldfont, lexer.HighlightedIdentifier )
        lexer.setColor( QColor('blue'), lexer.HighlightedIdentifier )
        self.setLexer(lexer)
        #TODO self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, 1, 'Courier')

        # Don't want to see the horizontal scrollbar at all
        # Use raw message to Scintilla here (all messages are documented
        # here: http://www.scintilla.org/ScintillaDoc.html)
        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 0)
        
        self.setIndentationWidth(4)
        self.setIndentationsUseTabs(False)
        self.setTabIndents(True)
        self.setIndentationGuides(True)
        #self.SendScintilla(QsciScintilla.SCI_SETINDENTATIONGUIDES, QsciScintilla.SC_IV_LOOKFORWARD )
        self.setEolMode(self.EolUnix)

        # not too small
        self.setMinimumSize(200, 100)
        self.errorIndicators = list()
        pixmap = QPixmap('ui/icons/hg-16.png')
        self.timingMarker = self.markerDefine(pixmap)

    def on_margin_clicked(self, nmargin, nline, modifiers):
        # Toggle marker for the line the margin was clicked on
        if self.markersAtLine(nline) != 0:
            self.markerDelete(nline, self.ARROW_MARKER_NUM)
        else:
            self.markerAdd(nline, self.ARROW_MARKER_NUM)

    def setPlainText(self, text ):
        self.setText(text)
        
    def toPlainText(self):
        return self.text()
    
    def cursorPosition(self):
        return self.getCursorPosition()
    
    def scrollPosition(self):
        return self.firstVisibleLine()
    
    def setScrollPosition(self, line):
        self.setFirstVisibleLine(line)
    
    def highlightError(self, line, col, toline, tocol):
        tocolumn = self.lineLength(toline-1) if tocol<0 else tocol
        fromcol = col-1 if col else 0
        self.fillIndicatorRange(line-1, fromcol, toline-1, tocolumn, 2)
        self.errorIndicators.append( (line-1, fromcol, toline-1, tocolumn) )
    
    def clearError(self):
#         for line, col, toline, tocol in self.errorIndicators:
#             self.clearIndicatorRange(line, col, toline, tocol, 2)
        toline = self.lines()-1
        col = self.lineLength(toline-1)
        self.clearIndicatorRange(0, 0, toline, col, 2 )
        self.errorIndicators = list()
        
    def highlightTimingViolation(self, linelist):
        if linelist:
            for line in linelist:
                self.markerAdd(line, self.timingMarker)
        else:    
            self.markerDeleteAll(self.timingMarker)
            
        
