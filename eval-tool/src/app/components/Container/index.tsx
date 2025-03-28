'use client'

// components/Container.tsx
import React, { useState } from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  TextField, 
  Grid, 
  IconButton,
  Box,
  Divider,
  Paper,
  Button,
  Chip,
  styled,
  Tooltip,
  FormHelperText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SettingsIcon from '@mui/icons-material/Settings';
import EditIcon from '@mui/icons-material/Edit';
import TuneIcon from '@mui/icons-material/Tune';

interface Container {
  navigator: string;
  provider: string;
  model: string;
  provider_params: string;
}

interface ValidationError {
  hasError: boolean;
  value: string;
}

interface ContainerErrors {
  navigator: ValidationError;
  provider: ValidationError;
  model: ValidationError;
  provider_params: ValidationError;
}

interface ContainerProps {
  container: Container;
  errors: ContainerErrors;
  index: number;
  onRemove: (index: number) => void;
  onChange: (index: number, field: keyof Container, value: string) => void;
  isRemovable: boolean;
}

// Styled components
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

const ParameterChip = styled(Chip)(({ theme }) => ({
  margin: '4px',
  borderRadius: '16px',
  backgroundColor: theme.palette.primary.main + '15',
  color: theme.palette.primary.main,
  fontWeight: 500,
  '& .MuiChip-deleteIcon': {
    color: theme.palette.primary.main + '80',
    '&:hover': {
      color: theme.palette.primary.main,
    }
  }
}));

