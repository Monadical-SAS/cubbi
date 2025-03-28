'use client'

import React, { ChangeEvent, useState } from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  TextField, 
  Grid, 
  FormHelperText,
  IconButton,
  Box,
  Divider,
  Alert,
  Paper,
  styled,
  Tab,
  Tabs
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import FolderIcon from '@mui/icons-material/Folder';
import ArticleIcon from '@mui/icons-material/Article';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import dynamic from 'next/dynamic';

// Import the MDEditor dynamically to avoid server-side rendering issues
const MDEditor = dynamic(() => import('@uiw/react-md-editor'), { ssr: false });
const MDPreview = dynamic(() => import('@uiw/react-md-editor').then((mod) => mod.default.Markdown), { ssr: false });

interface Exercise {
  path: string;
  instruction: string;
  input_file: string;
}

interface ValidationError {
  hasError: boolean;
  value: string;
}

interface ExerciseErrors {
  path: ValidationError;
  instruction: ValidationError;
  input_file: ValidationError;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

interface ExerciseProps {
  exercise: Exercise;
  errors: ExerciseErrors;
  index: number;
  onRemove: (index: number) => void;
  onChange: (index: number, field: keyof Exercise, value: string) => void;
  onDirectorySelection: (index: number, e: ChangeEvent<HTMLInputElement>) => void;
  onFileSelection: (index: number, field: 'instruction' | 'input_file', e: ChangeEvent<HTMLInputElement>) => void;
  isRemovable: boolean;
  isDirectorySupported: boolean;
}

// Styled components
const InputFileButton = styled('label')(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
  padding: '8px 16px',
  borderRadius: theme.shape.borderRadius,
  cursor: 'pointer',
  transition: 'all 0.2s ease-in-out',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  '&:hover': {
    backgroundColor: theme.palette.primary.dark,
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 8px rgba(0,0,0,0.15)',
  },
}));

const SelectedItem = styled(Paper)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(1.5),
  marginTop: theme.spacing(1.5),
  backgroundColor: theme.palette.grey[50],
  borderLeft: `4px solid ${theme.palette.primary.main}`,
  borderRadius: '4px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
}));

const SectionTitle = styled(Typography)(() => ({
  display: 'flex',
  alignItems: 'center',
  marginBottom: 1,
  color: 'text.primary',
  fontWeight: 500,
  '& svg': {
    marginRight: 1,
    color: 'primary.main',
  }
}));

const StyledCard = styled(Card)(() => ({
  borderRadius: '8px',
  boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
  transition: 'all 0.2s ease-in-out',
  overflow: 'visible',
  '&:hover': {
    boxShadow: '0 6px 16px rgba(0,0,0,0.1)',
  }
}));

