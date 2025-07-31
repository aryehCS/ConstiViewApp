from flask import Flask, request, render_template, render_template_string, redirect, url_for, session, send_file
from flask_session import Session
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

#configure server-side sessions
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

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

    #session['test'] = 'Server-Side Session Data'
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
                response = requests.get(search_url, headers=headers, timeout=30)
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
    print("[DEBUG] Checking Session for results...")
    if 'results' not in session:
        print("[DEBUG] No results to download")
        return "No results to download", 400

    results = session['results']
    print("[DEBUG] Found results with", len(results), "rows")

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

@app.route('/get_all_emails')
def get_all_emails():

    # Fetch all constituent emails and return as CSV - Optimized version

    token = config['tokens']['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Bb-Api-Subscription-Key': subscription_key
    }
    
    print("Starting optimized email extraction process...")
    
    # Step 1: Get all constituents first (bulk operation)
    print("\nStep 1: Fetching all constituents...")
    constituents_url = f'{base_url}/constituent/v1/constituents'
    all_constituents = {}
    offset = 0
    limit = 1000
    
    while True:
        paginated_url = f'{constituents_url}?limit={limit}&offset={offset}'
        print(f"  Fetching constituents with offset {offset}...")
        response = requests.get(paginated_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            constituents = data.get('value', [])
            
            if not constituents:
                break
                
            # Store constituents by ID for quick lookup
            for constituent in constituents:
                constituent_id = constituent.get('id')
                if constituent_id:
                    all_constituents[constituent_id] = constituent.get('name', '')
            
            print(f"  Retrieved {len(constituents)} constituent records (Total: {len(all_constituents)})")
            
            if len(constituents) < limit:
                break
                
            offset += limit
        else:
            print(f"Error fetching constituents: {response.status_code}")
            print(f"Response: {response.text}")
            break
    
    print(f"Retrieved {len(all_constituents)} total constituents")
    
    # Step 2: Get all email addresses
    print("\nStep 2: Fetching all email addresses...")
    email_url = f'{base_url}/constituent/v1/emailaddresses'
    all_emails = []
    offset = 0
    
    while True:
        paginated_url = f'{email_url}?limit={limit}&offset={offset}'
        print(f"  Fetching emails with offset {offset}...")
        response = requests.get(paginated_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            emails = data.get('value', [])
            
            if not emails:
                break
                
            all_emails.extend(emails)
            print(f"  Retrieved {len(emails)} email records (Total: {len(all_emails)})")
            
            if len(emails) < limit:
                break
                
            offset += limit
        else:
            print(f"Error fetching emails: {response.status_code}")
            print(f"Response: {response.text}")
            break
    
    print(f"Retrieved {len(all_emails)} total email records")
    
    # Step 3: Get all constituent codes (bulk operation)
    print(f"\nStep 3: Fetching all constituent codes...")
    codes_url = f'{base_url}/constituent/v1/constituents/constituentcodes'
    all_codes = {}
    offset = 0
    
    while True:
        paginated_url = f'{codes_url}?limit={limit}&offset={offset}'
        print(f"  Fetching constituent codes with offset {offset}...")
        response = requests.get(paginated_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            codes = data.get('value', [])
            
            if not codes:
                break
                
            # Store codes by constituent ID
            for code in codes:
                constituent_id = code.get('constituent_id')
                code_description = code.get('description', '')
                if constituent_id:
                    if constituent_id not in all_codes:
                        all_codes[constituent_id] = []
                    all_codes[constituent_id].append(code_description)
            
            # Debug: show first few codes to understand the structure
            if len(all_codes) <= 5:
                for constituent_id, codes_list in list(all_codes.items())[:3]:
                    print(f"    Debug: Sample codes - Constituent ID: {constituent_id}, Codes: {codes_list}")
            
            print(f"  Retrieved {len(codes)} code records (Total constituents with codes: {len(all_codes)})")
            
            if len(codes) < limit:
                break
                
            offset += limit
        else:
            print(f"Error fetching constituent codes: {response.status_code}")
            print(f"Response: {response.text}")
            break
    
    print(f"Retrieved codes for {len(all_codes)} constituents")
    
    # Debug: Check if we have any data
    print(f"Debug: Total emails to process: {len(all_emails)}")
    print(f"Debug: Total constituents with codes: {len(all_codes)}")
    
    # Analyze what codes we have
    all_unique_codes = set()
    member_count = 0
    for codes_list in all_codes.values():
        for code in codes_list:
            all_unique_codes.add(code.strip())
            if code.strip() == "Member":
                member_count += 1
    
    print(f"Debug: Unique constituent codes found: {sorted(all_unique_codes)}")
    print(f"Debug: Total 'Member' codes found: {member_count}")
    print(f"Debug: Total constituents with 'Member' code: {member_count}")
    
    # Step 4: Match emails to constituents and create CSV
    print(f"\nStep 4: Matching {len(all_emails)} emails to {len(all_constituents)} constituents...")
    email_data = []
    matched_count = 0
    unmatched_count = 0
    filtered_count = 0  # Count of records filtered out
    
    for i, email_record in enumerate(all_emails):
        if i % 1000 == 0:  # Show progress every 1000 records
            print(f"  Processing email {i+1}/{len(all_emails)} ({(i+1)/len(all_emails)*100:.1f}%)")
            
        constituent_id = email_record.get('constituent_id')
        email_address = email_record.get('address', '')
        
        # Debug: show first few email records
        if i < 3:
            print(f"    Debug: Email record {i+1} - ID: {constituent_id}, Email: {email_address}")
        
        # Skip if no email address
        if not email_address:
            continue
            
        # Get constituent name from our cache
        name = all_constituents.get(constituent_id, '')
        
        # Get constituent codes from our cache
        codes = all_codes.get(constituent_id, [])
        codes_string = ', '.join(codes) if codes else ''
        
        if name:
            matched_count += 1
        else:
            unmatched_count += 1
            print(f"    Warning: No constituent found for ID: {constituent_id}")
        
        # Only include records that have "Member" codes (exclude everything else)
        if codes and codes_string.strip():
            # Debug: show what codes we have for first few records
            if i < 5:
                print(f"    Debug: Record {i+1} - Original codes: {codes}")
            
            # Check if this record has "Member" code
            has_member = any(code.strip() == "Member" for code in codes)
            
            if has_member:  # Only include if "Member" code is present
                # Keep all codes including "Member"
                filtered_codes = [code for code in codes if code.strip() and code.strip() != "NonMember"]
                filtered_codes_string = ', '.join(filtered_codes)
                email_data.append({
                    'Email': email_address,
                    'Constituent Codes': filtered_codes_string
                })
                if len(email_data) <= 5:  # Debug: show first 5 records
                    print(f"    Debug: Added record (has Member) - Email: {email_address}, Codes: {filtered_codes_string}")
            else:
                filtered_count += 1  # Count records that don't have "Member" code
                if filtered_count <= 3:  # Debug: show first 3 filtered records
                    print(f"    Debug: Filtered out (no Member) - Email: {email_address}, Codes: {codes_string}")
        else:
            filtered_count += 1  # Count records with no codes
            if filtered_count <= 3:  # Debug: show first 3 records with no codes
                print(f"    Debug: Filtered out (no codes) - Email: {email_address}")
    
    # Create CSV output
    print(f"\nStep 5: Creating CSV file with {len(email_data)} email records...")
    output_str = StringIO()
    fieldnames = ['Email', 'Constituent Codes']
    writer = csv.DictWriter(output_str, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in email_data:
        writer.writerow(row)
    
    csv_data = output_str.getvalue().encode('utf-8')
    output = BytesIO(csv_data)
    
    print(f"Successfully generated CSV with {len(email_data)} email records")
    print(f"Summary:")
    print(f"   - Total constituents fetched: {len(all_constituents)}")
    print(f"   - Total emails fetched: {len(all_emails)}")
    print(f"   - Total constituents with codes: {len(all_codes)}")
    print(f"   - Matched emails: {matched_count}")
    print(f"   - Unmatched emails: {unmatched_count}")
    print(f"   - Filtered out (no codes or no 'Member'): {filtered_count}")
    print(f"   - Final records in CSV: {len(email_data)}")
    
    # Count how many records in final CSV have "Member" codes
    member_records_in_csv = 0
    for record in email_data:
        if "Member" in record.get('Constituent Codes', ''):
            member_records_in_csv += 1
    
    print(f"   - Records with 'Member' codes in final CSV: {member_records_in_csv}")
    
    # Save file directly to computer
    import os
    from datetime import datetime
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"all_constituent_emails_{timestamp}.csv"
    
    # Save to Downloads folder
    downloads_path = os.path.expanduser("~/Downloads")
    filepath = os.path.join(downloads_path, filename)
    
    # Write CSV to file
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in email_data:
            writer.writerow(row)
    
    print(f"File saved to: {filepath}")
    print(f"File size: {os.path.getsize(filepath):,} bytes")
    
    # Also return the file for browser download
    return send_file(output, mimetype='text/csv', download_name=filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
