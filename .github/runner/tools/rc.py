#!/usr/bin/python3

import os
import sys

# Add the current directory to the path
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_dir)

from vc6proxy import RcCompiler

def main():
    """
    Proxy script for RC.EXE 
    This script acts as a proxy between CMake and the Visual C++ 6.0 RC running in Wine.
    """
    # Get all arguments passed to this script
    args = sys.argv[1:]
    
    # Create a MIDL compiler instance
    rccomp = RcCompiler()
    
    # Run the MIDL compiler with the arguments
    return_code = rccomp.compile(args)
    
    # Return the compiler's exit code
    sys.exit(return_code)

if __name__ == "__main__":
    main()