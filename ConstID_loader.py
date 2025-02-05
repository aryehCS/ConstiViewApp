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
        # Single constituent fetch by ID
        api_url = f'{base_url}/constituent/v1/constituents/{constituent_id}'
        response = requests.get(api_url, headers=headers)
        print(f"[DEBUG] GET {api_url}, status={response.status_code}")
        if response.status_code == 200:
            constituent_data = response.json()
            print("[DEBUG] API Response for constituent:", constituent_data)
            constituent_data['import_id'] = constituent_data.get('import_id', 'N/A')
            constituent_data['constituent_id'] = constituent_data.get('lookup_id', 'N/A')

            # Fetch SIS ID alias
            alias_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/aliases'
            alias_resp = requests.get(alias_url, headers=headers)
            print(f"[DEBUG] GET {alias_url}, status={alias_resp.status_code}")
            if alias_resp.status_code == 200:
                alias_data = alias_resp.json()
                print("[DEBUG] Alias data:", alias_data)
                alias_list = alias_data.get('value', [])
                sis_id_alias = next((a['alias'] for a in alias_list if a.get('alias_type') == 'SIS ID'), 'N/A')
            else:
                sis_id_alias = 'N/A'

            constituent_data['sis_id_alias'] = sis_id_alias

            # Build the single result for the template
            data = {'value': [constituent_data]}

            # fetch constituent codes
            codes_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/constituentcodes'
            response_codes = requests.get(codes_url, headers=headers)
            print(f"[DEBUG] GET {codes_url}, status={response_codes.status_code}")
            if response_codes.status_code == 200:
                codes_json = response_codes.json()
                print("[DEBUG] Constituent codes data:", codes_json)
                codes = codes_json.get('value', [])
                data['value'][0]['codes'] = [code['description'] for code in codes]
            else:
                data['value'][0]['codes'] = []

            # fetch custom fields
            custom_fields_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/customfields'
            response_custom_fields = requests.get(custom_fields_url, headers=headers)
            print(f"[DEBUG] GET {custom_fields_url}, status={response_custom_fields.status_code}")
            if response_custom_fields.status_code == 200:
                cf_json = response_custom_fields.json()
                print("[DEBUG] Custom fields data:", cf_json)
                custom_fields = cf_json.get('value', [])
                z_sis_record_id = next(
                    (field['value'] for field in custom_fields if field.get('category') == 'Z-SIS Record ID'),
                    'N/A'
                )
                data['value'][0]['z_sis_record_id'] = z_sis_record_id
            else:
                data['value'][0]['z_sis_record_id'] = 'N/A'

        else:
            print(f"[ERROR] Could not fetch constituent: status_code={response.status_code}")

    elif request.method == 'POST':
        # Searching by userEntry text
        userEntry = request.form.get('userEntry').strip()
        encoded_userEntry = requests.utils.quote(userEntry)
        api_url = f'{base_url}/constituent/v1/constituents/search?search_text={encoded_userEntry}'
        response = requests.get(api_url, headers=headers)
        print(f"[DEBUG] GET {api_url}, status={response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("[DEBUG] API Response for search:", data)

            for constituent in data['value']:
                cid = constituent['id']
                constituent['import_id'] = constituent.get('import_id', 'N/A')
                constituent['constituent_id'] = constituent.get('lookup_id', 'N/A')

                # Fetch SIS ID alias
                alias_url = f'{base_url}/constituent/v1/constituents/{cid}/aliases'
                alias_resp = requests.get(alias_url, headers=headers)
                print(f"[DEBUG] GET {alias_url}, status={alias_resp.status_code}")
                if alias_resp.status_code == 200:
                    alias_json = alias_resp.json()
                    print("[DEBUG] Alias data for search result:", alias_json)
                    alias_list = alias_json.get('value', [])
                    sis_id_alias = next((a['alias'] for a in alias_list if a.get('alias_type') == 'SIS ID'), 'N/A')
                else:
                    sis_id_alias = 'N/A'

                constituent['sis_id_alias'] = sis_id_alias

                # fetch codes
                codes_url = f'{base_url}/constituent/v1/constituents/{cid}/constituentcodes'
                response_codes = requests.get(codes_url, headers=headers)
                print(f"[DEBUG] GET {codes_url}, status={response_codes.status_code}")
                if response_codes.status_code == 200:
                    codes_json = response_codes.json()
                    print("[DEBUG] Codes data:", codes_json)
                    codes = codes_json.get('value', [])
                    constituent['codes'] = [code['description'] for code in codes]
                else:
                    constituent['codes'] = []

                # fetch custom fields
                custom_fields_url = f'{base_url}/constituent/v1/constituents/{cid}/customfields'
                response_custom_fields = requests.get(custom_fields_url, headers=headers)
                print(f"[DEBUG] GET {custom_fields_url}, status={response_custom_fields.status_code}")
                if response_custom_fields.status_code == 200:
                    cf_json = response_custom_fields.json()
                    print("[DEBUG] Custom fields data:", cf_json)
                    custom_fields = cf_json.get('value', [])
                    z_sis_record_id = next(
                        (field['value'] for field in custom_fields if field.get('category') == 'Z-SIS Record ID'),
                        'N/A'
                    )
                    constituent['z_sis_record_id'] = z_sis_record_id
                else:
                    constituent['z_sis_record_id'] = 'N/A'
        else:
            print(f"[ERROR] Could not perform search: status_code={response.status_code}")

    # After all that, prepare the data for template
    if data and 'value' in data:
        data['count'] = len(data['value'])
    return render_template('main_page.html', data=data)

@app.route('/relationships/<constituent_id>')
def relationships(constituent_id):
    token = config['tokens']['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Bb-Api-Subscription-Key': subscription_key
    }

    info_url = f'{base_url}/constituent/v1/constituents/{constituent_id}'
    response_info = requests.get(info_url, headers=headers)
    print(f"[DEBUG] GET {info_url}, status={response_info.status_code}")
    if response_info.status_code == 200:
        constituent_name = response_info.json().get('name', 'Unknown')
    else:
        constituent_name = "Unknown"

    rel_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/relationships'
    response_rel = requests.get(rel_url, headers=headers)
    print(f"[DEBUG] GET {rel_url}, status={response_rel.status_code}")
    if response_rel.status_code == 200:
        rel_json = response_rel.json()
        print("[DEBUG] Relationships data:", rel_json)
        relationships = rel_json.get('value', [])
    else:
        relationships = []

    return render_template('relationships_page.html',
                           relationships=relationships,
                           constituent_name=constituent_name)

@app.route('/education/<constituent_id>')
def education(constituent_id):
    token = config['tokens']['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Bb-Api-Subscription-Key': subscription_key
    }

    info_url = f'{base_url}/constituent/v1/constituents/{constituent_id}'
    response_info = requests.get(info_url, headers=headers)
    print(f"[DEBUG] GET {info_url}, status={response_info.status_code}")
    if response_info.status_code == 200:
        constituent_name = response_info.json().get('name', 'Unknown')
    else:
        constituent_name = "Unknown"

    edu_url = f'{base_url}/constituent/v1/constituents/{constituent_id}/educations'
    response_education = requests.get(edu_url, headers=headers)
    print(f"[DEBUG] GET {edu_url}, status={response_education.status_code}")
    if response_education.status_code == 200:
        edu_json = response_education.json()
        print("[DEBUG] Education data:", edu_json)
        education_data = edu_json.get('value', [])
        # Apply your grade_level_mapping
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
                z_sis_id = row[0].strip()
                encoded_term = requests.utils.quote(z_sis_id)
                search_url = f'{base_url}/constituent/v1/constituents/search?search_text={encoded_term}'
                response = requests.get(search_url, headers=headers)
                print(f"[DEBUG] GET {search_url}, status={response.status_code}")

                if response.status_code == 200:
                    search_data = response.json()
                    print("[DEBUG] API Response for search term:", z_sis_id, search_data)
                    found_constituents = search_data.get('value', [])

                    if not found_constituents:
                        # No match
                        results.append({
                            'Original Z-SIS ID': z_sis_id,
                            'Returned lookup_id': 'N/A',
                            'SIS ID Alias': 'N/A',
                            'Name': 'Not Found',
                            'System Record ID': 'N/A',
                            'Z-SIS Record ID': 'N/A',
                        })
                    else:
                        for constituent in found_constituents:
                            cid = constituent['id']
                            returned_lookup_id = constituent.get('lookup_id', 'N/A')
                            name_val = constituent.get('name', 'N/A')

                            # Fetch custom fields
                            cf_url = f'{base_url}/constituent/v1/constituents/{cid}/customfields'
                            rcf = requests.get(cf_url, headers=headers)
                            print(f"[DEBUG] GET {cf_url}, status={rcf.status_code}")
                            if rcf.status_code == 200:
                                cf_json = rcf.json()
                                print("[DEBUG] Custom fields data:", cf_json)
                                cf_list = cf_json.get('value', [])
                                z_sis_record_id = next(
                                    (field['value'] for field in cf_list
                                     if field.get('category') == 'Z-SIS Record ID'),
                                    'N/A'
                                )
                            else:
                                z_sis_record_id = 'N/A'

                            # Fetch alias for SIS ID
                            alias_url = f'{base_url}/constituent/v1/constituents/{cid}/aliases'
                            alias_resp = requests.get(alias_url, headers=headers)
                            print(f"[DEBUG] GET {alias_url}, status={alias_resp.status_code}")
                            if alias_resp.status_code == 200:
                                alias_json = alias_resp.json()
                                print("[DEBUG] Alias data:", alias_json)
                                alias_list = alias_json.get('value', [])
                                sis_id_alias = next(
                                    (a['alias'] for a in alias_list if a.get('alias_type') == 'SIS ID'),
                                    'N/A'
                                )
                            else:
                                sis_id_alias = 'N/A'

                            results.append({
                                'Original Z-SIS ID': z_sis_id,
                                'Returned lookup_id': returned_lookup_id,
                                'SIS ID Alias': sis_id_alias,
                                'Name': name_val,
                                'System Record ID': cid,
                                'Z-SIS Record ID': z_sis_record_id
                            })
                else:
                    print(f"[ERROR] Search request failed: status_code={response.status_code}")
                    results.append({
                        'Original Z-SIS ID': z_sis_id,
                        'Returned lookup_id': 'N/A',
                        'SIS ID Alias': 'N/A',
                        'Name': 'API Error',
                        'System Record ID': 'N/A',
                        'Z-SIS Record ID': 'N/A',
                    })

            # Store the results in session
            session['results'] = results

            # Build a "summary" for quick display if desired
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

            final_data = {'value': list(unique_constituents.values()), 'count': len(unique_constituents)}
            data = final_data

    return render_template('CSV_page.html', data=data)

@app.route('/download_results')
def download_results():
    if 'results' not in session:
        return "No results to download", 400

    results = session['results']

    output_str = StringIO()
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
