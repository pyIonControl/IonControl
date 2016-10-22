#
#       This file demonstrates how to make user-defined functions. All user-defined functions must be decorated
#       by @userfunc in order to be recognized in an expression field. Any function that is decorated by @userfunc
#       that shows up in a .py file in the UserFunctions directory (or any subdirectory therein) will be immediately
#       accessible in an expression field once the file is saved.  The Evaluation Tests windowbelow is simply for
#       testing functions during development.

# functions that are not decorated with @userfunc won't be accessible in expression fields,
# but they can be used to build up more complicated user functions

def reciprocal(x):
    return 1/x

@userfunc
def root(x, n=2):
    """Example of a user-defined function that takes the nth root
     (determined by n) of a number, x. Defaults to a square root."""
    return x**reciprocal(n)

# User function doc strings are automatically added to the documentation window. Right clicking
# on a user function's name or doc string from the documentation window provides a shortcut to
# the user function source code.


