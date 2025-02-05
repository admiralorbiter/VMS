from flask import Blueprint, render_template, request, jsonify
import requests
import base64
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

playground_bp = Blueprint('playground', __name__)

@playground_bp.route('/playground/onet-interest-profiler')
def onet_interest_profiler():
    return render_template('playground/onet_interest_profiler.html')

@playground_bp.route('/playground')
def playground():
    return render_template('playground/playground.html')

def get_onet_headers():
    """Get O*NET API headers with authentication"""
    auth_key = os.getenv('ONET_AUTH_KEY')
    if not auth_key:
        raise ValueError("O*NET authentication key not found in environment variables")
    
    return {
        'Authorization': f'Basic {auth_key}',
        'Accept': 'application/json'
    }

@playground_bp.route('/playground/search-onet')
def search_onet():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify([])
    
    # O*NET Web Services URL for occupation search
    url = f'https://services.onetcenter.org/ws/online/search?keyword={keyword}'
    
    try:
        headers = get_onet_headers()
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

@playground_bp.route('/playground/search-skills')
def search_skills():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify([])
    
    # O*NET Web Services URL for skills search
    url = f'https://services.onetcenter.org/ws/online/skill_search?keyword={keyword}'
    
    try:
        headers = get_onet_headers()
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            skills = []
            if 'skill' in data:
                if isinstance(data['skill'], list):
                    skills = data['skill']
                else:
                    skills = [data['skill']]
            return jsonify(skills)
        else:
            return jsonify({'error': f'Error from O*NET API: {response.status_code}'}), 400
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500