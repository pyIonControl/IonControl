# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import runpy
from pathlib import Path
from expressionFunctions.UserFitFunctions import fitfunc
from expressionFunctions.ExprFuncDecorator import userfunc

def userFuncLoader(ParentPath):
    logger = logging.getLogger(__name__)
    ppath = Path(ParentPath)
    if ppath.exists():
        if ppath.is_dir():
            for path in ppath.iterdir():
                userFuncLoader(path)
        elif ppath.suffix == '.py':
            try:
                globs = {'fitfunc': fitfunc, 'userfunc': userfunc}
                runpy.run_path(str(ppath), globs)
            except SyntaxError as e:
                logger.error('Failed to load {0}, because {1}'.format(str(ppath), e))

