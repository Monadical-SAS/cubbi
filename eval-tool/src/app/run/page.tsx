'use client'

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Box,
  CircularProgress,
  Typography,
  Paper,
  Container,
  AppBar,
  Toolbar,
  Divider,
  Button,
  Grid,
  Card,
  CardContent,
  Chip,
  Stack,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import FolderIcon from '@mui/icons-material/Folder';
import TerminalIcon from '@mui/icons-material/Terminal';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import PendingIcon from '@mui/icons-material/Pending';
import { ConfigData } from '../types';
import dynamic from 'next/dynamic';

// Import the markdown editor styles - make sure these are available in your project
import '@uiw/react-md-editor/markdown-editor.css';
import '@uiw/react-markdown-preview/markdown.css';

// Import the MDEditor Markdown component dynamically to avoid SSR issues
const MDPreview = dynamic(() => import('@uiw/react-md-editor').then((mod) => mod.default.Markdown), { ssr: false });

const RunPage: React.FC = () => {
  const searchParams = useSearchParams();
  const configPath = searchParams.get('config');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [runStarted, setRunStarted] = useState<boolean>(false);
  const [runId, setRunId] = useState<string>('');
  
  // Track status for each container
  type ContainerStatus = 'pending' | 'running' | 'finished' | 'failed';
  type ContainerOutput = { status: ContainerStatus; output: string };
  
  const [containerOutputs, setContainerOutputs] = useState<Record<number, ContainerOutput>>({});
  const [webSocket, setWebSocket] = useState<WebSocket | null>(null);

  // Fetch configuration data
  useEffect(() => {
    const fetchConfig = async () => {
      if (!configPath) {
        setError('No configuration path provided');
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(configPath);
        if (!response.ok) {
          throw new Error('Failed to load configuration');
        }

        const data = await response.json();
        setConfig(data);
        
        // Initialize container outputs
        if (data.containers) {
          const initialOutputs: Record<number, ContainerOutput> = {};
          data.containers.forEach((_, index) => {
            initialOutputs[index] = { status: 'pending', output: '' };
          });
          setContainerOutputs(initialOutputs);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, [configPath]);

  // Polling for updates in development mode
  useEffect(() => {
    if (!runStarted || !runId) {
      return;
    }

    // Next.js API routes don't directly support WebSockets,
    // so we'll use polling in development mode for demonstration
    console.log('Using polling for container updates');
    
    let pollingInterval: NodeJS.Timeout;
    let isPolling = true;
    
    // Function to fetch updates
    const fetchUpdates = async () => {
      if (!isPolling) return;
      
      try {
        const response = await fetch(`/api/ws/run/${runId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch run updates');
        }
        
        const data = await response.json();
        
        // Process container states
        if (data.containers && Array.isArray(data.containers)) {
          data.containers.forEach((container) => {
            const { containerId, status, output } = container;
            
            setContainerOutputs(prev => {
              const currentContainer = prev[containerId];
              
              // Only update if there's a change
              if (!currentContainer || 
                  currentContainer.status !== status || 
                  currentContainer.output !== output) {
                return {
                  ...prev,
                  [containerId]: {
                    status: status || currentContainer?.status || 'pending',
                    output: output || currentContainer?.output || ''
                  }
                };
              }
              
              return prev;
            });
          });
          
          // Check if all containers are finished
          const allFinished = data.containers.every(
            (c: any) => c.status === 'finished' || c.status === 'failed'
          );
          
          if (allFinished) {
            setRunning(false);
            isPolling = false;
          }
        }
      } catch (error) {
        console.error('Error polling for updates:', error);
        
        // If polling fails too many times, fall back to simulation
        if (!Object.values(containerOutputs).some(output => output.output.includes('simulation mode'))) {
          console.log('Falling back to simulation mode due to polling errors');
          simulateRun();
          isPolling = false;
        }
      }
      
      // Continue polling if still running
      if (isPolling) {
        pollingInterval = setTimeout(fetchUpdates, 1000);
      }
    };
    
    // Start polling
    fetchUpdates();
    
    // Cleanup function
    return () => {
      isPolling = false;
      if (pollingInterval) {
        clearTimeout(pollingInterval);
      }
    };
  }, [runStarted, runId]);
  
  // Note: In a production environment, this would use real WebSockets
  // The WebSocket implementation would look something like this:
  /*
  useEffect(() => {
    if (!runStarted || !runId) {
      return;
    }

    // Connect to WebSocket server
    const socket = io();
    
    // Join the specific run channel
    socket.emit('joinRun', runId);
    
    // Set up event handlers
    socket.on('containerUpdate', (data) => {
      if (data.runId !== runId) return;
      
      const { containerId, status, output, append } = data;
      
      setContainerOutputs(prev => {
        const currentOutput = prev[containerId]?.output || '';
        const newOutput = append ? currentOutput + output : output;
        
        return {
          ...prev,
          [containerId]: {
            status: status || prev[containerId]?.status || 'pending',
            output: newOutput
          }
        };
      });
    });
    
    socket.on('runStatus', (data) => {
      if (data.runId !== runId) return;
      
      if (data.status === 'completed' || data.status === 'failed') {
        setRunning(false);
      }
    });
    
    // Cleanup function
    return () => {
      socket.off('containerUpdate');
      socket.off('runStatus');
      socket.disconnect();
    };
  }, [runStarted, runId]);
  */

  const handleRun = async () => {
    setRunning(true);
    setRunStarted(true);
    
    try {
      // Initialize container statuses to pending
      const initialOutputs: Record<number, ContainerOutput> = {};
      config?.containers.forEach((_, index) => {
        initialOutputs[index] = { status: 'pending', output: '# Initializing...\n\nWaiting for container to start.' };
      });
      setContainerOutputs(initialOutputs);
      
      // Make API call to start the run
      const response = await fetch('/api/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          config: configPath,
          containers: config?.containers.map(c => ({
            navigator: c.navigator,
            provider: c.provider,
            model: c.model,
            provider_params: c.provider_params
          })),
          exercises: config?.exercises.map(e => ({
            path: e.path,
            instruction: e.instruction,
            input_file: e.input_file
          })),
          output_dir: config?.output_dir
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to start run');
      }
      
      const data = await response.json();
      setRunId(data.runId);
      
      // If for some reason we don't get a WebSocket connection,
      // fall back to a simulated run for demonstration purposes
      if (process.env.NODE_ENV === 'development' && !data.runId) {
        console.log('Using simulated run for development');
        simulateRun();
      }
    } catch (err) {
      console.error('Error starting run:', err);
      setError(err instanceof Error ? err.message : 'Failed to start run');
      setRunning(false);
    }
  };
  
  // Fallback simulation function for development
  const simulateRun = () => {
    // Set a message to indicate we're using simulation mode
    setContainerOutputs(prev => {
      const updatedOutputs = { ...prev };
      Object.keys(updatedOutputs).forEach(key => {
        const index = parseInt(key);
        updatedOutputs[index] = {
          ...updatedOutputs[index],
          output: updatedOutputs[index].output + 
            "\n\n> **Note:** Using simulation mode as WebSocket connection is not available. " +
            "In production, this would stream real-time logs from the containers.\n\n"
        };
      });
      return updatedOutputs;
    });
    
    const totalContainers = config?.containers.length || 0;
    
    // Process each container sequentially with different timing and outcomes
    for (let i = 0; i < totalContainers; i++) {
      // Set container to running state
      setTimeout(() => {
        setContainerOutputs(prev => ({
          ...prev,
          [i]: { ...prev[i], status: 'running' }
        }));
        
        // Add some initial output
        setTimeout(() => {
          setContainerOutputs(prev => ({
            ...prev,
            [i]: { 
              ...prev[i], 
              output: prev[i].output + `\n# Starting container ${i + 1}: ${config?.containers[i].navigator}\n\nInitializing with model: ${config?.containers[i].model}\nProvider: ${config?.containers[i].provider}\n\n` 
            }
          }));
        }, 500);
        
        // Add more output
        setTimeout(() => {
          setContainerOutputs(prev => ({
            ...prev,
            [i]: { 
              ...prev[i], 
              output: prev[i].output + `\n## Processing exercise\n\nLoading files from: ${config?.exercises[0]?.path || 'unknown'}\nReading input file: ${config?.exercises[0]?.input_file || 'unknown'}\n\n\`\`\`\nExecuting code...\nAnalyzing results...\n\`\`\`\n` 
            }
          }));
        }, 1500 + i * 500);
        
        // Finalize with either success or failure (randomly)
        setTimeout(() => {
          const isSuccess = Math.random() > 0.3; // 70% chance of success
          setContainerOutputs(prev => ({
            ...prev,
            [i]: { 
              status: isSuccess ? 'finished' : 'failed',
              output: prev[i].output + `\n${isSuccess ? '## Success! ✅\n\nExecution completed successfully.\n\nResults saved to output directory.' : '## Failed ❌\n\nEncountered an error during execution.\n\nError: Connection timeout after 30 seconds.'}` 
            }
          }));
          
          // If this is the last container, set overall running to false
          if (i === totalContainers - 1) {
            setRunning(false);
          }
        }, 3000 + i * 2000);
      }, i * 1000); // Start each container after the previous one
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', p: 3 }}>
        <Paper sx={{ p: 4, maxWidth: 600, textAlign: 'center' }}>
          <Typography variant="h5" color="error" gutterBottom>
            Error Loading Configuration
          </Typography>
          <Typography variant="body1">{error}</Typography>
          <Button variant="contained" sx={{ mt: 3 }} onClick={() => window.close()}>
            Close Window
          </Button>
        </Paper>
      </Box>
    );
  }

  if (!config) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', p: 3 }}>
        <Paper sx={{ p: 4, maxWidth: 600, textAlign: 'center' }}>
          <Typography variant="h5" gutterBottom>
            No Configuration Found
          </Typography>
          <Button variant="contained" sx={{ mt: 3 }} onClick={() => window.close()}>
            Close Window
          </Button>
        </Paper>
      </Box>
    );
  }

  // Helper function to render status icon
  const renderStatusIcon = (status: ContainerStatus) => {
    switch (status) {
      case 'pending':
        return <PendingIcon sx={{ color: 'grey.500' }} />;
      case 'running':
        return <CircularProgress size={20} />;
      case 'finished':
        return <CheckCircleIcon sx={{ color: 'success.main' }} />;
      case 'failed':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      default:
        return null;
    }
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <SettingsIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Run Configuration
          </Typography>
          <Button 
            color="inherit" 
            startIcon={<PlayArrowIcon />}
            onClick={handleRun}
            disabled={running || runStarted}
          >
            {running ? 'Running...' : 'Start Run'}
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        {!runStarted ? (
          // Configuration Details View (before run starts)
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              Configuration Details
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  <FolderIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Output Directory
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
                  <Typography variant="body1">{config.output_dir}</Typography>
                </Paper>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  <TerminalIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Containers ({config.containers.length})
                </Typography>
                <Grid container spacing={2}>
                  {config.containers.map((container, index) => (
                    <Grid item xs={12} md={6} key={index}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            Container {index + 1}
                          </Typography>
                          <Stack spacing={1}>
                            <Box>
                              <Typography variant="subtitle2" component="span">Navigator: </Typography>
                              <Chip 
                                label={container.navigator || 'Not set'} 
                                size="small" 
                                color="primary" 
                                variant="outlined"
                              />
                            </Box>
                            <Box>
                              <Typography variant="subtitle2" component="span">Provider: </Typography>
                              <Chip 
                                label={container.provider || 'Not set'} 
                                size="small" 
                                color="secondary" 
                                variant="outlined"
                              />
                            </Box>
                            <Box>
                              <Typography variant="subtitle2" component="span">Model: </Typography>
                              <Chip 
                                label={container.model || 'Not set'} 
                                size="small" 
                                color="info" 
                                variant="outlined"
                              />
                            </Box>
                            {container.provider_params && (
                              <Box>
                                <Typography variant="subtitle2">Parameters:</Typography>
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                                  {container.provider_params.split(',').map((param, i) => (
                                    <Chip 
                                      key={i} 
                                      label={param} 
                                      size="small" 
                                      variant="outlined"
                                    />
                                  ))}
                                </Box>
                              </Box>
                            )}
                          </Stack>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  <FolderIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Exercises ({config.exercises.length})
                </Typography>
                <Grid container spacing={2}>
                  {config.exercises.map((exercise, index) => (
                    <Grid item xs={12} md={6} key={index}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            Exercise {index + 1}
                          </Typography>
                          <Stack spacing={1}>
                            <Box>
                              <Typography variant="subtitle2">Directory Path:</Typography>
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  bgcolor: 'grey.100', 
                                  p: 1, 
                                  borderRadius: 1,
                                  wordBreak: 'break-all'
                                }}
                              >
                                {exercise.path}
                              </Typography>
                            </Box>
                            <Box>
                              <Typography variant="subtitle2">Input File:</Typography>
                              <Typography variant="body2">{exercise.input_file}</Typography>
                            </Box>
                            <Box>
                              <Typography variant="subtitle2">Instruction:</Typography>
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  maxHeight: 100, 
                                  overflow: 'auto',
                                  whiteSpace: 'pre-wrap',
                                }}
                              >
                                {exercise.instruction.length > 100 
                                  ? `${exercise.instruction.substring(0, 100)}...` 
                                  : exercise.instruction}
                              </Typography>
                            </Box>
                          </Stack>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Grid>
            </Grid>
          </Paper>
        ) : (
          // Run Execution View (after run starts)
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              Run Execution
            </Typography>
            <Divider sx={{ mb: 3 }} />
            
            {running && (
              <Box sx={{ width: '100%', mb: 3 }}>
                <LinearProgress />
              </Box>
            )}
            
            <Typography variant="subtitle1" gutterBottom sx={{ mb: 2 }}>
              <TerminalIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Container Outputs
            </Typography>
            
            {config.containers.map((container, index) => {
              const containerOutput = containerOutputs[index];
              const status = containerOutput?.status || 'pending';
              
              let statusText = 'Pending';
              let statusColor = 'text.secondary';
              
              switch (status) {
                case 'running':
                  statusText = 'Running';
                  statusColor = 'primary.main';
                  break;
                case 'finished':
                  statusText = 'Finished';
                  statusColor = 'success.main';
                  break;
                case 'failed':
                  statusText = 'Failed';
                  statusColor = 'error.main';
                  break;
              }
              
              return (
                <Accordion 
                  key={index} 
                  defaultExpanded={true}
                  sx={{ 
                    mb: 2,
                    border: '1px solid',
                    borderColor: status === 'running' ? 'primary.light' : 
                                 status === 'finished' ? 'success.light' : 
                                 status === 'failed' ? 'error.light' : 'divider'
                  }}
                >
                  <AccordionSummary 
                    expandIcon={<ExpandMoreIcon />}
                    aria-controls={`container-${index}-content`}
                    id={`container-${index}-header`}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                      <Box sx={{ mr: 1 }}>
                        {renderStatusIcon(status)}
                      </Box>
                      <Typography 
                        variant="subtitle1" 
                        sx={{ fontWeight: status !== 'pending' ? 500 : 400 }}
                      >
                        Container {index + 1}: {container.navigator}
                      </Typography>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          ml: 'auto', 
                          color: statusColor,
                          fontWeight: 500
                        }}
                      >
                        {statusText}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box 
                      sx={{ 
                        p: 2, 
                        bgcolor: 'grey.50', 
                        borderRadius: 1,
                        minHeight: '100px'
                      }}
                      data-color-mode="light"
                    >
                      {containerOutput?.output ? (
                        <div className="wmde-markdown">
                          <MDPreview source={containerOutput.output} />
                        </div>
                      ) : (
                        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                          Waiting to start...
                        </Typography>
                      )}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              );
            })}
          </Paper>
        )}
        
        {!runStarted && (
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mb: 3 }}>
            <Button 
              variant="contained" 
              color="primary"
              startIcon={<PlayArrowIcon />}
              onClick={handleRun}
              disabled={running}
              size="large"
            >
              {running ? 'Running...' : 'Start Run'}
            </Button>
            <Button 
              variant="outlined"
              onClick={() => window.close()}
            >
              Close
            </Button>
          </Box>
        )}
        
        {runStarted && (
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mb: 3 }}>
            <Button 
              variant="outlined"
              onClick={() => window.location.reload()}
            >
              Reset
            </Button>
            <Button 
              variant="outlined"
              onClick={() => window.close()}
            >
              Close
            </Button>
          </Box>
        )}
      </Container>
    </>
  );
};

export default RunPage;