import json
import os

# Formatting all the data into the output format we want (so that our LLM can read it)
def format_properties(properties_dict):
    propTexts = []
    if not properties_dict:
        return " It has no defined properties."
    for propName, propDetails in properties_dict.items():
        propType = propDetails.get('type', 'any')
        description = f"Property '{propName}' is type '{propType}'."
        if propType == 'array':
            items = propDetails.get('items', {})
            itemType = items.get('type')
            itemRef = items.get('$ref')
            if itemRef:
                refName = itemRef.split('/')[-1]
                description += f" It is an array of '{refName}'."
            elif itemType:
                 description += f" It is an array of type '{itemType}'."
            else:
                 description += " It is an array of unspecified items."
        elif '$ref' in propDetails:
             refName = propDetails['$ref'].split('/')[-1]
             description = f"Property '{propName}' references model '{refName}'."
        # Add description/example if available
        if propDetails.get('description'):
             # Limit description length slightly
             desc_text = propDetails['description'].replace('\n', ' ').strip()
             # if len(desc_text) > 150: desc_text = desc_text[:147] + "..."
             description += f" Description: {desc_text}"
        if propDetails.get('example'):
             description += f" Example: {propDetails['example']}"
        propTexts.append(description)
    return " Properties include: " + " ".join(propTexts)


def format_bundled_models(modelDict):
    modelTexts = []
    if not modelDict:
        return ""
    for modelName, modelDetails in modelDict.items():
        model_type = modelDetails.get('type', 'object')
        summary = modelDetails.get('summary', '')
        # Add model's own description if present
        model_desc = modelDetails.get('description', '').replace('\n', ' ').strip()

        text = f"Includes definition for '{modelName}' (type: {model_type})."
        if summary and summary.strip():
            text += f" Summary: {summary.strip()}"
        if model_desc:
             text += f" Description: {model_desc}"

        properties = modelDetails.get('properties')
        if properties:
             text += format_properties(properties)
        else:
             text += " It has no defined properties."
        modelTexts.append(text)
    return " Bundled model definitions: " + " ".join(modelTexts)

# Formatting the request parameters into text so it's easier for the llm
def format_request_parameters(request_dict):
    """Formats request parameters (path, query, headers, cookie) into text."""
    if not request_dict:
        return ""

    param_texts = []

    # Process Path Parameters
    path_params = request_dict.get('path', [])
    if path_params:
        path_texts = ["Path Parameters:"]
        for param in path_params:
            name = param.get('name', 'unnamed')
            desc = param.get('description', '')
            ptype = param.get('schema', {}).get('type', 'string')
            req = 'required' if param.get('required') else 'optional'
            path_texts.append(f"- {name} ({ptype}, {req}): {desc}")
        param_texts.append(" ".join(path_texts))

    # Process Query Parameters (similar structure)
    query_params = request_dict.get('query', [])
    if query_params:
        query_texts = ["Query Parameters:"]
        for param in query_params:
            name = param.get('name', 'unnamed')
            desc = param.get('description', '')
            ptype = param.get('schema', {}).get('type', 'string')
            req = 'required' if param.get('required') else 'optional'
            query_texts.append(f"- {name} ({ptype}, {req}): {desc}")
        param_texts.append(" ".join(query_texts))

    # Process Header Parameters (similar structure)
    header_params = request_dict.get('headers', [])
    if header_params:
        header_texts = ["Header Parameters:"]
        for param in header_params:
             name = param.get('name', 'unnamed')
             desc = param.get('description', '')
             ptype = param.get('schema', {}).get('type', 'string')
             req = 'required' if param.get('required') else 'optional'
             header_texts.append(f"- {name} ({ptype}, {req}): {desc}")
        param_texts.append(" ".join(header_texts))

    # Process Cookie Parameters (similar structure)
    cookie_params = request_dict.get('cookie', [])
    if cookie_params:
        cookie_texts = ["Cookie Parameters:"]
        for param in cookie_params:
             name = param.get('name', 'unnamed')
             desc = param.get('description', '')
             ptype = param.get('schema', {}).get('type', 'string')
             req = 'required' if param.get('required') else 'optional'
             cookie_texts.append(f"- {name} ({ptype}, {req}): {desc}")
        param_texts.append(" ".join(cookie_texts))

    # Process Request Body (if defined, often in request['body'] or request['contents'])
    # Note: OpenAPI 2.0 (spec: oas2) uses 'parameters' array with 'in: body'
    # OpenAPI 3.x uses 'requestBody'. Adapt if needed based on actual spec used.
    request_body_schema = None
    request_body_content = request_dict.get('body', {}).get('contents', []) # Check common Stoplight structure
    if request_body_content and isinstance(request_body_content, list):
        # Assuming first content describes the body
        body_media_type = request_body_content[0].get('mediaType', 'unknown')
        request_body_schema = request_body_content[0].get('schema')
        if request_body_schema:
             body_desc = format_properties(request_body_schema.get('properties'))
             param_texts.append(f"Request Body ({body_media_type}):{body_desc}")

    return "\n".join(param_texts)


