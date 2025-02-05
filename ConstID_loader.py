from flask import Flask, request, render_template, redirect, url_for, session, send_file
import requests
import configparser
import csv
import os
from io import StringIO, BytesIO

# init configparser
config = configparser.ConfigParser()
config.read('resources/app_secrets.ini')

app = Flask(__name__)
app.secret_key = '3jduf892ks9c7d9f5dpal091hcna7djw'  # Needed for session usage

# set up credentials
client_id = config['app_secrets']['app_id']
client_secret = config['app_secrets']['app_secret']
subscription_key = config['app_secrets']['subscription_key']
auth_url = 'https://oauth2.sky.blackbaud.com/token'
base_url = 'https://api.sky.blackbaud.com'

def get_access_token():
    response = requests.post(auth_url, data={
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    })
    return response.json().get('access_token')

# Grade level mapping - will need to be updated on a yearly basis
grade_level_mapping = {
    'Brawerman - East/Glazer': {
        2025: 'Grade 6',
        2026: 'Grade 5',
        2027: 'Grade 4',
        2028: 'Grade 3',
        2029: 'Grade 2',
        2030: 'Grade 1',
        2031: 'Kindergarten'
    },
    'Brawerman - West/Irmas': {
        2025: 'Grade 6',
        2026: 'Grade 5',
        2027: 'Grade 4',
        2028: 'Grade 3',
        2029: 'Grade 2',
        2030: 'Grade 1',
        2031: 'Kindergarten'
    },
    'ECC - West/Irmas': {
        2032: 'TK Glazer',
        2033: 'Kachol/Katom',
        2034: 'Lavan/Yarok',
        2035: 'Nitzanim'
    },
    'ECC - Resnick': {
        2032: 'TK Mann',
        2033: 'Shemesh',
        2034: 'Keshet',
        2035: 'Geffen'
    },
    'Religious School': {
        2025: 'Grade 12',
        2026: 'Grade 11',
        2027: 'Grade 10',
        2028: 'Grade 9',
        2029: 'Grade 8',
        2030: 'Grade 7',
        2031: 'Grade 6',
        2032: 'Grade 5',
        2033: 'Grade 4',
        2034: 'Grade 3',
        2035: 'Grade 2',
        2036: 'Grade 1',
        2037: 'Kindergarten'
    }
}

