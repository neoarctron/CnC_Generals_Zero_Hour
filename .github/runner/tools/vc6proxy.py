#!/usr/bin/python3

import os
import sys
import subprocess
import tempfile
import re
import shutil
import platform
import io
import traceback
from pathlib import Path
from contextlib import contextmanager

# Global variables
VERBOSE = os.environ.get('VC6_VERBOSE', '0').lower() in ('1', 'true', 'yes')
log_buffer = io.StringIO()
last_command_successful = True

# Constants
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
IS_WINDOWS = platform.system() == "Windows"

def log(message, error=False):
    """Log a message to the buffer, immediately print if error or verbose mode."""
    global last_command_successful
    
    if error:
        last_command_successful = False
        print(message, file=sys.stderr)
    
    log_buffer.write(f"{message}\n")
    
    if VERBOSE:
        print(message)

def flush_logs_if_error():
    """Print all collected logs if there was an error."""
    global last_command_successful
    
    if not last_command_successful:
        print("\n----- Debug logs from build process -----")
        print(log_buffer.getvalue())
        print("-----------------------------------------")
        
    # Reset the buffer and success flag
    log_buffer.truncate(0)
    log_buffer.seek(0)
    last_command_successful = True

@contextmanager
def log_group(title):
    """Create a log group with a title and separator lines."""
    log(f"\n----- {title} -----")
    try:
        yield
    finally:
        log("---------------------------")

def unix_to_wine(path):
    """Convert a Unix path to a Wine-compatible path."""
    if IS_WINDOWS:
        return path

    if os.path.isabs(path): 
        return "Z:" + path.replace("/", "\\")
    return path

def wine_to_unix(path):
    """Convert a Wine path to a Unix-compatible path."""
    if IS_WINDOWS:
        return path
    
    if re.match(r'^[A-Za-z]:', path):
        drive_letter = path[0]
        if drive_letter.lower() == 'z':
            return path[2:].replace("\\", "/")
        else:
            drive_path = path[2:].replace('\\', '/')
            return "/mnt/{0}{1}".format(drive_letter.lower(), drive_path)
    
    return path.replace("\\", "/")