def format_responses(responses_list):
    """Formats the list of possible API responses into text."""
    if not responses_list:
        return "No responses defined."

    response_texts = ["Responses:"]
    for response in responses_list:
        code = response.get('code', 'unknown')
        desc = response.get('description', 'No description.')
        res_text = f"- Code {code}: {desc}"

        contents = response.get('contents', [])
        if contents and isinstance(contents, list):
            # Usually only one content type per response code, take the first
            content = contents[0]
            media_type = content.get('mediaType', 'unknown')
            schema = content.get('schema')
            if schema:
                schema_desc = format_properties(schema.get('properties'))
                res_text += f" Response Body ({media_type}):{schema_desc}"
            else:
                res_text += f" Response Body ({media_type}): No schema defined."
        else:
            res_text += " No response body defined." # Or specific body if not schema-based

        response_texts.append(res_text)

    return "\n".join(response_texts)


# Processing a specific json entry into a RAG text format
def process_api_doc_entry(entry):

    entryType = entry.get('type', 'unknown')
    # Use top-level name/summary first
    name = entry.get('name', 'Unnamed Document')
    summary = entry.get('summary', '')
    uri_for_warning = entry.get('uri', entry.get('_id', 'unknown_source'))

    contentParts = [f"Title: {name}"]
    if summary and summary.strip():
        contentParts.append(f"Summary: {summary.strip()}")

    data = entry.get('data', None)
    textContent = ""

    if entryType == 'article' and isinstance(data, str):
        textContent = data # Keep markdown as is

    elif entryType == 'model' and isinstance(data, dict):
        schemaType = data.get('type', 'object')
        modelDescription = f"This defines the data model '{name}', which is a '{schemaType}'."
        properties = data.get('properties')
        modelDescription += format_properties(properties)
        bundled = entry.get('bundledModels')
        modelDescription += format_bundled_models(bundled)
        textContent = modelDescription

    elif entryType == 'http_operation' and isinstance(data, dict):
        # Extract details specific to the HTTP operation
        method = data.get('method', 'UNKNOWN_METHOD').upper()
        path = data.get('path', 'unknown_path')
        op_desc = data.get('description', '')
        op_summary = data.get('summary', '') # Can be different from top-level summary

        operation_details = [f"API Operation: {method} {path}"]
        if op_summary and op_summary.strip():
            operation_details.append(f"Operation Summary: {op_summary.strip()}")
        if op_desc and op_desc.strip():
             operation_details.append(f"Operation Description: {op_desc.strip()}")

        # Format Request
        request_info = format_request_parameters(data.get('request'))
        if request_info:
            operation_details.append(f"Request Details:\n{request_info}")

        # Format Responses
        response_info = format_responses(data.get('responses'))
        if response_info:
             operation_details.append(f"Response Details:\n{response_info}")

        # Add Bundled Models specific to this operation if any
        bundled = entry.get('bundledModels')
        bundled_info = format_bundled_models(bundled)
        if bundled_info:
             operation_details.append(f"Referenced Model Definitions:\n{bundled_info}")

        textContent = "\n".join(operation_details)


    elif isinstance(data, str): # Fallback
         print(f"Warning: Entry '{name}' ({uri_for_warning}) has unrecognized type '{entryType}' but string data. Using data directly.")
         textContent = data
    else:
        print(f"Warning: Could not extract primary content for '{name}' ({uri_for_warning}) of type '{entryType}'. Data: {data}")
        textContent = "Content could not be processed."

    contentParts.append(f"Content: {textContent.strip()}")
    fullText = "\n\n".join(contentParts)

    return fullText.strip()



if __name__ == "__main__":
    try:
        with open("ScrapingStuff/storedData/allDocumentation.json", 'r', encoding='utf-8') as f:
            jsonDat = json.load(f)
    except FileNotFoundError:
        print("Error: Input file 'ScrapingStuff/storedData/allDocumentation.json' not found.")
        exit()
    except json.JSONDecodeError:
         print("Error: Could not decode JSON from input file.")
         exit()

    if not isinstance(jsonDat, dict):
        print(f"Error: Expected a dictionary in the JSON file, but got {type(jsonDat)}.")
        exit()

    processedDocs = {}
    print(f"Processing {len(jsonDat)} Api Docs entries...")
    count = 0
    for link, entry_object in jsonDat.items():
        if isinstance(entry_object, dict):
            processed = process_api_doc_entry(entry_object)
            if processed:
                processedDocs[link] = processed
                count += 1
        else:
             print(f"Warning: Skipping entry with key '{link}' because its value is not a dictionary ({type(entry_object)}).")

    print(f"Successfully processed {count} entries.")

    try:
        output_filepath = "ScrapingStuff/storedData/RagFormattedData.json"
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(processedDocs, f, indent=4)
        print(f"\nSuccessfully saved processed data to {output_filepath}")
    except IOError as e:
        print(f"\nError: Could not write output file to {output_filepath}: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during saving: {e}")