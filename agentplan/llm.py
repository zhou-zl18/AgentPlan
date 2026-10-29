"""Azure OpenAI calls, multiprocessing, and token accounting."""
import base64
import copy
import time
from multiprocessing import Pool
from functools import partial
from tqdm import tqdm
from openai import AzureOpenAI
from .config import AZURE_API_KEY, AZURE_API_VERSION, AZURE_ENDPOINT

LLM_USAGE = {
    'gpt-3.5-turbo': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0},
    'gpt-4o-mini': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0},
    'gpt-4o': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0},
}

def get_completion(prompt, model='gpt-4o-mini', temperature=0, use_json=False): 
    global LLM_USAGE
    if use_json:
        response_format = 'json_object'
    else:
        response_format = 'text'
        
    # if prompt is str
    if isinstance(prompt, str):
        messages = [{"role": "user", "content": prompt}]
    elif isinstance(prompt, list):
        messages = prompt
        assert messages[-1]['role'] == 'user'
    else:
        print(prompt)
        raise ValueError("Invalid prompt. Prompt must be a string or a list of strings.")

    client = AzureOpenAI(
        api_key = AZURE_API_KEY,
        api_version = AZURE_API_VERSION,
        azure_endpoint = AZURE_ENDPOINT,
    )
    if model == 'gpt-3.5-turbo':
        azure_model = 'gpt-35-turbo'
    elif model == 'gpt-4o-mini':
        azure_model = 'gpt-4o-mini'
    elif model == 'gpt-4o':
        azure_model = 'gpt-4o'
    else:
        raise ValueError(f"Invalid model: {model}")
    
    for attempt in range(10):
        try:
            response = client.chat.completions.create(
                response_format={ "type": response_format},
                model=azure_model,
                messages=messages,
                temperature=temperature,
            )
            break
        except Exception as e:
            print(f"Error on attempt {attempt + 1}/10: {str(e)}")
            time.sleep(30)
    
    # update usage
    LLM_USAGE[model]['completion_tokens'] += response.usage.completion_tokens
    LLM_USAGE[model]['prompt_tokens'] += response.usage.prompt_tokens
    LLM_USAGE[model]['total_tokens'] += response.usage.total_tokens
            
    return response.choices[0].message.content

def get_completion_with_usage(prompt, **kwargs):
    result = get_completion(prompt, **kwargs)
    return result, LLM_USAGE

def get_multiple_completion(prompts, model='gpt-3.5-turbo', temperature=0, num_cpus=64, use_tqdm=False):
    kwargs = {'model':model, 'temperature': temperature}
    fun_partial = partial(get_completion_with_usage, **kwargs)
    results = []
    usages = []
    
    with Pool(processes=num_cpus) as pool:
        result_iterator = pool.imap(fun_partial, prompts)
        if use_tqdm:
            with tqdm(total=len(prompts)) as t:
                for result, usage in result_iterator:
                    results.append(result)
                    usages.append(usage)
                    t.update()
        else:
            for result, usage in result_iterator:
                results.append(result)
                usages.append(usage)

    # 汇总所有进程的使用量
    global LLM_USAGE
    prev_usage = copy.deepcopy(LLM_USAGE)
    for usage in usages:
        for model in usage:
            for key in usage[model]:
                increase_usage = usage[model][key] - prev_usage[model][key]
                LLM_USAGE[model][key] += increase_usage
    
    time.sleep(3)
    return results

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_img_completion(prompt, image_path, model='gpt-4o', temperature=0.0):
    global LLM_USAGE
    client = AzureOpenAI(
        api_key = AZURE_API_KEY,
        api_version = AZURE_API_VERSION,
        azure_endpoint = AZURE_ENDPOINT,
    )
    base64_image = encode_image(image_path)
    messages = [{
        "role": "user", 
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
        ],
    }]

    for attempt in range(10):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4000,
                temperature=temperature,
            )
            break
        except Exception as e:
            print(f"Error on attempt {attempt + 1}/10: {str(e)}")
            time.sleep(30)

    # update usage
    LLM_USAGE[model]['completion_tokens'] += response.usage.completion_tokens
    LLM_USAGE[model]['prompt_tokens'] += response.usage.prompt_tokens
    LLM_USAGE[model]['total_tokens'] += response.usage.total_tokens

    return response.choices[0].message.content
