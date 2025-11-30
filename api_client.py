import requests
import json

from config import AETHER_API_KEY

# Configuration
API_KEY = AETHER_API_KEY
BASE_URL = "https://aetherosint.site/cutieee/api.php"

def call_api(search_type, term):
    """
    Generic function to call the API.
    
    Args:
        search_type (str): 'mobile' or 'id_number'
        term (str): The phone number or ID number to search for
    
    Returns:
        dict: The JSON response from the API or an error dictionary.
    """
    params = {
        "key": API_KEY,
        "type": search_type,
        "term": term
    }
    
    print(f"Calling API for {search_type}: {term}...")
    
    try:
        # We verify=False because sometimes these sites have self-signed certs, 
        # but ideally it should be True. 
        # Given the domain looks like a small custom site, SSL might be tricky.
        # I'll stick to default verification first.
        response = requests.get(BASE_URL, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            try:
                # Try to parse as JSON first
                return response.json()
            except json.JSONDecodeError:
                # The API sometimes returns duplicate JSON objects concatenated
                # Try to extract the first valid JSON object
                text = response.text.strip()
                
                # Find the first complete JSON object
                # Look for the pattern {"data":[...]}
                try:
                    # Try to find where the first JSON object ends
                    brace_count = 0
                    first_json_end = 0
                    
                    for i, char in enumerate(text):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                first_json_end = i + 1
                                break
                    
                    if first_json_end > 0:
                        first_json = text[:first_json_end]
                        return json.loads(first_json)
                    else:
                        return {"error": "Failed to parse JSON", "raw_content": response.text}
                except Exception as e:
                    return {"error": f"Failed to decode JSON: {str(e)}", "raw_content": response.text}
        else:
            return {"error": f"API returned status code {response.status_code}", "raw_content": response.text}
            
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

def get_mobile_info(phone_number):
    return call_api("mobile", phone_number)

def get_aadhar_info(id_number):
    return call_api("id_number", id_number)

if __name__ == "__main__":
    print("--- AetherOSINT API Client ---")
    print("1. Search by Mobile Number")
    print("2. Search by Aadhar/ID Number")
    
    choice = input("Select an option (1 or 2): ").strip()
    
    if choice == "1":
        term = input("Enter Mobile Number: ").strip()
        result = get_mobile_info(term)
        print("\n--- Result ---")
        print(json.dumps(result, indent=4))
        
    elif choice == "2":
        term = input("Enter Aadhar/ID Number: ").strip()
        result = get_aadhar_info(term)
        print("\n--- Result ---")
        print(json.dumps(result, indent=4))
        
    else:
        print("Invalid choice. Exiting.")