# main search page
@app.route('/', methods=['GET', 'POST'])
def index():
    data = None
    token = config['tokens']['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Bb-Api-Subscription-Key': subscription_key
    }

    constituent_id = request.args.get('constituent_id')
    if constituent_id:
        api_url = f'{base_url}/constituent/v1/constituents/{constituent_id}'
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            constituent_data = response.json()
            print("API Response for constituent:", constituent_data)  # Debug statement
            constituent_data['import_id'] = constituent_data.get('import_id', 'N/A')
            constituent_data['constituent_id'] = constituent_data.get('lookup_id', 'N/A')

            # ---- ADDED CODE FOR ALIASES HERE ----
            # Pull the SIS ID alias for this constituent:
            alias_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/aliases'
            alias_resp = requests.get(alias_url, headers=headers)
            if alias_resp.status_code == 200:
                alias_list = alias_resp.json().get('value', [])
                # find an alias where 'alias_type' == 'SIS ID'
                sis_id_alias = next((a['alias'] for a in alias_list if a.get('alias_type') == 'SIS ID'), 'N/A')
            else:
                sis_id_alias = 'N/A'
            # put it in your data structure
            constituent_data['sis_id_alias'] = sis_id_alias
            # ------------------------------------

            data = {'value': [constituent_data]}

            # fetch constituent codes
            codes_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/constituentcodes'
            response_codes = requests.get(codes_url, headers=headers)
            if response_codes.status_code == 200:
                codes = response_codes.json().get('value', [])
                data['value'][0]['codes'] = [code['description'] for code in codes]
            else:
                data['value'][0]['codes'] = []

            # fetch custom fields -> looking for z-sis record id
            custom_fields_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/customfields'
            response_custom_fields = requests.get(custom_fields_url, headers=headers)
            if response_custom_fields.status_code == 200:
                custom_fields = response_custom_fields.json().get('value', [])
                z_sis_record_id = next((field['value'] for field in custom_fields if field.get('category') == 'Z-SIS Record ID'), 'N/A')
                data['value'][0]['z_sis_record_id'] = z_sis_record_id
            else:
                data['value'][0]['z_sis_record_id'] = 'N/A'

        else:
            print(f"Error fetching constituent by ID: {response.status_code}")

    elif request.method == 'POST':
        userEntry = request.form.get('userEntry').strip()
        encoded_userEntry = requests.utils.quote(userEntry)
        api_url = f'{base_url}/constituent/v1/constituents/search?search_text={encoded_userEntry}'
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("API Response for search:", data)  # Debug statement

            for constituent in data['value']:
                cid = constituent['id']
                constituent['import_id'] = constituent.get('import_id', 'N/A')
                constituent['constituent_id'] = constituent.get('lookup_id', 'N/A')

                # ---- ADDED CODE FOR ALIASES HERE ----
                alias_url = f'{base_url}/constituent/v1/constituents/{cid}/aliases'
                alias_resp = requests.get(alias_url, headers=headers)
                if alias_resp.status_code == 200:
                    alias_list = alias_resp.json().get('value', [])
                    sis_id_alias = next((a['alias'] for a in alias_list if a.get('alias_type') == 'SIS ID'), 'N/A')
                else:
                    sis_id_alias = 'N/A'
                constituent['sis_id_alias'] = sis_id_alias
                # -------------------------------------

                # fetch codes
                codes_url = f'{base_url}/constituent/v1/constituents/{cid}/constituentcodes'
                response_codes = requests.get(codes_url, headers=headers)
                if response_codes.status_code == 200:
                    codes = response_codes.json().get('value', [])
                    constituent['codes'] = [code['description'] for code in codes]
                else:
                    constituent['codes'] = []

                # fetch custom fields -> z-sis record id
                custom_fields_url = f'{base_url}/constituent/v1/constituents/{cid}/customfields'
                response_custom_fields = requests.get(custom_fields_url, headers=headers)
                if response_custom_fields.status_code == 200:
                    custom_fields = response_custom_fields.json().get('value', [])
                    z_sis_record_id = next(
                        (field['value'] for field in custom_fields
                         if field.get('category') == 'Z-SIS Record ID'),
                        'N/A'
                    )
                    constituent['z_sis_record_id'] = z_sis_record_id
                else:
                    constituent['z_sis_record_id'] = 'N/A'
        else:
            print(f"Error with search request: {response.status_code}")

    if data and 'value' in data:
        data['count'] = len(data['value'])
    return render_template('main_page.html', data=data)


@app.route('/relationships/<constituent_id>')
def relationships(constituent_id):
    # this route shows relationships for a given constituent
    token = config['tokens']['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Bb-Api-Subscription-Key': subscription_key
    }

    # fetch info to display constituent name
    info_url = f'{base_url}/constituent/v1/constituents/{constituent_id}'
    response_info = requests.get(info_url, headers=headers)
    if response_info.status_code == 200:
        constituent_name = response_info.json().get('name', 'Unknown')
    else:
        constituent_name = "Unknown"

    # fetch relationships for the constituent
    rel_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/relationships'
    response_rel = requests.get(rel_url, headers=headers)
    if response_rel.status_code == 200:
        relationships = response_rel.json().get('value', [])
    else:
        relationships = []

    return render_template('relationships_page.html',
                           relationships=relationships,
                           constituent_name=constituent_name)


@app.route('/education/<constituent_id>')
def education(constituent_id):
    # shows all education records for a given constituent
    token = config['tokens']['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Bb-Api-Subscription-Key': subscription_key
    }

    # fetch const name for display at top of page
    info_url = f'{base_url}/constituent/v1/constituents/{constituent_id}'
    response_info = requests.get(info_url, headers=headers)
    if response_info.status_code == 200:
        constituent_name = response_info.json().get('name', 'Unknown')
    else:
        constituent_name = "Unknown"

    # fetch education data for the constituent
    edu_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/educations'
    response_education = requests.get(edu_url, headers=headers)
    if response_education.status_code == 200:
        education_data = response_education.json().get('value', [])
        # loop through each education record and assign a grade level if possible
        for record in education_data:
            school_name = record.get('school', 'N/A')
            class_of = record.get('class_of', 'N/A')
            if class_of != 'N/A' and school_name in grade_level_mapping:
                try:
                    class_of_int = int(class_of)
                    grade_level = grade_level_mapping[school_name].get(class_of_int, 'N/A')
                except:
                    grade_level = 'N/A'
            else:
                grade_level = 'N/A'
            record['grade_level'] = grade_level
    else:
        education_data = []

    return render_template('education_page.html',
                           education_data=education_data,
                           constituent_name=constituent_name)

