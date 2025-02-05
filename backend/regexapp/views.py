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
    parser_classes = [MultiPartParser]
    file = request.FILES.get('file')

    if not file:
        return Response({'error': 'No file uploaded'}, status=400)

    file_path = default_storage.save(file.name, file)
    full_path = os.path.join(default_storage.location, file_path)

    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(full_path, delimiter=None, engine='python')
        elif file.name.endswith('.xls') or file.name.endswith('.xlsx'):
            df = pd.read_excel(full_path)
        else:
            return Response({'error': 'Invalid file format. Only CSV and Excel files are supported'}, status=400)

        global data_store
        data_store = df.to_dict(orient='records')  # Store JSON data
    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Logs full error traceback to the console
        return Response({'error': str(e)}, status=500)


    default_storage.delete(file_path)
    return JsonResponse({'data': data_store})
    
@csrf_exempt
def generate_regex(request):
    """
    Takes user input text (natural language) and generates a regex pattern.
    """
    try:
        data = json.loads(request.body)
        user_prompt = data.get("user_prompt", "")
        print(user_prompt)

        if not user_prompt:
            return JsonResponse({"error": "User prompt is required"}, status=400)

        # Generate regex using LLM
        print("Waiting for Replacement Response...")
        retry = 1
        replacement_word = extract_context_replacement(user_prompt)
        print(f"Generated Replacement word: {replacement_word}")
        if enable_verfiy:
            result = verifyReplace(user_prompt, replacement_word)
            while ("No" in result or "Yes" not in result) :
                if retry == 4: return JsonResponse({"error": "Invalid response"}, status=400)
                print("Retry for Replacement word - ", retry, " , Incorrect Replace word!")
                retry += 1
                replacement_word = extract_context_replacement(user_prompt)
                print(f"Generated Replacement word: {replacement_word}")
                result = verifyReplace(user_prompt, replacement_word)
        
        # Get regex output
        retry = 1
        regex_pattern_full = generate_regex_from_desc(user_prompt)
        print(f"Generated Regex: {regex_pattern_full}")
        if enable_verfiy:
            result = verifyRegex(user_prompt, regex_pattern_full)
            while ("No" in result or "Yes" not in result) :
                if retry == 4: return JsonResponse({"error": "Invalid response"}, status=400)
                print("Retry for Regex - ", retry, " , Incorrect Regex!")
                retry += 1
                regex_pattern_full = generate_regex_from_desc(user_prompt)
                print(f"Generated Regex: {regex_pattern_full}")
                result = verifyRegex(user_prompt, regex_pattern_full)

        return JsonResponse({"regex_pattern": regex_pattern_full, "replace": replacement_word})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
      


# Load the pre-trained FLAN-T5 model
generator = pipeline("text2text-generation", model="google/flan-t5-large")

def extract_context_replacement(description):
    # Prompt that explicitly asks for the replacement word
    prompt = f"question: Which is the Replacement word from the context? Replacement word must be a single word strictly! Replacement word replaces the find! context: {description}"   

    # Generate response
    response = generator(prompt, max_length=100, num_return_sequences=1)

    # Extract and clean up output
    replacement_word = response[0]['generated_text'].strip()
    
    return replacement_word

def generate_regex_from_desc(description, model="mistral"):
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
        # Extract JSON response from the LLM output
        regex_data = json.loads(response["message"]["content"])
        return regex_data.get("regex_pattern", "")
    except json.JSONDecodeError:
        # Fallback: Extract regex manually if LLM doesn't return proper JSON
        regex_match = re.search(r'"regex_pattern":\s*"([^"]+)"', response["message"]["content"])
        return regex_match.group(1).strip() if regex_match else response["message"]["content"]
    
    

def verifyRegex(description, regex,  model="mistral"):
    print("Verifying Regex Response...")
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