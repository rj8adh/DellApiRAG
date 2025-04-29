import json

jsonExampleData = [
    # Model Type Example API Data Thingie
    {
        "tagNames": [],
        "references": ["apiprotoLockingId", "apiprotoSoftwareId"],
        "deepReferences": ["apiprotoLockingId", "apiprotoSoftwareId"],
        "modelRefList": [],
        "_id": "6613de5068ed810012514844",
        "baseUri": "/ccp_api_dtias_2.0_a08.json/definitions/apiprotoMachineInfo",
        "branchId": 98415,
        "branchNodeId": 4756418,
        "createdAt": "2024-03-14T07:52:41.482Z",
        "data": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "softwareIds": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/apiprotoSoftwareId"}
                },
                "lockingIds": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/apiprotoLockingId"}
                }
            },
            "$schema": "[http://json-schema.org/draft-07/schema#](http://json-schema.org/draft-07/schema#)"
        },
        "dataHash": "7345b8ae0b025b99c87cfdd4ce81569044a4587e",
        "dataSize": "273",
        "format": "json",
        "isFile": False,
        "isLatestVersion": True,
        "name": "apiprotoMachineInfo",
        "nodeId": 4786986,
        "projectId": 5318,
        "refName": "#/definitions/apiprotoMachineInfo",
        "snapshotId": 4454003,
        "spec": "oas2",
        "summary": "Represents machine information.", 
        "type": "model",
        "updatedAt": "2024-03-14T07:52:41.482Z",
        "uri": "/ccp_api_dtias_2.0_a08.json/definitions/apiprotoMachineInfo",
        "version": "0.0",
        "models": [],
        "mockUrl": "fulcrum-rest-api-guide/branches/dtias_release_branch_2.0/4990838undefined",
        "bundledModels": {
            "apiprotoLockingId": {
                "type": "object",
                "properties": {
                    "lockingIdCode": {"type": "string"},
                    "lockingIdValue": {"type": "string"}
                },
                 "summary": "Defines a locking ID.",
                "$schema": "[http://json-schema.org/draft-07/schema#](http://json-schema.org/draft-07/schema#)",
                "children": 2,
                "childrenCount": "{2}"
            },
            "apiprotoSoftwareId": {
                "type": "object",
                "properties": {
                    "softwareId": {"type": "string"},
                    "plc": {"type": "string"}
                },
                "summary": "Defines a software ID.",
                "$schema": "[http://json-schema.org/draft-07/schema#](http://json-schema.org/draft-07/schema#)",
                "children": 2,
                "childrenCount": "{2}"
            }
        }
    },
    # Article Type Example API Data Thingie
    {
        "tagNames": [],
        "references": [],
        "deepReferences": [],
        "modelRefList": [],
        "_id": "65e560288581f00012e25f35",
        "baseUri": "/docs/Example-GET-operation-on-server.md",
        "branchId": 98415,
        "branchNodeId": 4579402,
        "createdAt": "2024-03-27T10:57:57.609Z",
        "data": "# Example GET operation on a server using a token\n\n#### Prerequisites\nCreate a token. For more information, see [Create a token](Create-token.md).\n\nAfter you create a token, you can use the token from the **id token** field of the API response to retrieve server details.\n\n#### Steps\n\n1. Retrieve the token from the **id-token** field in the Create a token API response. For example:\n```\n      \n        id-token: eyJhbGciOiJSUz\n``` \n2. Set the **Token** environmental variable to the token obtained in the previous step. For example:\n```json\nexport Token=eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiw\n```\n\n3. Use the following example command as a reference to make your own API call. **Token** is a variable set to the generated token content. \n```shell\ncurl -X 'GET' \\  'https://DTIAS_ip/v1/tenants/{tenant_id}/search/resources/{Id}' \\  -H 'accept: application/json; charset=utf-8' \\  -H \"Authorization: Bearer $Token\"\n```\n>Note: In the API request, *{Id}* is the resource ID. \"DTIAS_ip\" is the IP address of the Dell Telecom Infrastructure Automation Suite instance, and \"tenant_id\" is **Fulcrum**.",
        "dataHash": "7b482bd74ebe4905938eb2921d1c0ecc85333362",
        "dataSize": "3230",
        "format": "markdown",
        "isFile": True,
        "isLatestVersion": True,
        "name": "Example GET operation on a server using a token",
        "nodeId": 1313171,
        "projectId": 5318,
        "snapshotId": 4524104,
        "spec": "md",
        "summary": "Create a token. For more information, see Create a token.",
        "type": "article",
        "updatedAt": "2024-03-27T10:57:57.609Z",
        "uri": "/docs/Example-GET-operation-on-server.md",
        "version": "0.0",
        "models": [],
        "mockUrl": "fulcrum-rest-api-guide/branches/dtias_release_branch_2.0/7570653undefined"
    }
]

