#!/usr/bin/python3

import os
import sys

# Add the current directory to the path
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_dir)

from vc6proxy import LibExe

def main():
    """
    Proxy script for LIB.EXE (linker)
    This script acts as a proxy between CMake and the Visual C++ 6.0 library manager running in Wine.
    """
    # Get all arguments passed to this script
    args = sys.argv[1:]
    
    # Create a linker instance
    libexe = LibExe()
    
    # Run the linker with the arguments
    return_code = libexe.create_lib(args)
    
    # Return the linker's exit code
    sys.exit(return_code)

if __name__ == "__main__":
    main()
