import os
import pathlib
import json
import shutil
from datetime import datetime
import subprocess

def create_benchmark_folder():
    """
    Creates a new .benchmark-{datetime} folder with a copy of the exercises folder
    """
    # Get current datetime formatted as YYYYMMDD-HHMMSS
    current_time = datetime.now().strftime("%Y%m%d-%H%M%S")
    benchmark_dir = f".benchmark-{current_time}"
    
    # Get the current working directory
    cwd = os.getcwd()
    exercises_dir = os.path.join(cwd, "benchmark")
    benchmark_path = os.path.join(cwd, benchmark_dir)
    
    print(f"Creating benchmark directory: {benchmark_path}")
    
    # Create the benchmark directory
    os.makedirs(benchmark_path, exist_ok=True)
    
    # Copy the exercises folder to the benchmark directory
    shutil.copytree(exercises_dir, os.path.join(benchmark_path, "benchmark"))
    
    print(f"Successfully copied exercises to {benchmark_path}")
    return benchmark_path

def create_goose_instructions_in_docs(root_dir):
    """
    Walks through all subfolders, finds .docs directories,
    and creates goose-instructions.md in each one.
    
    Args:
        root_dir: The root directory to start the search from
    """
    exercises_dir = os.path.join(root_dir, "benchmark")
    count = 0
    
    print(f"Starting search from: {exercises_dir}")
    
    # Walk through all directories and subdirectories
    for dirpath, dirnames, filenames in os.walk(exercises_dir):
        # Check if .docs directory exists in the current directory
        if ".docs" in dirnames:
            docs_path = os.path.join(dirpath, ".docs")
            goose_file_path = os.path.join(docs_path, "goose-instructions.md")
            
            meta_config_path = os.path.join(dirpath, ".meta/config.json")
            
            # Check if the config.json file exists
            if not os.path.exists(meta_config_path):
                print(f"Warning: Missing config.json in {dirpath}")
                continue
                
            # Read the config file
            try:
                with open(meta_config_path, "r") as config_file:
                    config = json.loads(config_file.read())
                
                instructions_path = os.path.join(docs_path, "instructions.md")
                
                # Check if the instructions.md file exists
                if not os.path.exists(instructions_path):
                    print(f"Warning: Missing instructions.md in {docs_path}")
                    continue
                    
                # Read the instructions file
                with open(instructions_path, "r") as file:
                    instructions = file.read()
                
                # Create the goose-instructions.md file
                with open(goose_file_path, "w") as f:
                    solution_files = ", ".join(config.get('files', {}).get('solution', []))
                    f.write(f"1) Install all the dependencies needed for this project\n")
                    f.write(f"2) Use the above instructions to modify the supplied files: {solution_files} Don't change the names of existing functions or classes, as they may be referenced from other code like unit tests, etc. Only use standard libraries, don't suggest installing any packages.\n {instructions}\n")
                    f.write(f"3) Run available tests and write the result in results.json file with this structure:\n```\n{{\n    total_suites: \n    total_tests: \n    execution_time: \n    total_tests_executions: \n    failed_suites: \n    passed_tests: \n}}\n```\n")
                
                count += 1
                print(f"Created goose-instructions.md in {docs_path}")
                
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in {meta_config_path}")
            except Exception as e:
                print(f"Error processing {dirpath}: {str(e)}")
    
    print(f"\nProcess completed. Created {count} goose-instructions.md files.")

def execute_goose_instructions(root_dir):
    """
    Executes the goose-instructions.md files in the .docs directories
    """
    exercises_dir = os.path.join(root_dir, "benchmark")
    
    print(f"Starting search from: {exercises_dir}")
    
    # Walk through all directories and subdirectories
    for dirpath, dirnames, filenames in os.walk(exercises_dir):
        try:
            # Check if .docs directory exists in the current directory
            if ".docs" in dirnames:
                docs_path = os.path.join(dirpath, ".docs")
                goose_file_path = os.path.join(docs_path, "goose-instructions.md")
                
                # Check if the goose-instructions.md file exists
                if not os.path.exists(goose_file_path):
                    print(f"Warning: Missing goose-instructions.md in {docs_path}")
                    continue
                os.chdir(dirpath)
                logs_dir = os.path.join(dirpath, "logs")
                os.makedirs(logs_dir, exist_ok=True)
                # Generate a timestamp for the log file
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                log_file_path = os.path.join(logs_dir, f"goose-run-{timestamp}.log")
                
                # Execute the command and stream output in real-time
                
                with open(log_file_path, 'w') as log_file:
                    cmd = ["goose", "run", "-i", goose_file_path]
                    cmd_msg = f"Executing command: {' '.join(cmd)}"
                    print(f"Executing command: {' '.join(cmd)}")
                    print(cmd_msg)
                    log_file.write(f"{cmd_msg}\n\n")
                    log_file.flush()
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    for line in process.stdout:
                        # Write to file and flush to ensure real-time logging
                        log_file.write(line)
                        log_file.flush()
                    return_code = process.wait()
                    if return_code == 0:
                        success_msg = "\nGoose command executed successfully!"
                        print(success_msg)
                        log_file.write(f"{success_msg}\n")
                    else:
                        error_msg = f"\nGoose command failed with return code: {return_code}"
                        print(error_msg)
                        log_file.write(f"{error_msg}\n")
                    
                    # Add final timestamp
                    log_file.write(f"\nGoose run completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    # Create a relative path for display to the user
                    rel_log_path = os.path.join("logs", os.path.basename(log_file_path))
                    print(f"\nLog file created at: {rel_log_path}")
                    if return_code != 0:
                        print(f"Check the log file for more details.")
                    print("\n")
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            try:
                with open(log_file_path, 'a') as log_file:
                    log_file.write(f"{error_msg}\n")
            except:
                # If we can't write to the log file, just print to console
                print(f"Could not write to log file.")
            return 1
        
        finally:
            # Return to the original directory
            os.chdir(exercises_dir)
            
                    

if __name__ == "__main__":
    # First create the benchmark folder with a copy of exercises
    benchmark_path = create_benchmark_folder()
    
    # Then process the copied exercises to create goose-instructions.md files
    create_goose_instructions_in_docs(benchmark_path)
    
    # Execute goose instructions
    execute_goose_instructions(benchmark_path)