const ContainerComponent: React.FC<ContainerProps> = ({
  container,
  errors,
  index,
  onRemove,
  onChange,
  isRemovable
}) => {
  // State for dialog
  const [dialogOpen, setDialogOpen] = useState<boolean>(false);
  const [paramName, setParamName] = useState<string>('');
  const [paramValue, setParamValue] = useState<string>('');
  const [paramError, setParamError] = useState<string>('');
  
  // Parse existing parameters
  const parseParams = (): Array<{ name: string, value: string }> => {
    if (!container.provider_params) return [];
    
    const params: Array<{ name: string, value: string }> = [];
    const paramPairs = container.provider_params.split(',');
    
    paramPairs.forEach(pair => {
      if (pair.trim()) {
        const [name, value] = pair.split('=');
        if (name && value) {
          params.push({ name: name.trim(), value: value.trim() });
        }
      }
    });
    
    return params;
  };
  
  // Convert params array back to string
  const stringifyParams = (params: Array<{ name: string, value: string }>): string => {
    return params.map(param => `${param.name}=${param.value}`).join(',');
  };
  
  // Handle adding or updating a parameter
  const handleAddParam = () => {
    if (!paramName.trim()) {
      setParamError('Parameter name is required');
      return;
    }
    
    if (!paramValue.trim()) {
      setParamError('Parameter value is required');
      return;
    }
    
    // Validate parameter name format
    if (!/^[a-zA-Z0-9_]+$/.test(paramName)) {
      setParamError('Parameter name can only contain letters, numbers, and underscores');
      return;
    }
    
    const currentParams = parseParams();
    const updatedParams = [...currentParams];
    
    // Check if we're editing an existing parameter
    const existingParamIndex = currentParams.findIndex(p => p.name === paramName);
    
    if (existingParamIndex >= 0) {
      // Update existing parameter
      updatedParams[existingParamIndex] = { name: paramName, value: paramValue };
    } else {
      // Add new parameter
      updatedParams.push({ name: paramName, value: paramValue });
    }
    
    // Update the container
    onChange(index, 'provider_params', stringifyParams(updatedParams));
    
    // Reset and close dialog
    setParamName('');
    setParamValue('');
    setParamError('');
    setDialogOpen(false);
  };
  
  // Handle removing a parameter
  const handleRemoveParam = (name: string) => {
    const currentParams = parseParams();
    const updatedParams = currentParams.filter(p => p.name !== name);
    onChange(index, 'provider_params', stringifyParams(updatedParams));
  };
  
  // Handle editing a parameter
  const handleEditParam = (name: string, value: string) => {
    setParamName(name);
    setParamValue(value);
    setDialogOpen(true);
  };
  
  const params = parseParams();
  
  return (
    <StyledCard sx={{ mb: 3, position: 'relative', overflow: 'visible' }}>
      <CardContent sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h5" component="h3" sx={{ 
            fontWeight: 'bold', 
            color: 'primary.main',
            display: 'flex',
            alignItems: 'center',
          }}>
            <SettingsIcon sx={{ mr: 1 }} />
            Container {index + 1}
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
              <EditIcon fontSize="small" />
              Navigator
            </SectionTitle>
            <Paper sx={{ p: 3, borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
              <FormControl fullWidth>
                <InputLabel id="navigator-label">Navigator</InputLabel>
                <Select
                  labelId="navigator-label"
                  value={container.navigator}
                  label="Navigator"
                  onChange={(e) => onChange(index, 'navigator', e.target.value)}
                  error={errors.navigator.hasError}
                  sx={{
                    borderRadius: '8px',
                    transition: 'all 0.2s',
                    '&:hover': {
                      boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                    },
                    '&.Mui-focused': {
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }
                  }}
                >
                  <MenuItem value="goose">Goose</MenuItem>
                  <MenuItem value="aider">Aider</MenuItem>
                </Select>
                <FormHelperText error={errors.navigator.hasError}>
                  {errors.navigator.hasError ? errors.navigator.value : 'Select the AI navigator to use'}
                </FormHelperText>
              </FormControl>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <SectionTitle variant="subtitle1" gutterBottom>
              <EditIcon fontSize="small" />
              Provider
            </SectionTitle>
            <Paper sx={{ p: 3, borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
              <FormControl fullWidth>
                <InputLabel id="provider-label">Provider</InputLabel>
                <Select
                  labelId="provider-label"
                  value={container.provider}
                  label="Provider"
                  onChange={(e) => onChange(index, 'provider', e.target.value)}
                  error={errors.provider.hasError}
                  sx={{
                    borderRadius: '8px',
                    transition: 'all 0.2s',
                    '&:hover': {
                      boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                    },
                    '&.Mui-focused': {
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }
                  }}
                >
                  <MenuItem value="openai">OpenAI</MenuItem>
                  <MenuItem value="litell">Litell</MenuItem>
                  <MenuItem value="anthropic">Anthropic</MenuItem>
                  <MenuItem value="azure">Azure</MenuItem>
                  <MenuItem value="google">Google</MenuItem>
                  <MenuItem value="aws">AWS</MenuItem>
                  <MenuItem value="openrouter">OpenRouter</MenuItem>
                </Select>
                <FormHelperText error={errors.provider.hasError}>
                  {errors.provider.hasError ? errors.provider.value : 'The provider of the LLM service'}
                </FormHelperText>
              </FormControl>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <SectionTitle variant="subtitle1" gutterBottom>
              <EditIcon fontSize="small" />
              Model
            </SectionTitle>
            <Paper sx={{ p: 3, borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
              <FormControl fullWidth>
                <InputLabel id="model-label">Model</InputLabel>
                <Select
                  labelId="model-label"
                  value={container.model}
                  label="Model"
                  onChange={(e) => onChange(index, 'model', e.target.value)}
                  error={errors.model.hasError}
                  sx={{
                    borderRadius: '8px',
                    transition: 'all 0.2s',
                    '&:hover': {
                      boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                    },
                    '&.Mui-focused': {
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }
                  }}
                >
                  <MenuItem value="gpt-4">GPT-4</MenuItem>
                  <MenuItem value="gpt-4-turbo">GPT-4 Turbo</MenuItem>
                  <MenuItem value="gpt-3.5-turbo">GPT-3.5 Turbo</MenuItem>
                  <MenuItem value="claude-3-opus">Claude 3 Opus</MenuItem>
                  <MenuItem value="claude-3-sonnet">Claude 3 Sonnet</MenuItem>
                  <MenuItem value="claude-3-haiku">Claude 3 Haiku</MenuItem>
                  <MenuItem value="claude-3.5-sonnet">Claude 3.5 Sonnet</MenuItem>
                  <MenuItem value="anthropic/claude-3.5-sonnet">Anthropic/Claude-3.5-Sonnet</MenuItem>
                  <MenuItem value="gemini-pro">Gemini Pro</MenuItem>
                  <MenuItem value="gemini-ultra">Gemini Ultra</MenuItem>
                </Select>
                <FormHelperText error={errors.model.hasError}>
                  {errors.model.hasError ? errors.model.value : 'The specific model to use'}
                </FormHelperText>
              </FormControl>
            </Paper>
          </Grid>
          
          <Grid item xs={12}>
            <SectionTitle variant="subtitle1" gutterBottom>
              <TuneIcon fontSize="small" />
              Provider Parameters
            </SectionTitle>
            <Paper sx={{ p: 3, borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Configure key-value parameters for the provider
                </Typography>
                <Button
                  variant="contained"
                  color="primary"
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={() => {
                    setParamName('');
                    setParamValue('');
                    setParamError('');
                    setDialogOpen(true);
                  }}
                  sx={{ 
                    borderRadius: '8px',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 4px 8px rgba(0,0,0,0.15)',
                    }
                  }}
                >
                  Add Parameter
                </Button>
              </Box>
              
              <Divider sx={{ mb: 2 }} />
              
              {params.length > 0 ? (
                <Box sx={{ 
                  display: 'flex', 
                  flexWrap: 'wrap', 
                  gap: 1, 
                  p: 2, 
                  borderRadius: '8px',
                  backgroundColor: 'grey.50'
                }}>
                  {params.map((param) => (
                    <Tooltip 
                      key={param.name} 
                      title={`${param.name} = ${param.value}`}
                      arrow
                    >
                      <ParameterChip
                        label={`${param.name} = ${param.value}`}
                        onDelete={() => handleRemoveParam(param.name)}
                        onClick={() => handleEditParam(param.name, param.value)}
                      />
                    </Tooltip>
                  ))}
                </Box>
              ) : (
                <Box sx={{ 
                  p: 3, 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center',
                  backgroundColor: 'grey.50',
                  borderRadius: '8px',
                  color: 'text.secondary'
                }}>
                  <Typography variant="body2">
                    No parameters added yet. Click &quot;Add Parameter&quot; to begin.
                  </Typography>
                </Box>
              )}
              
              {errors.provider_params.hasError && (
                <FormHelperText error sx={{ mt: 1 }}>
                  {errors.provider_params.value}
                </FormHelperText>
              )}
            </Paper>
          </Grid>
        </Grid>
      </CardContent>
      
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {paramName ? 'Edit Parameter' : 'Add Parameter'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ p: 1 }}>
            <TextField
              autoFocus
              fullWidth
              label="Parameter Name"
              value={paramName}
              onChange={(e) => setParamName(e.target.value)}
              margin="normal"
              placeholder="e.g., temperature, top_p"
              variant="outlined"
              InputLabelProps={{ shrink: true }}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Parameter Value"
              value={paramValue}
              onChange={(e) => setParamValue(e.target.value)}
              margin="normal"
              placeholder="e.g., 0.7, 0.9"
              variant="outlined"
              InputLabelProps={{ shrink: true }}
            />
            {paramError && (
              <FormHelperText error sx={{ mt: 1 }}>
                {paramError}
              </FormHelperText>
            )}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={() => setDialogOpen(false)} color="inherit">
            Cancel
          </Button>
          <Button onClick={handleAddParam} variant="contained" color="primary">
            {paramName ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </StyledCard>
  );
};

export default ContainerComponent;