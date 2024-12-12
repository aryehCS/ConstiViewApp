README

This application will pull constituent data (system record ID, Z-SIS record ID, Name, constituent code(s), family
relation data, and educational data). 

The family data contains relationship type, related Constituent name, and constituent ID.

The educational data contains current and former schooling data. This includes school name, status, class of, grade level,
and metadata (ID, Const. ID, Date entered, Date Left, Primary (y/n), Type, and Majors).

Environment Set-up (macOS):
1. Run "python3 --version" in terminal
2. If version comes up, it is downloaded.
3. If not, download python (make sure the download is correct for your mac - intel or arm)

Instructions to download and run the application:
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
8. 

Appendix A:

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

You will need to fill out app_id, app_secret, subscription_key, and api_subscription_key. The tokens will be automatically
filled out when you run the first file, so leave it. For the app secrets, you will either need to get this from your 
blackbaud api portal, or get them from me (Aryeh) directly, as it is a security risk to post them publicly. 

3. Now you will need to run bb_auth.py. Go to http://localhost:13631/ which should also be posted in the working terminal.
4. Sign in and verify your access with the Blackbaud api.
5. If you are successful you should see this in the terminal:
Access Token: xxx
Refresh Token: xxx
Full Response: {'access_token': 'xxx', 'token_type': 'Bearer', 'expires_in': 3600, etc...}
Tokens updated successfully in the .ini file.
6. Now you can run app.py. After this go to http://127.0.0.1:5000
7. You can now search by name, const ID, Z-SIS ID, or other search terms to bring up a list of constituents.


Security Notice:
Do not share app_secrets.ini publicly. It contains sensitive credentials.