
def get_goose_config(model="anthropic/claude-3.5-sonnet", provider="openrouter", aws_profile="us-west-2"):
    """
    Generate a basic Goose configuration in YAML format as a Python string.
    
    Args:
        model (str): The AI model to use
        provider (str): The provider to use
        aws_profile (str): AWS profile/region
        
    Returns:
        str: Formatted YAML configuration as a string
    """
    config_content = f'''GOOSE_PROVIDER: {provider}
GOOSE_MODEL: {model}
extensions:
  developer:
    enabled: true
    name: developer
    timeout: 300
    type: builtin
AWS_PROFILE: {aws_profile}
'''
    return config_content