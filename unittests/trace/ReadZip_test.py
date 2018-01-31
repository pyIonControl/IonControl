import pytest
from trace.TraceCollection import TraceCollection

def test_load_zip():
    tc = TraceCollection()
    tc.loadTrace('GSTScanFromFile_048.zip')