def run_command_with_wine(cmd, env=None, cwd=None):
    """Run a command with Wine, handling the environment and working directory."""
    if IS_WINDOWS:
        process = subprocess.Popen(
            cmd, 
            env=env, 
            cwd=cwd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        )
    else:
        wine_cmd = ['wine'] + cmd
        process = subprocess.Popen(
            wine_cmd, 
            env=env, 
            cwd=cwd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
    
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        log(f"Command failed with return code {process.returncode}", error=True)
        if stdout:
            log("STDOUT:", error=True)
            log(stdout, error=True)
        if stderr:
            log("STDERR:", error=True)
            log(stderr, error=True)
    
    return process.returncode, stdout, stderr

def create_batch_file(commands):
    """Create a temporary batch file with the given commands."""
    fd, path = tempfile.mkstemp(suffix='.bat')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write("@echo off\r\n")
            
            if not IS_WINDOWS:
                setup_path = unix_to_wine(os.path.join(SCRIPT_DIR, 'setup.bat'))
                f.write("call {0}\r\n".format(setup_path))
                
            for cmd in commands:
                f.write("{0}\r\n".format(cmd))
        
        log(f"Created batch file: {path}")
        with open(path, 'r') as f:
            batch_contents = f.read()
            log("Batch contents:")
            for line in batch_contents.splitlines():
                log(f"  {line}")
        
        return path
    except Exception as e:
        log(f"Error creating batch file: {str(e)}", error=True)
        traceback.print_exc(file=log_buffer)
        if os.path.exists(path):
            os.unlink(path)
        raise

class ProxyCompiler:
    """Base class for proxy compilers."""
    def __init__(self, env=None):
        self.env = env or os.environ.copy()
    
    def _run_batch(self, commands):
        """Run a batch file with the specified commands."""
        batch_path = None
        try:
            batch_path = create_batch_file(commands)
            
            if IS_WINDOWS:
                cmd = [batch_path]
            else:
                cmd = ["cmd", "/c", unix_to_wine(batch_path)]
            
            with log_group("Executing batch command"):
                log(f"Command: {' '.join(cmd)}")
            
            returncode, stdout, stderr = run_command_with_wine(cmd, env=self.env)
            
            with log_group("Command output"):
                if stdout:
                    log(stdout)
                if stderr:
                    if returncode != 0:
                        # If error, print stderr directly and log it
                        print(stderr, file=sys.stderr)
                    log(stderr)
            
            # If return code is non-zero, mark as error
            if returncode != 0:
                log(f"Command failed with return code {returncode}", error=True)
                flush_logs_if_error()
            
            return returncode
        except Exception as e:
            log(f"Error executing batch command: {str(e)}", error=True)
            traceback.print_exc(file=log_buffer)
            flush_logs_if_error()
            return 1
        finally:
            if batch_path and os.path.exists(batch_path):
                os.unlink(batch_path)

class CLCompiler(ProxyCompiler):
    """Proxy for Microsoft CL compiler."""
    def __init__(self, env=None):
        super().__init__(env)

    def compile(self, args):
        """Compile a file using CL.EXE."""
        log("Original args: " + str(args))
        
        include_dirs = []
        define_macros = []
        compiler_flags = []
        source_files = []
        output_opts = {}
        compile_only = False
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if (arg.startswith('-I') or arg.startswith('/I')) and len(arg) > 2:
                include_dirs.append(arg[2:])
                i += 1
            elif (arg == '-I' or arg == '/I') and i + 1 < len(args):
                include_dirs.append(args[i+1])
                i += 2
                
            elif (arg.startswith('-D') or arg.startswith('/D')) and len(arg) > 2:
                define_macros.append(arg[2:])
                i += 1
            elif (arg == '-D' or arg == '/D') and i + 1 < len(args):
                define_macros.append(args[i+1])
                i += 2
                
            elif arg.startswith('/Fo') and len(arg) > 3:
                output_opts['Fo'] = arg[3:]
                i += 1
            elif arg == '/Fo' and i + 1 < len(args):
                output_opts['Fo'] = args[i+1]
                i += 2
                
            elif arg.startswith('/Fd') and len(arg) > 3:
                output_opts['Fd'] = arg[3:]
                i += 1
            elif arg == '/Fd' and i + 1 < len(args):
                output_opts['Fd'] = args[i+1]
                i += 2
                
            elif arg == '-c' or arg == '/c':
                compile_only = True
                i += 1
                
            elif arg.endswith(('.c', '.cpp', '.cxx', '.cc', '.C', '.CPP', '.CXX', '.CC')):
                log(f"Found potential source file: {arg}")
                if os.path.exists(arg):
                    source_files.append(arg)
                else:
                    if '/' in arg or '\\' in arg:
                        source_files.append(arg)
                i += 1
                
            elif arg.startswith('-M'):
                compiler_flags.append('/' + arg[1:])
                i += 1
                
            elif arg.startswith('/'):
                if arg == '/nologo' and '/nologo' in compiler_flags:
                    i += 1
                    continue
                elif arg.startswith('/Ob'):
                    i += 1
                    continue
                else:
                    compiler_flags.append(arg)
                    i += 1
                    
            elif os.path.exists(arg) and arg.endswith(('.c', '.cpp', '.cxx', '.cc')):
                source_files.append(arg)
                i += 1
                
            elif arg.startswith('-'):
                i += 1
                
            else:
                compiler_flags.append(arg)
                i += 1
                
        if len(source_files) == 0 and len(args) > 0 and os.path.exists(args[-1]) and args[-1].endswith(('.c', '.cpp', '.cxx', '.cc')):
            source_files.append(args[-1])
            
        log("Found include dirs: " + str(include_dirs))
        log("Found define macros: " + str(define_macros))
        
        cl_args = ['/nologo']
        
        if compile_only:
            cl_args.append('/c')
            
        for dir in include_dirs:
            if os.path.exists(dir):
                wine_dir = unix_to_wine(dir)
                if ' ' in wine_dir:
                    cl_args.append(f'/I"{wine_dir}"')
                else:
                    cl_args.append(f'/I{wine_dir}')
            else:
                if ' ' in dir:
                    cl_args.append(f'/I"{dir}"')
                else:
                    cl_args.append(f'/I{dir}')
                    
        for macro in define_macros:
            if '"' in macro and '=' in macro:
                name, value = macro.split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                    cl_args.append(f'/D{name}=\\"{value}\\"')
                else:
                    cl_args.append(f'/D{macro}')
            else:
                cl_args.append(f'/D{macro}')
                
        for flag in compiler_flags:
            if flag != '/nologo':
                cl_args.append(flag)

        for src in source_files:
            log(f"Processing source file: {src}")
            if src.startswith('/'):
                wine_src = "Z:" + src
            elif os.path.exists(src):
                wine_src = unix_to_wine(src)
            else:
                wine_src = src
                
            if ' ' in wine_src:
                cl_args.append(f'"{wine_src}"')
            else:
                cl_args.append(wine_src)
                    
        if 'Fo' in output_opts:
            wine_output = unix_to_wine(output_opts['Fo'])
            if ' ' in wine_output:
                cl_args.append(f'/Fo"{wine_output}"')
            else:
                cl_args.append(f'/Fo{wine_output}')
                
        if 'Fd' in output_opts:
            wine_pdb = unix_to_wine(output_opts['Fd'])
            if ' ' in wine_pdb:
                cl_args.append(f'/Fd"{wine_pdb}"')
            else:
                cl_args.append(f'/Fd{wine_pdb}')
                
        cl_cmd = "CL.EXE {0}".format(' '.join(cl_args))
        
        log("Executing: " + cl_cmd)
        
        result = self._run_batch([cl_cmd])
        flush_logs_if_error()
        return result

class LibExe(ProxyCompiler):
    """Proxy for Microsoft LIB.EXE (Library Manager)."""
    def __init__(self, env=None):
        super().__init__(env)
        
    def create_lib(self, args):
        """Create a static library using LIB.EXE."""
        log("Original LIB args: " + str(args))
        
        out_file = None
        response_files = []
        obj_files = []
        other_args = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg.startswith('@'):
                response_files.append(arg[1:])
                i += 1
            elif arg.startswith('/out:'):
                out_file = arg[5:]
                i += 1
            elif arg == '/out:' and i + 1 < len(args):
                out_file = args[i+1]
                i += 2
            elif arg.endswith('.obj'):
                obj_files.append(arg)
                i += 1
            else:
                if arg != '/LIB':
                    other_args.append(arg)
                i += 1
        
        wine_args = []
        wine_args.extend(other_args)
        
        for resp_file in response_files:
            if os.path.exists(resp_file):
                wine_resp = unix_to_wine(resp_file)
                wine_args.append(f'@{wine_resp}')
            else:
                current_dir = os.getcwd()
                rel_path = os.path.normpath(os.path.join(current_dir, resp_file))
                if os.path.exists(rel_path):
                    wine_resp = unix_to_wine(rel_path)
                    wine_args.append(f'@{wine_resp}')
                else:
                    wine_args.append(f'@{resp_file}')
                    log(f"Warning: Response file {resp_file} not found, passing as-is")
        
        for obj_file in obj_files:
            if os.path.exists(obj_file):
                wine_obj = unix_to_wine(obj_file)
                wine_args.append(wine_obj)
            else:
                wine_args.append(obj_file)
        
        if out_file:
            if out_file.startswith('..'):
                current_dir = os.getcwd()
                abs_path = os.path.normpath(os.path.join(current_dir, out_file))
                output_dir = os.path.dirname(abs_path)
                if os.path.exists(output_dir):
                    wine_out = unix_to_wine(abs_path)
                    wine_args.append(f'/out:{wine_out}')
                else:
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                        wine_out = unix_to_wine(abs_path)
                        wine_args.append(f'/out:{wine_out}')
                    except:
                        wine_args.append(f'/out:{out_file}')
                        log(f"Warning: Output directory for {out_file} doesn't exist and couldn't be created")
            elif os.path.isabs(out_file) and os.path.exists(os.path.dirname(out_file)):
                wine_out = unix_to_wine(out_file)
                wine_args.append(f'/out:{wine_out}')
            else:
                wine_args.append(f'/out:{out_file}')
    
        log("Processed LIB args: " + str(wine_args))
        
        lib_args = []
        for arg in wine_args:
            if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                if arg.startswith('/out:'):
                    path = arg[5:]
                    lib_args.append(f'/out:"{path}"')
                elif arg.startswith('@'):
                    path = arg[1:]
                    lib_args.append(f'@"{path}"')
                else:
                    lib_args.append(f'"{arg}"')
            else:
                lib_args.append(arg)
                
        lib_cmd = "LIB.EXE {0}".format(' '.join(lib_args))
        
        log("Executing: " + lib_cmd)
        
        result = self._run_batch([lib_cmd])
        flush_logs_if_error()
        return result

class LinkExe(ProxyCompiler):
    """Proxy for Microsoft LINK.EXE."""
    def __init__(self, env=None):
        super().__init__(env)

    def process_response_file(self, resp_file):
        """Process a response file to convert all paths inside to Wine format."""
        try:
            with open(resp_file, 'r') as f:
                lines = f.readlines()
            
            fd, temp_path = tempfile.mkstemp(suffix='.rsp')
            
            log(f"Processing response file: {resp_file}")
            log(f"Creating temporary response file: {temp_path}")
            
            with os.fdopen(fd, 'w') as f:
                for line in lines:
                    line = line.strip()
                    if line:
                        log(f"  Processing line: {line}")
                        if os.path.exists(line) or (line.startswith('/') and len(line) > 1):
                            wine_path = unix_to_wine(line)
                            log(f"  Converted path: {line} -> {wine_path}")
                            f.write(f"{wine_path}\n")
                        else:
                            log(f"  Keeping line as is: {line}")
                            f.write(f"{line}\n")
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                log(f"Successfully created response file: {temp_path}")
                with open(temp_path, 'r') as f:
                    log("Response file content:")
                    for line in f:
                        log(f"  {line.strip()}")
            else:
                log(f"Warning: Created response file {temp_path} is empty or missing")
                return resp_file
            
            return temp_path
        except Exception as e:
            log(f"Warning: Failed to process response file {resp_file}: {str(e)}")
            traceback.print_exc(file=log_buffer)
            return resp_file

    def link(self, args):
        """Link files using LINK.EXE or create a library using LIB.EXE."""
        log("Original link args: " + str(args))
        
        is_static_lib = False
        out_file = None
        
        for i, arg in enumerate(args):
            if arg.startswith('/out:'):
                out_file = arg[5:]
                if out_file.endswith('.lib'):
                    is_static_lib = True
                break
            elif arg == '/out:' and i + 1 < len(args):
                out_file = args[i+1]
                if out_file.endswith('.lib'):
                    is_static_lib = True
                break
        
        if '/LIB' in args:
            is_static_lib = True
        
        if is_static_lib:
            log("Creating static library, using LIB.EXE instead of LINK.EXE")
            lib_tool = LibExe(self.env)
            return lib_tool.create_lib(args)
        
        implib_file = None
        pdb_file = None
        response_files = []
        obj_files = []
        lib_files = []
        lib_paths = []
        linker_directives = []
        other_args = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg.startswith('@'):
                response_files.append(arg[1:])
                i += 1
            elif arg.startswith('/out:'):
                out_file = arg[5:]
                if os.path.isabs(out_file):
                    wine_out = unix_to_wine(out_file)
                    log(f"Converting output path: {out_file} -> {wine_out}")
                    other_args.append(f'/out:{wine_out}')
                else:
                    other_args.append(arg)
                i += 1
            elif arg.startswith('/implib:'):
                implib_file = arg[8:]
                if os.path.isabs(implib_file):
                    wine_implib = unix_to_wine(implib_file)
                    log(f"Converting implib path: {implib_file} -> {wine_implib}")
                    other_args.append(f'/implib:{wine_implib}')
                else:
                    other_args.append(arg)
                i += 1
            elif arg.startswith('/pdb:'):
                pdb_file = arg[5:]
                if os.path.isabs(pdb_file):
                    wine_pdb = unix_to_wine(pdb_file)
                    log(f"Converting PDB path: {pdb_file} -> {wine_pdb}")
                    other_args.append(f'/pdb:{wine_pdb}')
                else:
                    other_args.append(arg)
                i += 1
            elif arg == '/out:' and i + 1 < len(args):
                out_file = args[i+1]
                other_args.append(arg)
                if os.path.isabs(out_file):
                    wine_out = unix_to_wine(out_file)
                    log(f"Converting output path: {out_file} -> {wine_out}")
                    other_args.append(wine_out)
                else:
                    other_args.append(args[i+1])
                i += 2
            elif arg == '/implib:' and i + 1 < len(args):
                implib_file = args[i+1]
                other_args.append(arg)
                if os.path.isabs(implib_file):
                    wine_implib = unix_to_wine(implib_file)
                    print(f"Converting implib path: {implib_file} -> {wine_implib}")
                    other_args.append(wine_implib)
                else:
                    other_args.append(args[i+1])
                i += 2
            elif arg == '/pdb:' and i + 1 < len(args):
                pdb_file = args[i+1]
                other_args.append(arg)
                if os.path.isabs(pdb_file):
                    wine_pdb = unix_to_wine(pdb_file)
                    print(f"Converting PDB path: {pdb_file} -> {wine_pdb}")
                    other_args.append(wine_pdb)
                else:
                    other_args.append(args[i+1])
                i += 2
            elif arg.upper().startswith('/NODEFAULTLIB:') or arg.upper().startswith('/DEFAULTLIB:') or \
                 arg.upper().startswith('/FORCE:') or arg.upper().startswith('/STACK:') or \
                 arg.upper().startswith('/HEAP:') or arg.upper().startswith('/BASE:'):
                linker_directives.append(arg)
                i += 1
            elif arg.startswith('-LIBPATH:') or arg.startswith('/LIBPATH:'):
                if arg.startswith('-LIBPATH:'):
                    path = arg[9:]
                    lib_paths.append(('/LIBPATH:', path))
                else:
                    path = arg[9:]
                    lib_paths.append(('/LIBPATH:', path))
                i += 1
            elif arg.endswith('.obj'):
                obj_files.append(arg)
                i += 1
            elif arg.endswith('.lib') and not (arg.startswith('/') or arg.startswith('-')):
                lib_files.append(arg)
                i += 1
            elif arg == '/LIB':
                i += 1
            else:
                other_args.append(arg)
                i += 1
        
        wine_args = other_args.copy()
        wine_args.extend(linker_directives)
        
        for directive, path in lib_paths:
            if os.path.exists(path):
                wine_path = unix_to_wine(path)
                wine_args.append(f'{directive}{wine_path}')
            else:
                if path.startswith('/'):
                    wine_args.append(f'{directive}Z:{path}')
                else:
                    wine_args.append(f'{directive}{path}')
        
        for resp_file in response_files:
            if os.path.exists(resp_file):
                processed_resp = self.process_response_file(resp_file)
                wine_resp = unix_to_wine(processed_resp)
                wine_args.append(f'@{wine_resp}')
            else:
                current_dir = os.getcwd()
                rel_path = os.path.normpath(os.path.join(current_dir, resp_file))
                if os.path.exists(rel_path):
                    processed_resp = self.process_response_file(rel_path)
                    wine_resp = unix_to_wine(processed_resp)
                    wine_args.append(f'@{wine_resp}')
                else:
                    wine_args.append(f'@{resp_file}')
                    log(f"Warning: Response file {resp_file} not found, passing as-is")
        
        for obj_file in obj_files:
            if os.path.exists(obj_file):
                wine_obj = unix_to_wine(obj_file)
                wine_args.append(wine_obj)
            else:
                if obj_file.startswith('/'):
                    wine_args.append(f'Z:{obj_file}')
                else:
                    wine_args.append(obj_file)
        
        for lib_file in lib_files:
            if os.path.exists(lib_file):
                wine_lib = unix_to_wine(lib_file)
                wine_args.append(wine_lib)
            else:
                wine_args.append(lib_file)
                log(f"Treating {lib_file} as system library (file not found)")
        
        log("Processed link args: " + str(wine_args))
        
        link_args = []
        for arg in wine_args:
            if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                if arg.startswith('/out:'):
                    path = arg[5:]
                    link_args.append(f'/out:"{path}"')
                elif arg.startswith('/implib:'):
                    path = arg[8:]
                    link_args.append(f'/implib:"{path}"')
                elif arg.startswith('/pdb:'):
                    path = arg[5:]
                    link_args.append(f'/pdb:"{path}"')
                elif arg.startswith('/LIBPATH:'):
                    path = arg[9:]
                    link_args.append(f'/LIBPATH:"{path}"')
                elif arg.startswith('@'):
                    path = arg[1:]
                    link_args.append(f'@"{path}"')
                else:
                    link_args.append(f'"{arg}"')
            else:
                link_args.append(arg)
                
        link_cmd = "LINK.EXE {0}".format(' '.join(link_args))
        
        log("Executing: " + link_cmd)
        
        result = self._run_batch([link_cmd])
        flush_logs_if_error()
        return result

class MidlCompiler(ProxyCompiler):
    """Proxy for Microsoft MIDL.EXE."""
    def __init__(self, env=None):
        super().__init__(env)
        
    def compile(self, args):
        """Compile an IDL file using MIDL.EXE."""
        log("Original MIDL args: " + str(args))
        
        idl_file = None
        output_files = {}
        include_dirs = []
        other_args = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg in ['/h', '/header', '/iid', '/acf', '/out', '/cstub', '/dlldata', 
                      '/proxy', '/sstub', '/tlb', '/prefix'] and i + 1 < len(args):
                opt_key = arg[1:] if arg.startswith('/') else arg
                if opt_key == 'header':
                    opt_key = 'h'
                output_files[opt_key] = args[i+1]
                i += 2
            elif arg.startswith('/I') and len(arg) > 2:
                include_dir = arg[2:]
                include_dirs.append(include_dir)
                i += 1
            elif arg == '/I' and i + 1 < len(args):
                include_dirs.append(args[i+1])
                i += 2
            elif arg.startswith('-I') and len(arg) > 2:
                include_dir = arg[2:]
                include_dirs.append(include_dir)
                i += 1
            elif arg == '-I' and i + 1 < len(args):
                include_dirs.append(args[i+1])
                i += 2
            elif arg.endswith('.idl'):
                idl_file = arg
                i += 1
            else:
                other_args.append(arg)
                i += 1
                
        if not idl_file and len(other_args) > 0:
            potential_idl = other_args[-1]
            if '.' in potential_idl and not potential_idl.startswith('/') and not potential_idl.startswith('-'):
                idl_file = potential_idl
                other_args.pop()
        
        wine_args = []
        
        for include_dir in include_dirs:
            if os.path.exists(include_dir):
                wine_include = unix_to_wine(include_dir)
                wine_args.append(f'/I{wine_include}')
            else:
                wine_args.append(f'/I{include_dir}')
        
        for arg in other_args:
            if arg.startswith('/') and '/' in arg[1:] and not os.path.exists(arg) and not arg[1:].split('/')[0] in ['W', 'Oicf', 'env', 'error', 'ms_ext', 'c_ext', 'robust']:
                log(f"Warning: Skipping argument that looks like a Unix path: {arg}")
                continue
            wine_args.append(arg)
        
        for opt, filename in output_files.items():
            output_dir = os.path.dirname(filename)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    log(f"Created directory: {output_dir}")
                except Exception as e:
                    log(f"Warning: Failed to create directory {output_dir}: {str(e)}")
            
            if not output_dir or os.path.exists(output_dir):
                wine_path = unix_to_wine(filename)
                wine_args.append(f'/{opt}')
                wine_args.append(wine_path)
            else:
                wine_args.append(f'/{opt}')
                wine_args.append(filename)
        
        if idl_file:
            fixed_path = idl_file.replace('\\', '/')
            
            if os.path.exists(fixed_path):
                wine_idl = unix_to_wine(fixed_path)
                wine_args.append(wine_idl)
            elif '/' in fixed_path:
                current_dir = os.getcwd()
                normalized_path = os.path.normpath(os.path.join(current_dir, fixed_path))
                
                if os.path.exists(normalized_path):
                    wine_idl = unix_to_wine(normalized_path)
                    wine_args.append(wine_idl)
                else:
                    path_parts = fixed_path.split('/')
                    if path_parts and path_parts[-1] and '\\' in path_parts[-1]:
                        last_part = path_parts[-1].replace('\\', '/')
                        fixed_path = '/'.join(path_parts[:-1] + [last_part])
                        
                        if os.path.exists(fixed_path):
                            wine_idl = unix_to_wine(fixed_path)
                            wine_args.append(wine_idl)
                        else:
                            fixed_path = 'Z:' + fixed_path if fixed_path.startswith('/') else fixed_path
                            wine_args.append(fixed_path.replace('/', '\\'))
                            log(f"Warning: IDL file {idl_file} not found, using best-guess conversion")
                    else:
                        fixed_path = 'Z:' + fixed_path if fixed_path.startswith('/') else fixed_path
                        wine_args.append(fixed_path.replace('/', '\\'))
                        print(f"Warning: IDL file {idl_file} not found, using best-guess conversion")
            else:
                wine_args.append(idl_file)
        else:
            log("Warning: No IDL file was identified in the arguments")
        
        log("Processed MIDL args: " + str(wine_args))
        
        midl_args = []
        for arg in wine_args:
            if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                if arg.startswith('/I'):
                    include_path = arg[2:]
                    midl_args.append(f'/I"{include_path}"')
                else:
                    midl_args.append(f'"{arg}"')
            else:
                midl_args.append(arg)
                
        midl_cmd = "MIDL.EXE {0}".format(' '.join(midl_args))
        
        log("Executing: " + midl_cmd)
        
        result = self._run_batch([midl_cmd])
        flush_logs_if_error()
        return result

class RcCompiler(ProxyCompiler):
    """Proxy for Microsoft RC.EXE (Resource Compiler)."""
    def __init__(self, env=None):
        super().__init__(env)
        
    def compile(self, args):
        """Compile a resource file using RC.EXE."""
        log("Original RC args: " + str(args))
        
        rc_file = None
        output_file = None
        include_dirs = []
        defines = []
        undefines = []
        other_args = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg.startswith('/fo') or arg.startswith('-fo'):
                if len(arg) > 3:
                    output_file = arg[3:]
                    i += 1
                elif i + 1 < len(args):
                    output_file = args[i+1]
                    i += 2
                else:
                    other_args.append(arg)
                    i += 1
            
            elif arg.startswith('/i') or arg.startswith('-i'):
                if len(arg) > 2:
                    include_dir = arg[2:]
                    include_dirs.append(include_dir)
                    i += 1
                elif i + 1 < len(args):
                    include_dirs.append(args[i+1])
                    i += 2
                else:
                    other_args.append(arg)
                    i += 1
            
            elif arg.startswith('/d') or arg.startswith('-d'):
                if len(arg) > 2:
                    define = arg[2:]
                    defines.append(define)
                    i += 1
                elif i + 1 < len(args):
                    defines.append(args[i+1])
                    i += 2
                else:
                    other_args.append(arg)
                    i += 1
            
            elif arg.startswith('/u') or arg.startswith('-u'):
                if len(arg) > 2:
                    undefine = arg[2:]
                    undefines.append(undefine)
                    i += 1
                elif i + 1 < len(args):
                    undefines.append(args[i+1])
                    i += 2
                else:
                    other_args.append(arg)
                    i += 1
            
            elif arg in ['/l', '-l', '/c', '-c'] and i + 1 < len(args):
                other_args.append(arg)
                other_args.append(args[i+1])
                i += 2
            
            elif arg in ['/r', '-r', '/v', '-v', '/x', '-x', '/w', '-w', '/n', '-n']:
                other_args.append(arg)
                i += 1
            
            elif i == len(args) - 1 and (arg.endswith('.rc') or arg.endswith('.RC')):
                rc_file = arg
                i += 1
            
            else:
                if (arg.endswith('.rc') or arg.endswith('.RC')) and not rc_file:
                    rc_file = arg
                else:
                    other_args.append(arg)
                i += 1
        
        wine_args = []
        wine_args.extend(other_args)
        
        for define in defines:
            wine_args.append(f'/d{define}')
        
        for undefine in undefines:
            wine_args.append(f'/u{undefine}')
        
        for include_dir in include_dirs:
            if os.path.exists(include_dir):
                wine_include = unix_to_wine(include_dir)
                wine_args.append(f'/i{wine_include}')
            else:
                wine_args.append(f'/i{include_dir}')
        
        if output_file:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    log(f"Created directory: {output_dir}")
                except Exception as e:
                    log(f"Warning: Failed to create directory {output_dir}: {str(e)}")
            
            if not output_dir or os.path.exists(output_dir):
                wine_output = unix_to_wine(output_file)
                wine_args.append(f'/fo{wine_output}')
            else:
                wine_args.append(f'/fo{output_file}')
        
        if rc_file:
            if os.path.exists(rc_file):
                wine_rc = unix_to_wine(rc_file)
                wine_args.append(wine_rc)
            else:
                current_dir = os.getcwd()
                normalized_path = os.path.normpath(os.path.join(current_dir, rc_file))
                
                if os.path.exists(normalized_path):
                    wine_rc = unix_to_wine(normalized_path)
                    wine_args.append(wine_rc)
                else:
                    wine_args.append(rc_file)
                    log(f"Warning: RC file {rc_file} not found, passing as-is")
        
        log("Processed RC args: " + str(wine_args))
        
        rc_args = []
        for arg in wine_args:
            if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                if arg.startswith('/fo'):
                    path = arg[3:]
                    rc_args.append(f'/fo"{path}"')
                elif arg.startswith('/i'):
                    path = arg[2:]
                    rc_args.append(f'/i"{path}"')
                else:
                    rc_args.append(f'"{arg}"')
            else:
                rc_args.append(arg)
                
        rc_cmd = "RC.EXE {0}".format(' '.join(rc_args))
        
        log("Executing: " + rc_cmd)
        
        result = self._run_batch([rc_cmd])
        flush_logs_if_error()
        return result

if __name__ == "__main__":
    print("VC6 Wine Tools - Python proxy for building with Visual C++ 6.0 through Wine")
    print("Usage: This script is intended to be used as a module, not run directly.")
    print("For compiler scripts, use the cl.py, link.py, or midl.py proxy scripts.")
    print("")
    print("Environment variables:")
    print("  VC6_VERBOSE=1    Enable verbose output (prints all logs regardless of errors)")
    sys.exit(0)