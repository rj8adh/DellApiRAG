Need Assistance

Sign In

- Discover APIs
  - [Explore APIs](https://developer.dell.com/apis)
- [Community](https://www.dell.com/community/Developers/ct-p/Developers)

Go back to APIs

Version

2.2.0  2.1.0  2.0.0

Introduction

How to make an API call

Create a token

Example GET operation on a server

Tasks (Use cases)

IDENTITY AND ACCESS MANAGEMENT APIS
Overview

SCIM service

Token vending and validation

Schemas

DTIAS APIS
Overview

Inventory

Backup

Service Tag

Orchestrator

Logs

File Server

Core

License Management

Resources

Schemas

FACADE API
Overview

Secrets

ESE

Certificate

Configurations

Media

ConfigMap

Firmware Media

Hardware Profiles

OS Drivers

Profile Telemetries

SCP Media

Server Telemetries

Servers

Version

Schemas

### Telecom Infrastructure Automation Suite REST APIs

Dell Telecom Infrastructure Automation Suite provides infrastructure management and orchestration capabilities that are required by disaggregated telecom networks.

Version

2.0.0

Category Name

Software

- API Documentation

# Create a token

When you make a request for a token, three tokens are generated. These tokens include an access token, an id token, and a refresh token. The access token is used for user operations such as creating a user. The id token is used to make API calls for Dell Telecom Infrastructure Automation Suite operations such as retrieving server details. The refresh token is required to refresh the access token and the id token.

The id token that is created to perform Dell Telecom Infrastructure Automation Suite operations expires after five minutes. You have to generate a new id token to continue with the operations.

### API sample request

The following is a sample request for creating a token where "DTIAS\_ip" is the IP address of the Dell Telecom Infrastructure Automation Suite instance, "tenant\_id" is **Fulcrum**, "username" is the default admin, **admin**, and "password" is the keycloak user password value which is set in the **dtias\_config.yaml** file during Dell Telecom Infrastructure Automation Suite installation.

```json
curl --request POST \
  --url https://DTIAS_ip/identity/v1/tenant/{tenant_id}/token/create \
  --header 'Content-Type: application/json' \
  --data '{
  "grant_type": "password",
  "client_id": "ccpapi",
  "username": "admin",
  "password": "keycloak_user_password"
}'
```

### API sample response

The following is a sample response.

```json
{
"access_token":
"eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJqZmZVVHhnS3gxV2h2SndlVFZxekpJT2NUMXNNLVVXT2RWeHlHdWtHal9
VIn0.eyJleHAiOjE2NzI5ODQ2NzgsImlhdCI6MTY3Mjk4NDM3OCwianRpIjoiMzNiNDQ3NTYtMjE2ZC00Y2ViLTk4MmMtNjkyMzFm
NWU0ZmE4IiwiaXNzIjoiaHR0cHM6Ly9ibW8ta2V5Y2xvYWsva2V5Y2xvYWsvcmVhbG1zL2JtbyIsImF1ZCI6WyJyZWFsbS1tYW5hZ2
VtZW50IiwiYWNjb3VudCJdLCJzdWIiOiJkZWZmNDE4NS01ZDhlLTQzN2EtYWY1OC1kNjdkNjNlZDNlM2MiLCJ0eXAiOiJCZWFyZXIiLC
JhenAiOiJibW8tY2xpZW50Iiwic2Vzc2lvbl9zdGF0ZSI6IjAxNDdjZWVlLTgyYTctNDg2Zi04OTVlLTYxNWVlNTk3ODFjYyIsImFjciI6IjEiLCJ
hbGxvd2VkLW9yaWdpbnMiOlsiKiJdLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiZGVmYXVsdC1yb2xlcy1ibW8iLCJvZmZsaW5lX2Fj
Y2VzcyIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsicmVhbG0tbWFuYWdlbWVudCI6eyJyb2xlcyI6WyJtY
W5hZ2UtdXNlcnMiXX0sImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZp
ZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIGVtYWlsIHByb2ZpbGUiLCJzaWQiOiIwMTQ3Y2VlZS04MmE3LTQ4NmYtODk1ZS02M
TVlZTU5NzgxY2MiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5hbWUiOiJhZG1pbiIsImdyb3VwcyI6WyJnbG9iYWwtYWRtaW4iLCJzd
XBwb3J0LWFkbWluIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImFkbWluIiwiZ2l2ZW5fbmFtZSI6ImFkbWluIn0.J77BOuUb8pd6ar0CAm1
aiRX_yOkkp5Pd4NFIDLFCh0MXTZW1nbU2lGzJ9jwIVa-
H0w7MHrZL3WVmV6vwJigHxeiQGddRUpBV8L_HR8E8lxMtXGmiOXy3jlTrK8y8dxz0NM25akAOf68beASfVn5VnZN7fUPiqxxI5co9
2I7nO39N2uabBbbp3YLUIjVYNyawkpxamyTHGZT88eZrhSBvGXkuT3ptGufwtv4A-n4RsYnHKh2AFP5NggpXfsPj9W4iDjffgYVRVT0RQuwx_
RvffPeP_p1xbTkD5N5uW8K2jTOf2ihHa-GV4_SNrLbXFRQHcYUVo9cnDcU0CwlJnquw",
"expires_in": 300,
"refresh_expires_in": 1800,
"refresh_token":
"eyJhbGciOiJIUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJlMTczZDliMS04YTZiLTRhNTEtYjQ0NS00MmIwMDc3MWQ1NWYifQ.eyJleHAiOjE
2NzI5ODYxNzgsImlhdCI6MTY3Mjk4NDM3OCwianRpIjoiMmRiNDAyOWItYTgzNi00Y2VlLTllMzYtNTNkM2M5ZjUyOWFlIiwiaXNzIjoiaHR
0cHM6Ly9ibW8ta2V5Y2xvYWsva2V5Y2xvYWsvcmVhbG1zL2JtbyIsImF1ZCI6Imh0dHBzOi8vYm1vLWtleWNsb2FrL2tleWNsb2FrL3JlYWx
tcy9ibW8iLCJzdWIiOiJkZWZmNDE4NS01ZDhlLTQzN2EtYWY1OC1kNjdkNjNlZDNlM2MiLCJ0eXAiOiJSZWZyZXNoIiwiYXpwIjoiYm1vLWNs
aWVudCIsInNlc3Npb25fc3RhdGUiOiIwMTQ3Y2VlZS04MmE3LTQ4NmYtODk1ZS02MTVlZTU5NzgxY2MiLCJzY29wZSI6Im9wZW5pZCBlb
WFpbCBwcm9maWxlIiwic2lkIjoiMDE0N2NlZWUtODJhNy00ODZmLTg5NWUtNjE1ZWU1OTc4MWNjIn0.DJC-UdzVbrTzgd_ARcdqAY2-
l5hfxjXBTqz26tRbe3k",
"token_type": "Bearer",
"session_state": "0147ceee-82a7-486f-895e-615ee59781cc",
"id_token":
"eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJqZmZVVHhnS3gxV2h2SndlVFZxekpJT2NUMXNNLVVXT2RWeHlHdWtHal9VIn0.e
yJleHAiOjE2NzI5ODQ2NzgsImlhdCI6MTY3Mjk4NDM3OCwiYXV0aF90aW1lIjowLCJqdGkiOiI3MjM5NjAwNC0wODZlLTRiMzAtYTQ3Mi1j
NGFkMTAyMDgxZWUiLCJpc3MiOiJodHRwczovL2Jtby1rZXljbG9hay9rZXljbG9hay9yZWFsbXMvYm1vIiwiYXVkIjoiYm1vLWNsaWVudCIsI
nN1YiI6ImRlZmY0MTg1LTVkOGUtNDM3YS1hZjU4LWQ2N2Q2M2VkM2UzYyIsInR5cCI6IklEIiwiYXpwIjoiYm1vLWNsaWVudCIsInNlc3Np
b25fc3RhdGUiOiIwMTQ3Y2VlZS04MmE3LTQ4NmYtODk1ZS02MTVlZTU5NzgxY2MiLCJhdF9oYXNoIjoiUGY2UXV1YXA5a1pPdEZlRnJiNU
tqUSIsImFjciI6IjEiLCJzaWQiOiIwMTQ3Y2VlZS04MmE3LTQ4NmYtODk1ZS02MTVlZTU5NzgxY2MiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2Us
Im5hbWUiOiJhZG1pbiIsImdyb3VwcyI6WyJnbG9iYWwtYWRtaW4iLCJzdXBwb3J0LWFkbWluIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImFkb
WluIiwiZ2l2ZW5fbmFtZSI6ImFkbWluIn0.PIrx7H7kAuKtbe-sreDUKcWMrelOsf71odfCBEK36u4hRAP63ZyESdxO9iNIkcw-
V4SzHoLyeEGOVMTOmlLy46jF_6gcYK1rV-sDtTzPsT1w7ALM8YG2C-caAgrLIFYVSV3_2-
BwzI8cAcaSj10yemh7SqSSXVHHJGSvzXEKDUNVwJb-
L7GJx1wEQ36MP6zKqQAmNbTZ64CYdL9_ysUl3o1DB_phb83cLGcUqn4lZhkWqeKJHoN9-
h9CK4x6lF3CAdyOM85kRSSqKIfywYpbis2u_U0awuNuyf4E8aR_E91NmwY69b0Dd3G_bbPrxLW_bp8qxcsdE4TdmwWHGEAIhw",
"scope": "openid email profile"
}
```

If you want to update the access token and the id token using the refresh token, use the following sample API request:

```json
curl --request POST \
  --url https://DTIAS_ip/identity/v1/tenant/{tenant_id}/token/create \
  --header 'Content-Type: application/json' \
  --data '{
  "client_id": "ccpapi",
  "grant_type": "refresh_token",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJjN2U3YWZlNi1lMzE0LTQzZTctODk3OS0xYTU2ZDVjNWUzMTAifQ.eyJleHAiOjE2OTMzODk1MjUsImlhdCI6MTY5MzM4NzcyNSwianRpIjoiMGU5ZDQwZjYtMDQ2Ny00NDc3LTlkYjMtYWM0MTdhNWEyNWE4IiwiaXNzIjoiaHR0cHM6Ly9mbGNtLW9jL2tleWNsb2FrL3JlYWxtcy9GdWxjcnVtIiwiYXVkIjoiaHR0cHM6Ly9mbGNtLW9jL2tleWNsb2FrL3JlYWxtcy9GdWxjcnVtIiwic3ViIjoiN2VjZTZhNWEtMDYyNi00NmQ4LWExMmYtNDM2OTQxMTIzZDMxIiwidHlwIjoiUmVmcmVzaCIsImF6cCI6ImNjcGFwaSIsInNlc3Npb25fc3RhdGUiOiJkOWU4ZDQzYy0wYjMyLTQyM2ItODU1NS05OTYzOTM2ZjQ2OGUiLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwic2lkIjoiZDllOGQ0M2MtMGIzMi00MjNiLTg1NTUtOTk2MzkzNmY0NjhlIn0.9lREuiPnhFMHhklL6ue8D1Bq1sVesabZtNo83quKtSI"
}'

```

Back