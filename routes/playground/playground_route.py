from flask import Blueprint, render_template, request, jsonify
import requests
import base64
import os

playground_bp = Blueprint('playground', __name__)

@playground_bp.route('/playground/onet-interest-profiler')
def onet_interest_profiler():
    return render_template('playground/onet_interest_profiler.html')

@playground_bp.route('/playground')
def playground():
    return render_template('playground/playground.html')

@playground_bp.route('/playground/search-onet')
def search_onet():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify([])
    
    # O*NET Web Services URL for occupation search
    url = f'https://services.onetcenter.org/ws/online/search?keyword={keyword}'
    
    # Create Basic Auth header and specify JSON format
    credentials = base64.b64encode(b'prepkc:2996tva').decode('utf-8')
    headers = {
        'Authorization': f'Basic {credentials}',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # O*NET returns data in a specific format, let's extract just the occupations
            data = response.json()
            occupations = []
            if 'occupation' in data:
                if isinstance(data['occupation'], list):
                    occupations = data['occupation']
                else:
                    occupations = [data['occupation']]
            return jsonify(occupations)
        else:
            return jsonify({'error': f'Error from O*NET API: {response.status_code}'}), 400
    except Exception as e:
        print(f"Error: {str(e)}")  # Add logging for debugging
        return jsonify({'error': str(e)}), 500