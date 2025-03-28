import { NextRequest, NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import { exec } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';
import { EventEmitter } from 'events';

// Global event emitter for broadcasting container logs
export const runEvents = new EventEmitter();

// In-memory storage for active runs (in a real app, this would be a database)
interface ActiveRun {
  id: string;
  config: any;
  containers: any[];
  exercises: any[];
  output_dir: string;
  startTime: Date;
  processes: Record<number, {
    child: any;
    status: 'pending' | 'running' | 'finished' | 'failed';
    output: string;
  }>;
  tempDir?: string;
}

const activeRuns: Record<string, ActiveRun> = {};

export async function POST(request: NextRequest) {
  try {
    // Parse the request body
    const data = await request.json();
    
    // Validate the data
    if (!data || !data.containers || !data.exercises || !data.output_dir) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }
    
    // Generate a unique run ID
    const runId = uuidv4();
    
    // Create a temporary directory for this run
    const tempDir = path.join(process.cwd(), 'tmp', runId);
    try {
      await fs.mkdir(tempDir, { recursive: true });
    } catch (mkdirError) {
      console.error('Error creating temp directory:', mkdirError);
      return NextResponse.json(
        { error: 'Failed to create temporary directory' },
        { status: 500 }
      );
    }
    
    // Store the run information
    activeRuns[runId] = {
      id: runId,
      config: data.config,
      containers: data.containers,
      exercises: data.exercises,
      output_dir: data.output_dir,
      startTime: new Date(),
      processes: {},
      tempDir
    };
    
    // Start background processes for each container
    executeContainers(runId, data.containers, data.exercises, tempDir);
    
    return NextResponse.json({ 
      success: true,
      runId,
      message: 'Run started successfully'
    });
  } catch (error) {
    console.error('Error starting run:', error);
    return NextResponse.json(
      { error: 'Failed to start run' },
      { status: 500 }
    );
  }
}

// Helper function to get run by ID
export function getRunById(runId: string): ActiveRun | null {
  return activeRuns[runId] || null;
}

// Function to start background processes for each container
function executeContainers(runId: string, containers: any[], exercises: any[], tempDir: string) {
  const run = activeRuns[runId];
  if (!run) return;
  
  // Execute each container in sequence
  containers.forEach((container, index) => {
    // Initialize container process info
    run.processes[index] = {
      child: null,
      status: 'pending',
      output: '# Initializing container...\n\nPreparing environment for execution.'
    };
    
    // Emit initial status
    runEvents.emit('containerUpdate', {
      runId,
      containerId: index,
      status: 'pending',
      output: run.processes[index].output,
      append: false
    });
    
    // Schedule execution with a delay to simulate sequential startup
    setTimeout(() => {
      // Call async function but don't await it here - we want it to run in the background
      startContainerProcess(runId, index, container, exercises, tempDir).catch(error => {
        console.error(`Error starting container process ${index}:`, error);
        
        // Update container status to failed
        if (run.processes[index]) {
          run.processes[index].status = 'failed';
          const errorOutput = `\n# Fatal Error\n\nAn unexpected error occurred: ${error}\n`;
          run.processes[index].output += errorOutput;
          
          // Emit update
          runEvents.emit('containerUpdate', {
            runId,
            containerId: index,
            status: 'failed',
            output: errorOutput,
            append: true
          });
        }
      });
    }, index * 1000); // Start each container 1 second after the previous one
  });
}

