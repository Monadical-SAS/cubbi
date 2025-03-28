
// types/index.ts
export interface Container {
    navigator: string;
    provider: string;
    model: string;
    provider_params: string;
}

export interface Exercise {
    path: string;
    instruction: string;
    input_file: string;
}

export interface ConfigData {
    containers: Container[];
    exercises: Exercise[];
    output_dir: string;
}

export interface ValidationError {
    hasError: boolean;
    value: string;
}

export interface ContainerErrors {
    navigator: ValidationError;
    provider: ValidationError;
    model: ValidationError;
    provider_params: ValidationError;
}

export interface ExerciseErrors {
    path: ValidationError;
    instruction: ValidationError;
    input_file: ValidationError;
}

// Add declaration for js-yaml library
declare module 'js-yaml' {
    export function dump(obj: unknown, options?: unknown): string;
    export function load(str: string, options?: unknown): unknown;
}

// Add type definitions for directory attribute in file inputs
// These extensions are already provided by the environment
