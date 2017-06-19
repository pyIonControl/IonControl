"""
Created on 27 Jun 2016 at 4:24 PM

@author: monroelab
"""

from visa import ResourceManager

instrument = ResourceManager().open_resource('PTS3500')
instrument.write("F1000000000\\nA1\\n")
while True:
    if input('break? y/n > ') == 'y':
        break
instrument.close()
del instrument