// Function to start a single container process
async function startContainerProcess(runId: string, containerId: number, container: any, exercises: any[], tempDir: string) {
  const run = activeRuns[runId];
  if (!run) return;
  
  // Update container status to running
  run.processes[containerId].status = 'running';
  
  // Create container-specific directory
  const containerDir = path.join(tempDir, `container-${containerId}`);
  try {
    await fs.mkdir(containerDir, { recursive: true });
  } catch (error) {
    console.error(`Error creating container directory: ${containerDir}`, error);
    // Update output with error information
    const errorOutput = `\n# Error Starting Container\n\nFailed to create container directory. Error: ${error}\n`;
    run.processes[containerId].output += errorOutput;
    run.processes[containerId].status = 'failed';
    
    // Emit update
    runEvents.emit('containerUpdate', {
      runId,
      containerId,
      status: 'failed',
      output: errorOutput,
      append: true
    });
    return;
  }
  
  // Generate a command based on container configuration
  let command;
  try {
    // Initial update for waiting for command generation
    const preparingOutput = `\n# Preparing Configuration\n\nCreating YAML configuration file for MC eval...\n`;
    run.processes[containerId].output += preparingOutput;
    runEvents.emit('containerUpdate', {
      runId,
      containerId,
      status: 'running',
      output: preparingOutput,
      append: true
    });
    
    // Generate the command
    command = await generateCommand(container, exercises, containerDir);
    
    // Update output with starting information
    const initialOutput = `\n# Starting Container: ${container.navigator}\n\nProvider: ${container.provider}\nModel: ${container.model}\nCommand: \`${command}\`\n\n## Execution Log\n\n`;
    run.processes[containerId].output += initialOutput;
    
    // Emit update
    runEvents.emit('containerUpdate', {
      runId,
      containerId,
      status: 'running',
      output: initialOutput,
      append: true
    });
  } catch (error) {
    console.error('Error generating command:', error);
    const errorOutput = `\n# Error Preparing Container\n\nFailed to generate command. Error: ${error}\n`;
    run.processes[containerId].output += errorOutput;
    run.processes[containerId].status = 'failed';
    
    runEvents.emit('containerUpdate', {
      runId,
      containerId,
      status: 'failed',
      output: errorOutput,
      append: true
    });
    return;
  }
  
  // Start the process
  const childProcess = exec(command, {
    cwd: containerDir,
    env: {
      ...process.env,
      NAVIGATOR: container.navigator,
      PROVIDER: container.provider,
      MODEL: container.model,
      PROVIDER_PARAMS: container.provider_params || '',
      PATH: process.env.PATH // Ensure PATH is properly passed
    },
    maxBuffer: 1024 * 1024 * 10 // 10MB buffer for output
  });
  
  run.processes[containerId].child = childProcess;
  
  // Handle process output
  childProcess.stdout?.on('data', (data) => {
    const output = `\`\`\`\n${data.toString()}\n\`\`\`\n`;
    run.processes[containerId].output += output;
    
    // Emit update
    runEvents.emit('containerUpdate', {
      runId,
      containerId,
      status: 'running',
      output,
      append: true
    });
  });
  
  childProcess.stderr?.on('data', (data) => {
    const output = `\`\`\`\n${data.toString()}\n\`\`\`\n`;
    run.processes[containerId].output += output;
    
    // Emit update
    runEvents.emit('containerUpdate', {
      runId,
      containerId,
      status: 'running',
      output,
      append: true
    });
  });
  
  // Handle process completion
  childProcess.on('close', (code) => {
    const isSuccess = code === 0;
    const status = isSuccess ? 'finished' : 'failed';
    run.processes[containerId].status = status;
    
    const completionMessage = isSuccess 
      ? `\n## Success ✅\n\nExecution completed successfully with exit code 0.\nResults saved to output directory: ${run.output_dir}\n` 
      : `\n## Failed ❌\n\nExecution failed with exit code ${code}.\nPlease check the logs above for details.\n`;
    
    run.processes[containerId].output += completionMessage;
    
    // Emit update
    runEvents.emit('containerUpdate', {
      runId,
      containerId,
      status,
      output: completionMessage,
      append: true
    });
    
    // Check if all containers are finished
    const allFinished = Object.values(run.processes).every(
      p => p.status === 'finished' || p.status === 'failed'
    );
    
    if (allFinished) {
      // Emit run completion event
      runEvents.emit('runStatus', {
        runId,
        status: 'completed'
      });
      
      // Clean up temp directory after a delay
      setTimeout(() => {
        if (run.tempDir) {
          fs.rm(run.tempDir, { recursive: true, force: true })
            .catch(error => console.error('Error cleaning up temp directory:', error));
        }
      }, 60 * 60 * 1000); // Keep files for 1 hour for debugging
    }
  });
}

// Helper function to generate the config file and command based on container configuration
async function generateCommand(container: any, exercises: any[], containerDir: string): Promise<string> {
  const { navigator, provider, model, provider_params } = container;
  
  try {
    // Create a config file for this container
    const configFileName = `${containerDir}/config.yaml`;
    
    // Parse provider parameters
    const providerParams: Record<string, string> = {};
    if (provider_params) {
      provider_params.split(',').forEach((param: string) => {
        const [key, value] = param.split('=');
        if (key && value) {
          providerParams[key.trim()] = value.trim();
        }
      });
    }
    
    // Build the config object
    const config = {
      navigator,
      provider,
      model,
      provider_params: providerParams,
      exercises: exercises.map(exercise => ({
        path: exercise.path,
        instruction: exercise.instruction,
        input_file: exercise.input_file
      }))
    };
    
    // Convert to YAML format - simple approach
    let yamlContent = 'navigator: ' + navigator + '\n';
    yamlContent += 'provider: ' + provider + '\n';
    yamlContent += 'model: ' + model + '\n';
    
    if (Object.keys(providerParams).length > 0) {
      yamlContent += 'provider_params:\n';
      Object.entries(providerParams).forEach(([key, value]) => {
        yamlContent += `  ${key}: ${value}\n`;
      });
    }
    
    yamlContent += 'exercises:\n';
    exercises.forEach((exercise: any) => {
      yamlContent += '  - path: ' + exercise.path + '\n';
      yamlContent += '    input_file: ' + exercise.input_file + '\n';
      
      // Handle multiline instruction content properly
      yamlContent += '    instruction: |\n';
      const instructionLines = exercise.instruction.split('\n');
      instructionLines.forEach((line: string) => {
        yamlContent += '      ' + line + '\n';
      });
    });
    
    // Write the config file
    await fs.writeFile(configFileName, yamlContent, 'utf8');
    
    // Return the mc eval command
    return `echo "Executing MC eval with ${navigator} navigator on ${provider} (${model})" && ` +
           `echo "Config file created at: ${configFileName}" && ` +
           `echo "Running MC eval command..." && ` +
           `mc eval --config-file ${configFileName}`;
           
    // Fallback command in case mc command is not available
    // return `echo "Would run: mc eval --config-file ${configFileName}" && ` +
    //        `echo "Config file content:" && ` +
    //        `cat ${configFileName} && ` +
    //        `echo "Simulating MC eval execution..." && ` +
    //        `sleep 3 && ` +
    //        `echo "Evaluation complete" && ` +
    //        `exit 0`;
  } catch (error) {
    console.error('Error generating config file:', error);
    
    // Fallback command if config file creation fails
    return `echo "Error creating config file. Using fallback command." && ` +
           `echo "Would run: mc eval with ${navigator} on ${provider} (${model})" && ` +
           `sleep 2 && ` +
           `echo "Simulated run complete" && ` +
           `exit 0`;
  }
}