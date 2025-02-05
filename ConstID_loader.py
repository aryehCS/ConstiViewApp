from flask import Flask, request, render_template, render_template_string, redirect, url_for, session, send_file
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
    }) # exchanges client_id and client_secret for an access token from Blackbaud
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
                # fetch codes
                codes_url = f'{base_url}/constituent/v1/constituents/{cid}/constituentcodes'
                response_codes = requests.get(codes_url, headers=headers)
                if response_codes.status_code == 200:
                    codes = response_codes.json().get('value', [])
                    constituent['codes'] = [code['description'] for code in codes]
                else:
                    constituent['codes'] = []

                # fetch custom fields -> z_sis_record_id
                custom_fields_url = f'{base_url}/constituent/v1/constituents/{cid}/customfields'
                response_custom_fields = requests.get(custom_fields_url, headers=headers)
                if response_custom_fields.status_code == 200:
                    custom_fields = response_custom_fields.json().get('value', [])
                    z_sis_record_id = next((field['value'] for field in custom_fields if field.get('category') == 'Z-SIS Record ID'), 'N/A')
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

    return render_template('relationships_page.html', relationships=relationships, constituent_name=constituent_name)

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

    # fetch education data
    edu_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/educations'
    response_education = requests.get(edu_url, headers=headers)
    if response_education.status_code == 200:
        education_data = response_education.json().get('value', [])
        # loop & map classes
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

    return render_template('education_page.html', education_data=education_data, constituent_name=constituent_name)