@app.route('/upload_csv', methods=['GET', 'POST'])
def upload_csv():
    data = None
    token = config['tokens']['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Bb-Api-Subscription-Key': subscription_key
    }

    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            file_data = file.read().decode('utf-8')
            csv_reader = csv.reader(StringIO(file_data))

            results = []

            for row in csv_reader:
                if not row:
                    continue
                # The first column is your "Z-SIS ID" from the CSV
                z_sis_id = row[0].strip()

                # Search by Z-SIS ID
                encoded_term = requests.utils.quote(z_sis_id)
                search_url = f'{base_url}/constituent/v1/constituents/search?search_text={encoded_term}'
                response = requests.get(search_url, headers=headers)

                if response.status_code == 200:
                    search_data = response.json()
                    found_constituents = search_data.get('value', [])

                    if not found_constituents:
                        # No constituent returned
                        results.append({
                            'Original Z-SIS ID': z_sis_id,
                            'Returned lookup_id': 'N/A',
                            'SIS ID Alias': 'N/A',  # new column for the SIS alias
                            'Name': 'Not Found',
                            'System Record ID': 'N/A',
                            'Z-SIS Record ID': 'N/A',
                        })
                    else:
                        # For each found constituent
                        for constituent in found_constituents:
                            cid = constituent['id']
                            returned_lookup_id = constituent.get('lookup_id', 'N/A')

                            # (Optional) Fetch custom fields
                            cf_url = f'{base_url}/constituent/v1/constituents/{cid}/customfields'
                            rcf = requests.get(cf_url, headers=headers)
                            if rcf.status_code == 200:
                                cf = rcf.json().get('value', [])
                                z_sis_record_id = next(
                                    (field['value'] for field in cf if field.get('category') == 'Z-SIS Record ID'),
                                    'N/A'
                                )
                            else:
                                z_sis_record_id = 'N/A'

                            # ---- ADDED CODE FOR ALIASES HERE ----
                            alias_url = f'{base_url}/constituent/v1/constituents/{cid}/aliases'
                            alias_resp = requests.get(alias_url, headers=headers)
                            if alias_resp.status_code == 200:
                                alias_list = alias_resp.json().get('value', [])
                                sis_id_alias = next((a['alias'] for a in alias_list if a.get('alias_type') == 'SIS ID'), 'N/A')
                            else:
                                sis_id_alias = 'N/A'
                            # -------------------------------------

                            results.append({
                                'Original Z-SIS ID': z_sis_id,
                                'Returned lookup_id': returned_lookup_id,
                                'SIS ID Alias': sis_id_alias,   # store the SIS alias from aliases endpoint
                                'Name': constituent['name'],
                                'System Record ID': cid,
                                'Z-SIS Record ID': z_sis_record_id
                            })
                else:
                    # Error calling the search endpoint
                    results.append({
                        'Original Z-SIS ID': z_sis_id,
                        'Returned lookup_id': 'N/A',
                        'SIS ID Alias': 'N/A',
                        'Name': 'API Error',
                        'System Record ID': 'N/A',
                        'Z-SIS Record ID': 'N/A',
                    })

            # Save full results to session, so we can download them later
            session['results'] = results

            # Build a "summary" for display if needed
            unique_constituents = {}
            for entry in results:
                cid = entry['System Record ID']
                if cid not in unique_constituents:
                    unique_constituents[cid] = {
                        'id': cid,
                        'lookup_id': entry['Returned lookup_id'],
                        'sis_alias': entry['SIS ID Alias'],
                        'z_sis_record_id': entry['Z-SIS Record ID'],
                        'name': entry['Name'],
                        'original_z_sis_id': entry['Original Z-SIS ID']
                    }
            final_data = {'value': list(unique_constituents.values()),
                          'count': len(unique_constituents)}
            data = final_data

    return render_template('CSV_page.html', data=data)

@app.route('/download_results')
def download_results():
    """Download the CSV of the results that were stored in session."""
    if 'results' not in session:
        return "No results to download", 400

    results = session['results']

    output_str = StringIO()
    # Add columns in the final CSV, including the new SIS ID Alias:
    fieldnames = [
        'Original Z-SIS ID',
        'Returned lookup_id',
        'SIS ID Alias',
        'Name',
        'System Record ID',
        'Z-SIS Record ID'
    ]
    writer = csv.DictWriter(output_str, fieldnames=fieldnames)
    writer.writeheader()
    for line in results:
        writer.writerow(line)

    csv_data = output_str.getvalue().encode('utf-8')
    output = BytesIO(csv_data)

    return send_file(output, mimetype='text/csv', download_name='output.csv', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