# Formats schematic properties into text for the RAG model to use later
def format_properties(properties_dict):
    propTexts = []

    if not properties_dict:
        return "It has no defined properties."
    
    for propName, propDetails in properties_dict.items():

        propType = propDetails.get('type', 'any')
        description = f"Property '{propName}' is type '{propType}'."

        if propType == 'array':

            items = propDetails.get('items', {})
            itemType = items.get('type')
            itemRef = items.get('$ref')
            
            if itemRef:
                refName = itemRef.split('/')[-1] # Getting the reference name
                description += f" It is an array of '{refName}'."
            elif itemType:
                 description += f" It is an array of type '{itemType}'."
            else:
                 description += " It is an array of unspecified items."

        elif '$ref' in propDetails:
             refName = propDetails['$ref'].split('/')[-1]
             description = f"Property '{propName}' references model '{refName}'."

        # Add description/example if available (might need to adapt field names later)
        if propDetails.get('description'):
             description += f" Description: {propDetails['description']}"
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
        text = f"Includes definition for '{modelName}' (type: {model_type})."
        if summary:
            text += f" Summary: {summary}"
        # Recursively format properties of the bundled model
        properties = modelDetails.get('properties')
        if properties:
             text += format_properties(properties)
        else:
             text += " It has no defined properties."
        modelTexts.append(text)
    return " Bundled model definitions: " + " ".join(modelTexts)


def process_api_doc_entry(entry):

    entryType = entry.get('type', 'unknown')
    name = entry.get('name', 'Unnamed Document')
    summary = entry.get('summary', '')

    contentParts = [f"Title: {name}"]
    if summary:
        contentParts.append(f"Summary: {summary}")

    data = entry.get('data', None)
    textContent = ""

    if entryType == 'article' and isinstance(data, str):
        # For articles/markdown, the data field is the main content
        textContent = data
    elif entryType == 'model' and isinstance(data, dict):
        # For models, parse the schema structure
        schemaType = data.get('type', 'object')
        modelDescription = f"This defines the model '{name}', which is a '{schemaType}'."

        # Format main properties
        properties = data.get('properties')
        modelDescription += format_properties(properties)

        # Format bundled models
        bundled = entry.get('bundledModels')
        modelDescription += format_bundled_models(bundled)

        textContent = modelDescription
    elif isinstance(data, str): # Fallback if type isn't clear but data is string
         print(f"Warning: Entry '{name}' has unrecognized type '{entryType}' but string data. Using data directly.")
         textContent = data
    else:
        print(f"Warning: Could not extract primary content for '{name}' of type '{entryType}'. Data: {data}")
        textContent = "Content could not be processed." # Or skip this entry

    contentParts.append(f"Content: {textContent.strip()}")

    # Combine all parts into a single text block
    fullText = "\n\n".join(contentParts)

    return fullText.strip()

if __name__ == "__main__":
    # jsonDat = jsonExampleData
    with open("ScrapingStuff/storedData/allDocumentation.json", 'r') as f:
        jsonDat = json.load(f)

    # Processing
    processedDocs = {}
    print("Processing Api Docs")
    for i, link in enumerate(jsonDat):
        # if i > 5: # Testing on first 5 entries
        #     break
        processed = process_api_doc_entry(jsonDat[link])
        if processed:
            processedDocs[link] = processed

    # Just printing the outputs
    for doc in processedDocs:
        print(f"--- Processed Entry ---")
        print(f"Source URI: {doc}")
        print(f"Text for Embedding:\n{processedDocs[doc]}")
        print("-" * 25)

    with open("ScrapingStuff/storedData/RagFormattedData.json", 'w') as f:
        json.dump(processedDocs, f, indent=4)