// Tab Panel component
function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`instruction-tabpanel-${index}`}
      aria-labelledby={`instruction-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ pt: 2 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const ExerciseComponent: React.FC<ExerciseProps> = ({
  exercise,
  errors,
  index,
  onRemove,
  onChange,
  onDirectorySelection,
  onFileSelection,
  isRemovable,
  isDirectorySupported
}) => {
  // Get theme for styling
  
  // State for instruction editor tabs
  const [instructionTab, setInstructionTab] = useState<number>(0);
  
  // Function to handle tab change
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setInstructionTab(newValue);
  };
  
  // State for instruction markdown content
  const [instructionMarkdown, setInstructionMarkdown] = useState<string>(exercise.instruction || '');
  
  // Update markdown content when exercise.instruction changes
  React.useEffect(() => {
    setInstructionMarkdown(exercise.instruction || '');
  }, [exercise.instruction]);
  
  // Helper function to create a file input
  const createFileInput = (id: string, accept: string, label: string, onChange: (e: ChangeEvent<HTMLInputElement>) => void, icon: React.ReactNode) => (
    <>
      <input
        type="file"
        id={id}
        accept={accept}
        style={{ display: 'none' }}
        onChange={onChange}
      />
      <InputFileButton htmlFor={id}>
        {icon}
        <span style={{ marginLeft: '8px' }}>{label}</span>
      </InputFileButton>
    </>
  );

  return (
    <StyledCard sx={{ mb: 3, position: 'relative', overflow: 'visible' }}>
      <CardContent sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h5" component="h3" sx={{ 
            fontWeight: 'bold', 
            color: theme => theme.palette.primary.main,
            display: 'flex',
            alignItems: 'center',
          }}>
            <ArticleIcon sx={{ mr: 1 }} />
            Exercise {index + 1}
          </Typography>
          <IconButton 
            color="error" 
            onClick={() => onRemove(index)} 
            disabled={!isRemovable}
            size="medium"
            sx={{ 
              opacity: isRemovable ? 1 : 0.5,
              borderRadius: '8px',
              transition: 'all 0.2s ease',
              '&:hover': { 
                backgroundColor: isRemovable ? 'rgba(244, 67, 54, 0.1)' : 'transparent',
                transform: isRemovable ? 'scale(1.1)' : 'none'
              }
            }}
          >
            <DeleteIcon />
          </IconButton>
        </Box>
        <Divider sx={{ mb: 3 }} />
        
        <Grid container spacing={4}>
          <Grid item xs={12}>
            <SectionTitle variant="subtitle1" gutterBottom>
              <FolderIcon fontSize="small" />
              Exercise Directory
            </SectionTitle>
            
            <Paper sx={{ p: 3, borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
              {isDirectorySupported ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <input
                    type="file"
                    id={`directory-input-${index}`}
                    webkitdirectory="true"
                    directory="true"
                    style={{ display: 'none' }}
                    onChange={(e) => onDirectorySelection(index, e)}
                  />
                  <InputFileButton htmlFor={`directory-input-${index}`}>
                    <FolderIcon />
                    <span style={{ marginLeft: '8px' }}>Select Directory</span>
                  </InputFileButton>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2, textAlign: 'center' }}>
                    Choose the directory containing all files for this exercise
                  </Typography>
                  
                  {exercise.path && (
                    <SelectedItem sx={{ width: '100%', mt: 2 }}>
                      <FolderIcon color="primary" sx={{ mr: 1 }} />
                      <Box sx={{ flex: 1 }}>
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontWeight: 500,
                            textOverflow: 'ellipsis',
                            overflow: 'hidden',
                            whiteSpace: 'nowrap'
                          }}
                          title={exercise.path}
                        >
                          {exercise.path}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Selected directory (full path)
                        </Typography>
                      </Box>
                    </SelectedItem>
                  )}
                  
                  {errors.path.hasError ? (
                    <FormHelperText error sx={{ mt: 1 }}>{errors.path.value}</FormHelperText>
                  ) : (
                    <FormHelperText sx={{ mt: 1 }}>Directory where exercise files are located</FormHelperText>
                  )}
                </Box>
              ) : (
                <Box>
                  <TextField
                    fullWidth
                    label="Full Directory Path"
                    placeholder="/path/to/exercise/folder"
                    variant="outlined"
                    value={exercise.path}
                    onChange={(e) => onChange(index, 'path', e.target.value)}
                    error={errors.path.hasError}
                    helperText={errors.path.hasError ? errors.path.value : 'Enter the full directory path where exercise files are located'}
                    InputLabelProps={{ shrink: true }}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        borderRadius: '8px',
                        transition: 'all 0.2s',
                        '&:hover': {
                          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                        },
                        '&.Mui-focused': {
                          boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                        }
                      }
                    }}
                  />
                </Box>
              )}
            </Paper>
          </Grid>
          
          {exercise.path && (
            <Grid item xs={12}>
              <Alert 
                severity="info" 
                icon={<FolderIcon fontSize="inherit" />}
                sx={{ 
                  mb: 2, 
                  borderRadius: '8px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                  '& .MuiAlert-icon': {
                    color: theme => theme.palette.primary.main
                  }
                }}
              >
                <Typography 
                  variant="body1" 
                  sx={{ 
                    fontWeight: 500,
                    textOverflow: 'ellipsis', 
                    overflow: 'hidden', 
                    whiteSpace: 'nowrap' 
                  }}
                  title={exercise.path}
                >
                  <strong>Directory selected:</strong> {exercise.path}
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
                  You can now select files from this directory for instructions and inputs
                </Typography>
              </Alert>
            </Grid>
          )}
          
          <Grid item xs={12}>
            <SectionTitle variant="subtitle1" gutterBottom>
              <ArticleIcon fontSize="small" />
              Exercise Instructions
            </SectionTitle>
            
            <Paper sx={{ p: 0, borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
              <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'grey.50' }}>
                <Tabs 
                  value={instructionTab} 
                  onChange={handleTabChange} 
                  aria-label="instruction tabs"
                  variant="fullWidth"
                  sx={{
                    '& .MuiTab-root': {
                      py: 1.5,
                      fontWeight: 500,
                      transition: 'all 0.2s',
                      '&.Mui-selected': {
                        fontWeight: 600,
                        backgroundColor: 'rgba(0,0,0,0.02)'
                      },
                      '&:hover': {
                        backgroundColor: 'rgba(0,0,0,0.05)'
                      }
                    }
                  }}
                >
                  <Tab icon={<EditIcon />} iconPosition="start" label="Edit" />
                  <Tab icon={<VisibilityIcon />} iconPosition="start" label="Preview" />
                  <Tab icon={<ArticleIcon />} iconPosition="start" label="Upload File" />
                </Tabs>
              </Box>
              
              <TabPanel value={instructionTab} index={0}>
                <MDEditor
                  value={instructionMarkdown}
                  onChange={(value) => {
                    setInstructionMarkdown(value || '');
                    // Update the parent component with the markdown content
                    onChange(index, 'instruction', value || '');
                  }}
                  height={320}
                  preview="edit"
                  highlightEnable={true}
                  enableScroll={true}
                  textareaProps={{
                    placeholder: 'Write your exercise instructions here using Markdown...\n\n# Exercise Title\n\n## Description\nDescription of what the exercise is about.\n\n## Tasks\n- Task 1\n- Task 2\n\n## Requirements\n* Requirement 1\n* Requirement 2'
                  }}
                />
              </TabPanel>
              
              <TabPanel value={instructionTab} index={1}>
                <Box sx={{ 
                  p: 3, 
                  minHeight: '320px', 
                  backgroundColor: '#fff',
                  overflowY: 'auto',
                  border: '1px solid #eee'
                }}>
                  {instructionMarkdown ? (
                    <MDPreview source={instructionMarkdown} />
                  ) : (
                    <Box 
                      sx={{ 
                        height: '100%', 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        color: 'text.secondary',
                        flexDirection: 'column',
                        p: 4
                      }}
                    >
                      <VisibilityIcon sx={{ fontSize: 40, opacity: 0.5, mb: 2 }} />
                      <Typography variant="body1" sx={{ opacity: 0.7 }}>
                        Your preview will appear here once you&apos;ve added content in the Edit tab
                      </Typography>
                    </Box>
                  )}
                </Box>
              </TabPanel>
              
              <TabPanel value={instructionTab} index={2}>
                <Box sx={{ 
                  p: 3, 
                  minHeight: '320px', 
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Box sx={{ width: '100%', maxWidth: 500, textAlign: 'center' }}>
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="h6" gutterBottom>
                        Upload Markdown Instructions
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                        Select a markdown file containing the exercise instructions
                      </Typography>
                      
                      {createFileInput(
                        `instruction-file-${index}`,
                        '.md',
                        'Select Markdown File',
                        (e) => onFileSelection(index, 'instruction', e),
                        <ArticleIcon />
                      )}
                    </Box>
                    
                    {exercise.instruction && (
                      <Box sx={{ mt: 3 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          Selected File:
                        </Typography>
                        <SelectedItem>
                          <ArticleIcon color="primary" sx={{ mr: 1 }} />
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {exercise.instruction.length > 30 
                              ? `${exercise.instruction.substring(0, 30)}...` 
                              : exercise.instruction}
                          </Typography>
                        </SelectedItem>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          The content has been loaded into the editor. You can switch to the Edit tab to make changes.
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Box>
              </TabPanel>
            </Paper>
            
            {errors.instruction.hasError ? (
              <FormHelperText error sx={{ mt: 1 }}>{errors.instruction.value}</FormHelperText>
            ) : (
              <FormHelperText sx={{ mt: 1 }}>Markdown instructions for the exercise</FormHelperText>
            )}
          </Grid>
          
          <Grid item xs={12}>
            <SectionTitle variant="subtitle1" gutterBottom>
              <UploadFileIcon fontSize="small" />
              Input File
            </SectionTitle>
            
            <Paper sx={{ p: 3, borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                {createFileInput(
                  `input-file-${index}`,
                  '',
                  'Select Input File',
                  (e) => onFileSelection(index, 'input_file', e),
                  <UploadFileIcon />
                )}
                
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2, textAlign: 'center' }}>
                  Select the main file that users will work with in this exercise
                </Typography>
                
                {exercise.input_file && (
                  <SelectedItem sx={{ width: '100%', mt: 2 }}>
                    <UploadFileIcon color="primary" sx={{ mr: 1 }} />
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>{exercise.input_file}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {exercise.path ? `From: ${exercise.path}` : 'Input file selected'}
                      </Typography>
                    </Box>
                  </SelectedItem>
                )}
              </Box>
              
              {errors.input_file.hasError ? (
                <FormHelperText error sx={{ mt: 1 }}>{errors.input_file.value}</FormHelperText>
              ) : (
                <FormHelperText sx={{ mt: 1 }}>This file will be provided to users to work on</FormHelperText>
              )}
            </Paper>
          </Grid>
          
        </Grid>
      </CardContent>
    </StyledCard>
  );
};

export default ExerciseComponent;