from django.shortcuts import render
import os
import pandas as pd
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from django.http import JsonResponse
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from transformers import pipeline
import ollama
import re

# Create your views here.

# Store JSON data
data_store = []
enable_verfiy = False

@api_view(['POST'])
def upload_excel(request):
    # Specify that this view accepts multipart/form-data (for file uploads)
    parser_classes = [MultiPartParser]

    # Retrieve the uploaded file from the request
    file = request.FILES.get('file')

    # If no file is uploaded, return an error response
    if not file:
        return Response({'error': 'No file uploaded'}, status=400)

    # Save the file to the default storage and get its path
    file_path = default_storage.save(file.name, file)
    full_path = os.path.join(default_storage.location, file_path)

    try:
        # Read the file into a Pandas DataFrame based on the file extension
        if file.name.endswith('.csv'):
            df = pd.read_csv(full_path, delimiter=None, engine='python')  # Automatically detects delimiters
        elif file.name.endswith('.xls') or file.name.endswith('.xlsx'):
            df = pd.read_excel(full_path)
        else:
            # Return an error response if the file format is unsupported
            return Response({'error': 'Invalid file format. Only CSV and Excel files are supported'}, status=400)

        # Convert the DataFrame into a list of dictionaries (JSON-like structure) and store it globally
        global data_store
        data_store = df.to_dict(orient='records')  # Store JSON data for further processing

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Logs full error traceback to the console for debugging
        return Response({'error': str(e)}, status=500)  # Return a generic error response in case of an exception

    # Delete the uploaded file after processing to free up storage
    default_storage.delete(file_path)
    # Return the processed data as JSON response
    return JsonResponse({'data': data_store})
    
@csrf_exempt
def generate_regex(request):
    """
    Takes user input text (natural language) and generates a regex pattern.
    """
    try:
        # Parse the JSON request body
        data = json.loads(request.body)
        user_prompt = data.get("user_prompt", "")
        print(user_prompt)

        # Validate user input
        if not user_prompt:
            return JsonResponse({"error": "User prompt is required"}, status=400)

        # Generate replacement word using LLM
        print("Waiting for Replacement Response...")
        retry = 1
        replacement_word = extract_context_replacement(user_prompt)
        print(f"Generated Replacement word: {replacement_word}")

        # Verify replacement word if verification is enabled
        if enable_verfiy:
            result = verifyReplace(user_prompt, replacement_word)
            while "No" in result or "Yes" not in result:
                if retry == 4:  # Limit retries to prevent infinite loops
                    return JsonResponse({"error": "Invalid response"}, status=400)
                print(f"Retrying Replacement word - Attempt {retry}, Incorrect Replace word!")
                retry += 1
                replacement_word = extract_context_replacement(user_prompt)
                print(f"Generated Replacement word: {replacement_word}")
                result = verifyReplace(user_prompt, replacement_word)
        
        # Generate regex pattern based on user input
        retry = 1
        regex_pattern_full = generate_regex_from_desc(user_prompt)
        print(f"Generated Regex: {regex_pattern_full}")

        # Verify regex if verification is enabled
        if enable_verfiy:
            result = verifyRegex(user_prompt, regex_pattern_full)
            while "No" in result or "Yes" not in result:
                if retry == 4:  # Limit retries to prevent infinite loops
                    return JsonResponse({"error": "Invalid response"}, status=400)
                print(f"Retrying Regex - Attempt {retry}, Incorrect Regex!")
                retry += 1
                regex_pattern_full = generate_regex_from_desc(user_prompt)
                print(f"Generated Regex: {regex_pattern_full}")
                result = verifyRegex(user_prompt, regex_pattern_full)

        # Return generated regex pattern and replacement word
        return JsonResponse({"regex_pattern": regex_pattern_full, "replace": replacement_word})

    except Exception as e:
        # Return a server error response with the error message
        return JsonResponse({"error": str(e)}, status=500)
      


# Load the pre-trained FLAN-T5 model
generator = pipeline("text2text-generation", model="google/flan-t5-large")

def extract_context_replacement(description):
    """
    Extracts a single replacement word from the given description using a language model.
    """
    # Construct a prompt that explicitly asks for a single replacement word
    prompt = (f"question: Which is the Replacement word from the context? "
              f"Replacement word must be a single word strictly! Replacement word replaces the find! "
              f"context: {description}")

    # Generate response using the model
    response = generator(prompt, max_length=100, num_return_sequences=1)

    # Extract and clean up output
    if response and isinstance(response, list) and 'generated_text' in response[0]:
        replacement_word = response[0]['generated_text'].strip()
    else:
        replacement_word = ""  # Default to an empty string if response is invalid

    return replacement_word

def generate_regex_from_desc(description, model="mistral"):
    """
    Generates a regex pattern from a natural language description using an LLM model.
    """
    print("Waiting for Regex Response...")
    
    prompt = (
        f"I want you to act as a regex generator. Your role is to convert the following natural language query to a regular expression with valid word boundary on both ends '\b <your_regex> \b' (regex):{description}"
        f"You should provide the regular expressions in a format that can be easily copied and pasted into a regex-enabled text editor or programming language. Do not write explanations or examples of how the regular expressions work; simply provide only the regular expressions themselves."
        f"Provide only the regex pattern as your response, without any explanation or additional text. Regex should be strictly valid without double backslashes or domain matching issues!"
        f"Return the response strictly in JSON format as: {{'regex_pattern': '\b<your_regex>\b'}} and no other explanation in the response. Regex should have word boundary on both sides!"
    )
    
    response = ollama.chat(model=model, messages=[
        {"role": "user", "content": prompt}
    ])

    try:
        # Extract JSON response from the model
        regex_data = json.loads(response["message"]["content"])
        return regex_data.get("regex_pattern", "")

    except (json.JSONDecodeError, KeyError):
        # Fallback: Extract regex manually if JSON parsing fails
        regex_match = re.search(r'"regex_pattern":\s*"([^"]+)"', response["message"]["content"])
        return regex_match.group(1).strip() if regex_match else response["message"]["content"]


def verifyRegex(description, regex, model="mistral"):
    """
    Verifies if the given regex strictly matches the 'find' part of the description.
    The model must return only 'Yes' or 'No'.
    """
    print("Verifying Regex Response...")

    # Constructing the prompt for verification
    prompt = (
        f"I want you to act as a regex verifier. Your role is to check whether the regex {regex} strictly matches the find part of description: {description} and verify it."
        f"You should only return strictly as 'Yes' or 'No'. No other explanation!"  
        f"Do not write explanations or examples of how the regular expressions work; simply provide only 'Yes' if regex matches, 'No' if it doesn't match."    
    )
    
    response = ollama.chat(model=model, messages=[
        {"role": "user", "content": prompt},
    ])
    
    # Generate response
    ans = response["message"]["content"].strip()
    print("Regex Verification success - ", ans)   
    return ans

def verifyReplace(description, replace,  model="mistral"):
    print("Verifying Replacement Response...")
    
    # Constructing the prompt for verification
    prompt = (
        f"I want you to act as a context verifier. Your role is to check whether the replacement word {replace} matches the replace part of description: {description} and verify it. You should remember that replacement word must be a single word strictly."
        f"You should only return strictly as 'Yes' or 'No'. No other explanation!" 
        f"Do not write explanations or examples; simply provide only 'Yes' if replacement word matches, 'No' if it doesn't match."  
    )
    
    response = ollama.chat(model=model, messages=[
        {"role": "user", "content": prompt},
    ])
    
    # Generate response
    ans = response["message"]["content"].strip()
    print("Replace Verification success - ", ans)   
    return ans