#!/usr/bin/python3

import os
import sys

# Add the current directory to the path
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_dir)

from vc6proxy import LinkExe

def main():
    """
    Proxy script for LINK.EXE (linker)
    This script acts as a proxy between CMake and the Visual C++ 6.0 linker running in Wine.
    """
    # Get all arguments passed to this script
    args = sys.argv[1:]
    
    # Create a linker instance
    linker = LinkExe()
    
    # Run the linker with the arguments
    return_code = linker.link(args)
    
    # Return the linker's exit code
    sys.exit(return_code)

if __name__ == "__main__":
    main()