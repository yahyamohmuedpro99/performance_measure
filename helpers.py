import ast
import pstats
import subprocess
import tempfile
import os
import sys
import resource

from flask import jsonify

def check_indentation(code: str):
    try:
        ast.parse(code)
        print("The code has correct indentation.")
        return True
    except IndentationError as e:
        print(f"IndentationError: {e}")
        return False

def set_resource_limits():
    # Set CPU time limit to 5 seconds
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    # Set maximum memory usage to 100 MB
    resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))


def run_untrusted_code_with_profiling(code: str):
    profile_results = {
        "output": None,
        "profiling_stats": None,
        "memory_usage": None,
        "error": None,
        "cleanup_error": None
    }

    # Create a temporary directory to isolate the execution environment
    with tempfile.TemporaryDirectory() as tempdir:
        code_file = os.path.join(tempdir, "untrusted_code.py")
        profile_output = os.path.join(tempdir, "profile1.txt")

        # Modify the untrusted code to include profiling
        profiled_code = f"""
import cProfile
import pstats
import psutil
import os

def run():
    {code}

# Profiling setup
profiler = cProfile.Profile()
profiler.enable()
run()
profiler.disable()

# Save profiling stats
profiler.dump_stats('{profile_output}')

# Get memory usage after execution
process = psutil.Process(os.getpid())
memory_info = process.memory_info()
with open('{profile_output}.mem', 'w') as mem_output:
    mem_output.write(f"Memory Usage (in MB): {{memory_info.rss / (1024 * 1024):.2f}}\\n")
"""

        # Write the modified code to the file
        with open(code_file, "w") as f:
            f.write(profiled_code)

        # Run the untrusted code in a separate process
        try:
            result = subprocess.run(
                [sys.executable, code_file],  # Use the current Python interpreter
                capture_output=True,
                text=True,
                timeout=10,  # Set a timeout for the execution
                cwd=tempdir,  # Change to the temporary directory
                preexec_fn=set_resource_limits,  # Set resource limits before execution
                check=True  # Raise an exception on non-zero exit
            )

            # Capture stdout from the executed code
            profile_results['output'] = result.stdout.strip()

            # Read profiling results
            if os.path.exists(profile_output):
                stats = pstats.Stats(profile_output)
                profile_stats = stats.strip_dirs().sort_stats(pstats.SortKey.TIME).stream()
                profile_results['profiling_stats'] = profile_stats.getvalue()
            else:
                profile_results['profiling_stats'] = f"Profile output file not found: {profile_output}"

            # Read memory usage
            if os.path.exists(f"{profile_output}.mem"):
                with open(f"{profile_output}.mem", "r") as mem_output:
                    profile_results['memory_usage'] = mem_output.read().strip()
            else:
                profile_results['memory_usage'] = f"Memory output file not found: {profile_output}.mem"

        except subprocess.CalledProcessError as e:
            profile_results['error'] = f"Error running the code:\n{e.stderr}"
        except subprocess.TimeoutExpired:
            profile_results['error'] = "Error: The untrusted code execution timed out."
        except Exception as e:
            profile_results['error'] = f"Unexpected error: {str(e)}"
        finally:
            # Clean up the temporary files
            try:
                if os.path.exists(code_file):
                    os.remove(code_file)
                if os.path.exists(profile_output):
                    os.remove(profile_output)
                if os.path.exists(f"{profile_output}.mem"):
                    os.remove(f"{profile_output}.mem")
            except Exception as cleanup_error:
                profile_results['cleanup_error'] = f"Error during cleanup: {str(cleanup_error)}"

    return profile_results

