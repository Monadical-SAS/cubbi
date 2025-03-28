'use client'

import { useState, useEffect, ChangeEvent, useCallback } from 'react';
import Head from 'next/head';
import yaml from 'js-yaml';
import { ConfigData, Container, ContainerErrors, Exercise, ExerciseErrors, ValidationError } from './types';
import ContainerComponent from './components/Container';
import ExerciseComponent from './components/Exercise';
import {
  Container as MuiContainer,
  AppBar,
  Box,
  Button,
  CssBaseline,
  Divider,
  Paper,
  Toolbar,
  Typography,
  useTheme,
  TextField,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Stack,
  Snackbar,
  Alert,
  Radio,
  Stepper,
  Step,
  StepLabel,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DownloadIcon from '@mui/icons-material/Download';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SettingsIcon from '@mui/icons-material/Settings';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import SaveIcon from '@mui/icons-material/Save';
import RefreshIcon from '@mui/icons-material/Refresh';
import DescriptionIcon from '@mui/icons-material/Description';

const steps = [
  {
    label: 'Create Containers',
    description: 'Define containers with provider and model information'
  },
  {
    label: 'Upload Exercises',
    description: 'Add exercises with instructions and input files'
  },
  {
    label: 'Output Settings',
    description: 'Configure output directory and format'
  },
];

const Home: React.FC = () => {
  const theme = useTheme();

  // Stepper state
  const [activeStep, setActiveStep] = useState<number>(0);

  const [containers, setContainers] = useState<Container[]>([
    { name: '', provider: '', model: '', provider_params: '' }
  ]);

  const [exercises, setExercises] = useState<Exercise[]>([
    { name: '', path: '', instruction: '', input_file: '' }
  ]);

  const [outputDir, setOutputDir] = useState<string>('');
  const [outputFormat, setOutputFormat] = useState<'json' | 'yaml'>('json');
  const [output, setOutput] = useState<string>('');

  // Saved configurations
  interface SavedConfig {
    filename: string;
    path: string;
    lastModified: string;
    size: number;
  }
  const [savedConfigs, setSavedConfigs] = useState<SavedConfig[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState<boolean>(false);

  // UI state
  const [snackbarOpen, setSnackbarOpen] = useState<boolean>(false);
  const [snackbarMessage, setSnackbarMessage] = useState<string>('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error' | 'info' | 'warning'>('success');

  // State to track if directory selection is supported by the browser
  const [isDirectorySupported, setIsDirectorySupported] = useState<boolean>(true);

  // State for validation errors
  const [containerErrors, setContainerErrors] = useState<ContainerErrors[]>([{
    name: { hasError: false, value: '' },
    provider: { hasError: false, value: '' },
    model: { hasError: false, value: '' },
    provider_params: { hasError: false, value: '' }
  }]);

  const [exerciseErrors, setExerciseErrors] = useState<ExerciseErrors[]>([{
    name: { hasError: false, value: '' },
    path: { hasError: false, value: '' },
    instruction: { hasError: false, value: '' },
    input_file: { hasError: false, value: '' }
  }]);

  const [outputDirError, setOutputDirError] = useState<ValidationError>({ hasError: false, value: '' });

  // Helper function for showing snackbar notifications
  const showSnackbar = useCallback((message: string, severity: 'success' | 'error' | 'info' | 'warning') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  }, []);

  // Function to fetch saved configurations - wrapped in useCallback to avoid dependency issues
  const fetchSavedConfigs = useCallback(async (): Promise<void> => {
    try {
      setLoadingConfigs(true);
      const response = await fetch('/api/configs');

      if (!response.ok) {
        throw new Error('Failed to fetch configurations');
      }

      const data = await response.json();
      setSavedConfigs(data.configs || []);
    } catch (error) {
      console.error('Error fetching configurations:', error);
      showSnackbar('Failed to fetch saved configurations', 'error');
    } finally {
      setLoadingConfigs(false);
    }
  }, [showSnackbar]);

  // Check if directory selection is supported when component mounts
  // and fetch saved configurations
  useEffect(() => {
    const input = document.createElement('input');
    input.type = 'file';

    // Check if webkitdirectory or directory attributes are supported
    const directorySupported = 'webkitdirectory' in input || 'directory' in input;
    setIsDirectorySupported(directorySupported);

    // Fetch saved configurations
    fetchSavedConfigs();
  }, [fetchSavedConfigs]);

  const addContainer = (): void => {
    setContainers([...containers, { name: '', provider: '', model: '', provider_params: '' }]);
    setContainerErrors([...containerErrors, {
      name: { hasError: false, value: '' },
      provider: { hasError: false, value: '' },
      model: { hasError: false, value: '' },
      provider_params: { hasError: false, value: '' }
    }]);

    showSnackbar('Container added', 'success');
  };

  const addExercise = (): void => {
    setExercises([...exercises, { name: '', path: '', instruction: '', input_file: '' }]);
    setExerciseErrors([...exerciseErrors, {
      name: { hasError: false, value: '' },
      path: { hasError: false, value: '' },
      instruction: { hasError: false, value: '' },
      input_file: { hasError: false, value: '' }
    }]);

    showSnackbar('Exercise added', 'success');
  };

  const removeContainer = (index: number): void => {
    const newContainers = [...containers];
    newContainers.splice(index, 1);
    setContainers(newContainers);

    const newContainerErrors = [...containerErrors];
    newContainerErrors.splice(index, 1);
    setContainerErrors(newContainerErrors);

    showSnackbar('Container removed', 'info');
  };

  const removeExercise = (index: number): void => {
    const newExercises = [...exercises];
    newExercises.splice(index, 1);
    setExercises(newExercises);

    const newExerciseErrors = [...exerciseErrors];
    newExerciseErrors.splice(index, 1);
    setExerciseErrors(newExerciseErrors);

    showSnackbar('Exercise removed', 'info');
  };

  // Validation functions
  const validateContainerField = (index: number, field: keyof Container, value: string): ValidationError => {
    const error: ValidationError = { hasError: false, value: '' };

    switch (field) {
      case 'name':
        if (!value.trim()) {
          error.hasError = true;
          error.value = 'Container name is required';
        } else if (!/^[a-zA-Z0-9_-]+$/.test(value)) {
          error.hasError = true;
          error.value = 'Name should only contain letters, numbers, hyphens and underscores';
        }
        break;
      case 'provider':
        if (!value.trim()) {
          error.hasError = true;
          error.value = 'Provider is required';
        }
        break;
      case 'model':
        if (!value.trim()) {
          error.hasError = true;
          error.value = 'Model is required';
        }
        break;
      case 'provider_params':
        if (value.trim() && !/^([a-zA-Z0-9_]+=[^,]+(,[a-zA-Z0-9_]+=[^,]+)*)?$/.test(value)) {
          error.hasError = true;
          error.value = 'Invalid format. Use: param1=value1,param2=value2';
        }
        break;
    }

    return error;
  };

  const validateExerciseField = (index: number, field: keyof Exercise, value: string): ValidationError => {
    const error: ValidationError = { hasError: false, value: '' };

    switch (field) {
      case 'name':
        if (!value.trim()) {
          error.hasError = true;
          error.value = 'Exercise name is required';
        } else if (!/^[a-zA-Z0-9_-]+$/.test(value)) {
          error.hasError = true;
          error.value = 'Name should only contain letters, numbers, hyphens and underscores';
        }
        break;
      case 'path':
        if (!value.trim()) {
          error.hasError = true;
          error.value = 'Path is required';
        }
        break;
      case 'instruction':
        if (!value.trim()) {
          error.hasError = true;
          error.value = 'Instruction content is required';
        }
        break;
      case 'input_file':
        if (!value.trim()) {
          error.hasError = true;
          error.value = 'Input file is required';
        }
        break;
    }

    return error;
  };

  const validateOutputDir = (value: string): ValidationError => {
    const error: ValidationError = { hasError: false, value: '' };

    if (!value.trim()) {
      error.hasError = true;
      error.value = 'Output directory is required';
    }

    return error;
  };

  const handleContainerChange = (index: number, field: keyof Container, value: string): void => {
    // Update the container value
    const newContainers = [...containers];
    newContainers[index][field] = value;
    setContainers(newContainers);

    // Validate and update error state
    const validationResult = validateContainerField(index, field, value);
    const newContainerErrors = [...containerErrors];
    newContainerErrors[index] = {
      ...newContainerErrors[index],
      [field]: validationResult
    };
    setContainerErrors(newContainerErrors);
  };

  const handleExerciseChange = (index: number, field: keyof Exercise, value: string): void => {
    // Update the exercise value
    const newExercises = [...exercises];
    newExercises[index][field] = value;
    setExercises(newExercises);

    // Validate and update error state
    const validationResult = validateExerciseField(index, field, value);
    const newExerciseErrors = [...exerciseErrors];
    newExerciseErrors[index] = {
      ...newExerciseErrors[index],
      [field]: validationResult
    };
    setExerciseErrors(newExerciseErrors);
  };

  const handleDirectorySelection = (index: number, e: ChangeEvent<HTMLInputElement>): void => {
    if (e.target.files && e.target.files.length > 0) {
      // Use the path of the first file and get its directory
      const filePath = e.target.files[0].webkitRelativePath;
      const folderPath = filePath.split('/')[0];

      // Update the path value and validate
      handleExerciseChange(index, 'path', folderPath);
    }
  };

  const handleFileSelection = (index: number, field: 'instruction' | 'input_file', e: ChangeEvent<HTMLInputElement>): void => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const fileName = file.name;

      // If instruction file is a markdown file, read its content
      if (field === 'instruction' && fileName.endsWith('.md')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          if (event.target && typeof event.target.result === 'string') {
            // Update with the content of the file
            handleExerciseChange(index, field, event.target.result);
          }
        };
        reader.readAsText(file);
      } else {
        // For other files just use the filename
        handleExerciseChange(index, field, fileName);
      }
    }
  };

  // Validation for step transitions
  const validateContainers = (): boolean => {
    let isValid = true;

    // Validate containers
    const newContainerErrors = [...containerErrors];
    containers.forEach((container, index) => {
      Object.keys(container).forEach(key => {
        const field = key as keyof Container;
        const validationResult = validateContainerField(index, field, container[field]);
        newContainerErrors[index][field] = validationResult;
        if (validationResult.hasError) {
          isValid = false;
        }
      });
    });
    setContainerErrors(newContainerErrors);

    return isValid;
  };

  const validateExercises = (): boolean => {
    let isValid = true;

    // Validate exercises
    const newExerciseErrors = [...exerciseErrors];
    exercises.forEach((exercise, index) => {
      Object.keys(exercise).forEach(key => {
        const field = key as keyof Exercise;
        const validationResult = validateExerciseField(index, field, exercise[field]);
        newExerciseErrors[index][field] = validationResult;
        if (validationResult.hasError) {
          isValid = false;
        }
      });
    });
    setExerciseErrors(newExerciseErrors);

    return isValid;
  };

  const validateOutputSettings = (): boolean => {
    // Validate output directory
    const outputDirValidation = validateOutputDir(outputDir);
    setOutputDirError(outputDirValidation);

    return !outputDirValidation.hasError;
  };

  const validateCurrentStep = (): boolean => {
    switch (activeStep) {
      case 0:
        return validateContainers();
      case 1:
        return validateExercises();
      case 2:
        return validateOutputSettings();
      default:
        return true;
    }
  };

  const handleNext = (): void => {
    if (validateCurrentStep()) {
      setActiveStep((prevActiveStep) => prevActiveStep + 1);
    } else {
      showSnackbar('Please fix validation errors before proceeding', 'error');
    }
  };

  const handleBack = (): void => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleStepChange = (step: number): void => {
    // Allow freely navigating to a previous step
    if (step < activeStep) {
      setActiveStep(step);
      return;
    }

    // For advancing, validate the current step first
    if (validateCurrentStep()) {
      setActiveStep(step);
    } else {
      showSnackbar('Please fix validation errors before proceeding', 'error');
    }
  };

  const validateAll = (): boolean => {
    return validateContainers() && validateExercises() && validateOutputSettings();
  };

  const generateOutput = (): void => {
    // Validate all steps before generating output
    if (!validateAll()) {
      showSnackbar('Please fix validation errors before generating', 'error');
      return;
    }

    const data: ConfigData = {
      containers,
      exercises,
      output_dir: outputDir
    };

    if (outputFormat === 'json') {
      setOutput(JSON.stringify(data, null, 2));
    } else {
      setOutput(yaml.dump(data));
    }

    showSnackbar(`${outputFormat.toUpperCase()} generated successfully`, 'success');
  };

  const saveToServer = async (): Promise<void> => {
    // Validate all steps before saving
    if (!validateAll()) {
      showSnackbar('Please fix validation errors before saving', 'error');
      return;
    }

    try {
      const data: ConfigData = {
        containers,
        exercises,
        output_dir: outputDir
      };

      setSnackbarMessage('Saving configuration to server...');
      setSnackbarSeverity('info');
      setSnackbarOpen(true);

      const response = await fetch('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to save configuration');
      }

      showSnackbar(`Configuration saved successfully as ${result.filename}`, 'success');

      // Refresh the list of saved configurations
      await fetchSavedConfigs();
    } catch (error) {
      console.error('Error saving configuration:', error);
      showSnackbar('Failed to save configuration: ' + (error instanceof Error ? error.message : 'Unknown error'), 'error');
    }
  };

  const downloadFile = (): void => {
    if (!output) return;

    const blob = new Blob([output], { type: outputFormat === 'json' ? 'application/json' : 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = outputFormat === 'json' ? 'config.json' : 'config.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showSnackbar(`${outputFormat.toUpperCase()} file downloaded`, 'success');
  };

  const loadSavedConfig = async (configPath: string): Promise<void> => {
    try {
      setSnackbarMessage('Loading configuration...');
      setSnackbarSeverity('info');
      setSnackbarOpen(true);

      const response = await fetch(configPath);

      if (!response.ok) {
        throw new Error('Failed to load configuration');
      }

      const data: ConfigData = await response.json();

      // Update state with loaded data
      if (data.containers) {
        setContainers(data.containers);
        // Initialize validation errors for containers
        setContainerErrors(data.containers.map(() => ({
          name: { hasError: false, value: '' },
          provider: { hasError: false, value: '' },
          model: { hasError: false, value: '' },
          provider_params: { hasError: false, value: '' }
        })));
      }

      if (data.exercises) {
        setExercises(data.exercises);
        // Initialize validation errors for exercises
        setExerciseErrors(data.exercises.map(() => ({
          name: { hasError: false, value: '' },
          path: { hasError: false, value: '' },
          instruction: { hasError: false, value: '' },
          input_file: { hasError: false, value: '' }
        })));
      }

      if (data.output_dir) {
        setOutputDir(data.output_dir);
      }

      // Generate output in the selected format
      if (outputFormat === 'json') {
        setOutput(JSON.stringify(data, null, 2));
      } else {
        setOutput(yaml.dump(data));
      }

      showSnackbar('Configuration loaded successfully', 'success');

      // Reset to first step
      setActiveStep(0);
    } catch (error) {
      console.error('Error loading configuration:', error);
      showSnackbar('Failed to load configuration: ' + (error instanceof Error ? error.message : 'Unknown error'), 'error');
    }
  };


  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };

  // Content for each step
  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6" component="h2">
                Containers
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={addContainer}
                color="primary"
              >
                Add Container
              </Button>
            </Box>
            <Divider sx={{ mb: 3 }} />

            {containers.map((container, index) => (
              <ContainerComponent
                key={index}
                container={container}
                errors={containerErrors[index]}
                index={index}
                onRemove={removeContainer}
                onChange={handleContainerChange}
                isRemovable={containers.length > 1}
              />
            ))}
          </Box>
        );
      case 1:
        return (
          <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6" component="h2">
                Exercises
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={addExercise}
                color="primary"
              >
                Add Exercise
              </Button>
            </Box>
            <Divider sx={{ mb: 3 }} />

            {exercises.map((exercise, index) => (
              <ExerciseComponent
                key={index}
                exercise={exercise}
                errors={exerciseErrors[index]}
                index={index}
                onRemove={removeExercise}
                onChange={handleExerciseChange}
                onDirectorySelection={handleDirectorySelection}
                onFileSelection={handleFileSelection}
                isRemovable={exercises.length > 1}
                isDirectorySupported={isDirectorySupported}
              />
            ))}
          </Box>
        );
      case 2:
        return (
          <Box>
            <Typography variant="h6" component="h2" gutterBottom>
              Output Settings
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Stack spacing={3}>
              <TextField
                fullWidth
                label="Output Directory"
                variant="outlined"
                value={outputDir}
                onChange={(e) => {
                  setOutputDir(e.target.value);
                  setOutputDirError(validateOutputDir(e.target.value));
                }}
                error={outputDirError.hasError}
                helperText={outputDirError.hasError ? outputDirError.value : ''}
              />

              <FormControl component="fieldset">
                <FormLabel component="legend">Output Format</FormLabel>
                <RadioGroup
                  row
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value as 'json' | 'yaml')}
                >
                  <FormControlLabel value="json" control={<Radio />} label="JSON" />
                  <FormControlLabel value="yaml" control={<Radio />} label="YAML" />
                </RadioGroup>
              </FormControl>

              <Stack direction="row" spacing={2}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<PlayArrowIcon />}
                  onClick={generateOutput}
                >
                  Generate
                </Button>

                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={<DownloadIcon />}
                  onClick={downloadFile}
                  disabled={!output}
                >
                  Download
                </Button>

                <Button
                  variant="contained"
                  color="success"
                  startIcon={<SaveIcon />}
                  onClick={saveToServer}
                >
                  Save to Server
                </Button>
              </Stack>
            </Stack>
          </Box>
        );
      default:
        return 'Unknown step';
    }
  };

  return (
    <>
      <CssBaseline />
      <Head>
        <title>YAML/JSON Generator</title>
        <meta name="description" content="Generate YAML and JSON configuration files" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <AppBar position="static" color="primary" elevation={0}>
        <Toolbar>
          <SettingsIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Configuration Generator
          </Typography>
        </Toolbar>
      </AppBar>

      <MuiContainer maxWidth="lg" sx={{ py: 4 }}>
        <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
          <Typography variant="h5" component="h1" gutterBottom>
            Create Your Configuration
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Follow these steps to create your YAML/JSON configuration file. You can go back to previous steps at any time.
          </Typography>

          <Stepper activeStep={activeStep} orientation="horizontal" sx={{ mb: 4 }}>
            {steps.map((step, index) => (
              <Step key={step.label} completed={index < activeStep}>
                <StepLabel
                  optional={
                    <Typography variant="caption" color="text.secondary">
                      {step.description}
                    </Typography>
                  }
                  onClick={() => handleStepChange(index)}
                  sx={{ cursor: 'pointer' }}
                >
                  {step.label}
                </StepLabel>
              </Step>
            ))}
          </Stepper>

          <Box sx={{ mb: 3 }}>
            {getStepContent(activeStep)}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
            <Button
              color="inherit"
              disabled={activeStep === 0}
              onClick={handleBack}
              startIcon={<NavigateBeforeIcon />}
            >
              Back
            </Button>

            {activeStep === steps.length - 1 ? (
              <Box />
            ) : (
              <Button
                variant="contained"
                color="primary"
                onClick={handleNext}
                endIcon={<NavigateNextIcon />}
              >
                Next
              </Button>
            )}
          </Box>
        </Paper>

        {output && (
          <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
            <Typography variant="h5" component="h2" gutterBottom>
              Output
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Box
              component="pre"
              sx={{
                backgroundColor: theme.palette.grey[100],
                p: 2,
                borderRadius: 1,
                overflow: 'auto',
                maxHeight: '400px',
                fontSize: '0.875rem',
                fontFamily: '"Roboto Mono", monospace',
              }}
            >
              {output}
            </Box>
          </Paper>
        )}

        <Paper elevation={3} sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h5" component="h2">
              Saved Configurations
            </Typography>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={fetchSavedConfigs}
              disabled={loadingConfigs}
            >
              Refresh
            </Button>
          </Box>
          <Divider sx={{ mb: 3 }} />

          {loadingConfigs ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : savedConfigs.length > 0 ? (
            <Box>
              <List>
                {savedConfigs.map((config) => (
                  <ListItem
                    key={config.filename}
                    secondaryAction={
                      <Button
                        variant="contained"
                        size="small"
                        onClick={() => loadSavedConfig(config.path)}
                      >
                        Load
                      </Button>
                    }
                    sx={{
                      mb: 1,
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: 'divider',
                      '&:hover': {
                        backgroundColor: 'rgba(0, 0, 0, 0.04)'
                      }
                    }}
                  >
                    <ListItemIcon>
                      <DescriptionIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary={config.filename}
                      secondary={`Last modified: ${new Date(config.lastModified).toLocaleString()} • Size: ${(config.size / 1024).toFixed(1)} KB`}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          ) : (
            <Box py={4} textAlign="center" color="text.secondary">
              <Typography variant="body1">
                No saved configurations found.
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Save a configuration using the &quot;Save to Server&quot; button to see it here.
              </Typography>
            </Box>
          )}
        </Paper>
      </MuiContainer>

      <Box
        component="footer"
        sx={{
          py: 3,
          mt: 'auto',
          backgroundColor: theme.palette.grey[100],
          textAlign: 'center'
        }}
      >
        <Typography variant="body2" color="text.secondary">
          YAML/JSON Configuration Generator
        </Typography>
      </Box>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbarSeverity}
          sx={{ width: '100%' }}
          variant="filled"
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </>
  );
};

export default Home;