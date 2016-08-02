# -*- coding: utf-8 -*-
"""
Created on Wed May 22 06:53:20 2013

@author: wolverine
"""

RedProgressBar = """
QProgressBar {
border: 1px solid black;
text-align: center;
padding: 1px;
border-top-left-radius: 3px;
border-bottom-left-radius: 3px;
border-top-right-radius: 3px;
border-bottom-right-radius: 3px;
background: QLinearGradient( x1: 0, y1: 0, x2: 0, y2:1,
stop: 0 #fff,
stop: 0.4999 #eee,
stop: 0.5 #ddd,
stop: 1 #eee );
width: 15px;
height: 17px;
margin-right: 12ex;
}

QProgressBar::chunk {
background: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1,
stop: 0 #dd0000,
stop: 0.4999 #ba0000,
stop: 0.5 #aa0000,
stop: 1 #880000 );
border-top-left-radius: 3px;
border-bottom-left-radius: 3px;
border-top-right-radius: 3px;
border-bottom-right-radius: 3px;
border: 1px solid black;
}"""
