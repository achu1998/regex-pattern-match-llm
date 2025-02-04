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


@api_view(['GET'])
def get_stored_data(request):
    return JsonResponse({'data': data_store})

def is_valid_regex(pattern):
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False
    
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
    prompt = f"question: Which is the Replacement word? Replacement word must be a single word strictly! Give single correct word without changing spelling! Do not return entire sentence or empty! context: {description}"   
    

    # Generate response
    response = generator(prompt, max_length=100, num_return_sequences=1)

    # Extract and clean up output
    replacement_word = response[0]['generated_text'].strip()
    
    return replacement_word

def generate_regex_from_desc(description, model="codellama"):
    print("Waiting for Regex Response...")
    prompt = (
        f"I want you to act as a regex generator. Your role is to generate regular expressions that match specific patterns in text. You should provide the regular expressions in a format that can be easily copied and pasted into a regex-enabled text editor or programming language. Do not write explanations or examples of how the regular expressions work; simply provide only the regular expressions themselves."
        f"My first prompt is to generate a regular expression that strictly matches description."
        f"Description: {description}"
        f"An important rule is that names will have first and last name! Example : John Doe. So regex should consider John as first name and Doe as last name!"
        f"Make sure all the cases are covered! Remove case-insensitive flag (?i). Regex are case sensitive"
        f"Return the response strictly in JSON format as: {{'regex_pattern': '<your_regex>'}} and no other explanation in the response."
    )
    
    response = ollama.chat(model=model, messages=[
        {"role": "system", "content": prompt},
        # {"role": "user", "content": prompt}
    ])

    try:
        # Extract JSON response from the LLM output
        regex_data = json.loads(response["message"]["content"])
        return regex_data.get("regex_pattern", "")
    except json.JSONDecodeError:
        # Fallback: Extract regex manually if LLM doesn't return proper JSON
        regex_match = re.search(r'"regex_pattern":\s*"([^"]+)"', response["message"]["content"])
        return regex_match.group(1).strip() if regex_match else response["message"]["content"]
    
    

def verifyRegex(description, regex,  model="deepseek-r1:1.5b"):
    print("Verifying Regex Response...")
    prompt = (
        f"You are an regex verifier. Check whether the regex {regex} strictly matches the find part of description: {description} and verify it. (?i) should not be present in regex. Case-sensitive."
        f"An important rule is that names will have first and last name! Example : John Doe. So regex should consider John as first name and Doe as last name!"
        f"Return strictly as 'Yes' or 'No'"      
    )
    
    response = ollama.chat(model=model, messages=[
        {"role": "system", "content": prompt},
    ])
    
    # Generate response
    ans = response["message"]["content"]
    if "</think>" in ans:
        ans = ans.split("</think>")[-1].strip()
    print("Regex Verification success - ", ans)   
    return ans

def verifyReplace(description, replace,  model="deepseek-r1:1.5b"):
    print("Verifying Replacement Response...")
    prompt = (
        f"You are an context verifier. Check whether the replacement word {replace} matches the replace part of description: {description} and verify it. Replacement word must be a single word strictly! Case-sensitive. No special characters or spaces!"
        f"Return strictly as 'Yes' or 'No'"      
    )
    
    response = ollama.chat(model=model, messages=[
        {"role": "system", "content": prompt},
    ])
    
    # Generate response
    ans = response["message"]["content"]
    if "</think>" in ans:
        ans = ans.split("</think>")[-1].strip()
    print("Replace Verification success - ", ans)   
    return ans

# description = "Find hex color ending with '00' in the HEX column and replace them with 'REDACTED'."
# regex = "{'regex_pattern':'#[a-zA-Z0-9]{6}00'}"
# verify(description, regex)