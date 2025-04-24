# To install dependencies
1. `conda create --name <myenv> --file conda_requirements.txt`
2. `conda activate <myenv>`
3. `pip install -r requirements.txt`

# To use
1. Add appropriate api keys to config_api_keys.
2. Add Groq api key for LLM call in `example_OAI_CONGIG_LIST` and rename it as `OAI_CONGIG_LIST`.