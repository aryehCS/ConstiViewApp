# ConstiView Application

This application will pull constituent data (system record ID, Z-SIS record ID, Name, constituent code(s), family
relation data, and educational data). 

### Family Data
- Relationship type
- Related constituents
- Constituent ID

### Educational Data
- Current and former schooling data, including:
    - School name
    - Status
    - Class of
    - Grade level
    - Metadata
        - ID
        - Constituent ID
        - Date entered
        - Date left
        - Primary (y/n)
        - Type
        - Majors

---

## Environment Set-up (macOS):
1. Run "python3 --version" in terminal
2. If version comes up, it is downloaded.
3. If not, download python (make sure the download is correct for your mac - intel or arm)

## Instructions to download and run the application:
1. Clone the repository to your local machine.
Do this by running the following in terminal:
``` git clone https://github.com/aryehCS/ConstiViewApp.git ```
2. Navigate into the project directory:
``` cd ConstiViewApp ```
3. Navigate into the resources folder:
``` cd resources ```
4. Create a new file called "app_secrets.ini" in the resources folder.
``` touch app_secrets.ini ```
5. Open that file in a text editor.
``` open app_secrets.ini ```
6. Paste the text from Appendix A into the file and save the file.
7. Navigate back to the project directory:
``` cd .. ```
8. Download the required packages:
``` pip3 install -r requirements.txt ```
9. Run the following command to run the authorization file:
``` python3 bb_auth.py ```
10. Go to http://localhost:13631/ in your browser and sign in with your Blackbaud account.
11. If you are successful you should see this in the terminal:
```
Access Token: xxx
Refresh Token: xxx
Full Response: {'access_token': 'xxx', 'token_type': 'Bearer', 'expires_in': 3600, etc...}
Tokens updated successfully in the .ini file.
```
12. Run the following command to run the application:
``` python3 CSVoutput_test.py ```
13. Now go to http://127.0.0.1:5000 in your browser.

## Appendix A:
```
[app_secrets]

app_id = 

app_secret =

subscription_key = 

[tokens]

access_token = 

refresh_token = 

[other]

redirect_uri = http://localhost:13631/callback

test_api_endpoint = https://api.sky.blackbaud.com/constituent/v1/constituents/constituentcodes/{constituent_code_id}

[api]

base_url = https://api.sky.blackbaud.com
```
You will need to fill out app_id, app_secret, subscription_key, and api_subscription_key. The tokens will be automatically
filled out when you run the first file, so leave it. For the app secrets, you will either need to get this from your 
blackbaud api portal, or get them from me (Aryeh) directly, as it is a security risk to post them publicly. 


## Security Notice:
Do not share app_secrets.ini publicly. It contains sensitive credentials.