@app.route('/upload_csv', methods=['GET', 'POST'])
def upload_csv():
    """
    Upload a CSV that contains your Z-SIS IDs in the first column.
    We'll:
    1. Clear old session data (if any).
    2. Read each row's Z-SIS ID (call it 'term').
    3. Search the Blackbaud API to get constituent data for that 'term'.
    4. Collect each result, but use the *CSV's* Z-SIS ID as 'Z-SIS Record ID'.
    """
    data = None
    token = config['tokens']['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Bb-Api-Subscription-Key': subscription_key
    }

    if request.method == 'POST':
        # ---- Clear old results to ensure the download CSV is always fresh:
        session.pop('results', None)
        # ---------------------------------------

        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            file_data = file.read().decode('utf-8')
            csv_reader = csv.reader(StringIO(file_data))
            search_terms = [row[0] for row in csv_reader if row]

            results = []

            for term in search_terms:
                encoded_term = requests.utils.quote(term)
                search_url = f'{base_url}/constituent/v1/constituents/search?search_text={encoded_term}'
                response = requests.get(search_url, headers=headers)
                print("API Response for search term:", term)
                print("Status:", response.status_code)
                if response.status_code == 200:
                    search_data = response.json()
                    print("Search data:", search_data)
                    found_constituents = search_data.get('value', [])

                    if not found_constituents:
                        # No match found for that Z-SIS ID
                        results.append({
                            'System Record ID': 'N/A',
                            'Constituent ID': 'N/A',
                            # <-- Use the CSV's term directly in the final output
                            'Z-SIS Record ID': term,
                            'Name': 'Not Found',
                            'Constituent Code': 'N/A',
                            'School Name': 'N/A',
                            'Status': 'N/A',
                            'Class Of': 'N/A',
                            'Grade Level': 'N/A',
                            'Type': 'N/A',
                            'Majors': 'N/A',
                            'Date Entered': 'N/A',
                            'Date Left': 'N/A',
                            'Primary': 'No'
                        })
                    else:
                        for constituent in found_constituents:
                            cid = constituent['id']
                            # If the API returns a 'lookup_id' or something similar
                            bb_lookup_id = constituent.get('lookup_id', 'N/A')
                            # Or use the name
                            name_val = constituent.get('name', 'N/A')

                            # fetch codes
                            codes_url = f'{base_url}/constituent/v1/constituents/{cid}/constituentcodes'
                            rcodes = requests.get(codes_url, headers=headers)
                            if rcodes.status_code == 200:
                                c_codes = rcodes.json().get('value', [])
                                codes_list = [c['description'] for c in c_codes]
                                combined_codes = ', '.join(codes_list)
                            else:
                                combined_codes = 'N/A'

                            # fetch educations
                            edu_url = f'{base_url}/constituent/v1/constituents/{cid}/educations'
                            redu = requests.get(edu_url, headers=headers)
                            if redu.status_code == 200:
                                edu_data = redu.json().get('value', [])
                                primary_record = next((ed for ed in edu_data if ed.get('primary')), None)
                                if primary_record:
                                    school_name = primary_record.get('school', 'N/A')
                                    class_of = primary_record.get('class_of', 'N/A')
                                    if class_of != 'N/A' and school_name in grade_level_mapping:
                                        try:
                                            grade_level = grade_level_mapping[school_name].get(int(class_of), 'N/A')
                                        except:
                                            grade_level = 'N/A'
                                    else:
                                        grade_level = 'N/A'

                                    date_entered = primary_record.get('date_entered')
                                    de_str = f"{date_entered['d']}/{date_entered['m']}/{date_entered['y']}" if date_entered else 'N/A'

                                    date_left = primary_record.get('date_left')
                                    dl_str = f"{date_left['d']}/{date_left['m']}/{date_left['y']}" if date_left else 'N/A'

                                    majors_list = primary_record.get('majors', [])
                                    majors_str = ", ".join(majors_list) if majors_list else 'N/A'

                                    # Add a row for this constituent
                                    results.append({
                                        'System Record ID': cid,
                                        # We'll treat 'Constituent ID' as the 'lookup_id'
                                        'Constituent ID': bb_lookup_id,
                                        # Use the *CSV's* SIS ID as the Z-SIS Record ID
                                        'Z-SIS Record ID': term,
                                        'Name': name_val,
                                        'Constituent Code': combined_codes,
                                        'School Name': school_name,
                                        'Status': primary_record.get('status', 'N/A'),
                                        'Class Of': class_of,
                                        'Grade Level': grade_level,
                                        'Type': primary_record.get('type', 'N/A'),
                                        'Majors': majors_str,
                                        'Date Entered': de_str,
                                        'Date Left': dl_str,
                                        'Primary': 'Yes'
                                    })
                                else:
                                    # no primary record
                                    results.append({
                                        'System Record ID': cid,
                                        'Constituent ID': bb_lookup_id,
                                        'Z-SIS Record ID': term,
                                        'Name': name_val,
                                        'Constituent Code': combined_codes,
                                        'School Name': 'N/A',
                                        'Status': 'N/A',
                                        'Class Of': 'N/A',
                                        'Grade Level': 'N/A',
                                        'Type': 'N/A',
                                        'Majors': 'N/A',
                                        'Date Entered': 'N/A',
                                        'Date Left': 'N/A',
                                        'Primary': 'No'
                                    })
                            else:
                                # If educations fail, still store the row
                                results.append({
                                    'System Record ID': cid,
                                    'Constituent ID': bb_lookup_id,
                                    'Z-SIS Record ID': term,
                                    'Name': name_val,
                                    'Constituent Code': combined_codes,
                                    'School Name': 'N/A',
                                    'Status': 'N/A',
                                    'Class Of': 'N/A',
                                    'Grade Level': 'N/A',
                                    'Type': 'N/A',
                                    'Majors': 'N/A',
                                    'Date Entered': 'N/A',
                                    'Date Left': 'N/A',
                                    'Primary': 'No'
                                })
                else:
                    print("Error searching for:", term, "status code:", response.status_code)
                    # No valid result
                    results.append({
                        'System Record ID': 'N/A',
                        'Constituent ID': 'N/A',
                        'Z-SIS Record ID': term,
                        'Name': 'API Error',
                        'Constituent Code': 'N/A',
                        'School Name': 'N/A',
                        'Status': 'N/A',
                        'Class Of': 'N/A',
                        'Grade Level': 'N/A',
                        'Type': 'N/A',
                        'Majors': 'N/A',
                        'Date Entered': 'N/A',
                        'Date Left': 'N/A',
                        'Primary': 'No'
                    })

            # ---- Save new results in the session ----
            session['results'] = results

            # Build summary for display if needed
            unique_constituents = {}
            for line in results:
                cid = line['System Record ID']
                if cid not in unique_constituents:
                    unique_constituents[cid] = {
                        'id': cid,
                        'constituent_id': line['Constituent ID'],
                        # store the CSV Z-SIS directly
                        'z_sis_record_id': line['Z-SIS Record ID'],
                        'name': line['Name'],
                        'codes': line['Constituent Code'].split(', ')
                            if line['Constituent Code'] and line['Constituent Code'] != 'N/A' else []
                    }

            final_data = {'value': list(unique_constituents.values()),
                          'count': len(unique_constituents)}
            data = final_data

    return render_template('CSV_page.html', data=data)

@app.route('/download_results')
def download_results():
    if 'results' not in session:
        return "No results to download", 400

    results = session['results']

    output_str = StringIO()
    fieldnames = [
        'System Record ID', 'Constituent ID', 'Z-SIS Record ID', 'Name', 'Constituent Code',
        'School Name', 'Status', 'Class Of', 'Grade Level', 'Type', 'Majors',
        'Date Entered', 'Date Left', 'Primary'
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
