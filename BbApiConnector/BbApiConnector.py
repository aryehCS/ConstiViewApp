import requests
import json
import configparser

class BbApiConnector(object):
    """
    This class is used to establish and maintain a connection to the Blackbaud SKY API using a previously generated
    .ini file.
    """
    def __init__(self, config_file_name):
        self.config_file_name = config_file_name
        self._config = configparser.ConfigParser()
        self._config.read(self.config_file_name)

    def get_session(self):
        session = requests.Session()
        session.headers = {
            'Bb-Api-Subscription-Key': self._config['other']['api_subscription_key'],
            'Host': 'api.sky.blackbaud.com',
            'Authorization': f"Bearer {self._config['tokens']['access_token']}"
        }
        while True:
            get_result = session.get(self._config['other']['test_api_endpoint'])
            if get_result.status_code == 401:
                print("401: Unauthorized. Retrieving updated access token...")
                new_token = self.update_access_token()  # Update access token dynamically
                if new_token:
                    session.headers.update({'Authorization': f"Bearer {new_token}"})  # Update session with new token

            elif get_result.status_code == 200:
                print("200: The access token is live!")
                return session

            else:
                print(f"Unknown error with the API. Status code is {get_result.status_code}.")
                print(get_result.text)
                return None

        return session

    def update_access_token(self):
        token_uri = 'https://oauth2.sky.blackbaud.com/token'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': self._config['tokens']['refresh_token'],
            'preserve_refresh_token': True,
            'client_id': self._config['app_secrets']['app_id'],
            'client_secret': self._config['app_secrets']['app_secret']
        }

        response = requests.post(token_uri, data=params, headers=headers)
        new_token = response.json().get('access_token')
        if new_token:
            # Print the new access token to the terminal
            print(f"New Access Token: {new_token}")
            print(f"Full Response: {response.json()}")

            # Update the config with the new token
            self._config['tokens']['access_token'] = new_token

            # Save the updated token to the .ini file
            with open(self.config_file_name, 'w') as config_file:
                self._config.write(config_file)

            print("Access token updated successfully in the .ini file.")
            return new_token  # Return the new token to update session headers
        else:
            print("Failed to retrieve a new access token.")
            return None
