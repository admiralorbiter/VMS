from flask import Blueprint, render_template, request, jsonify
import requests
import base64
import os
import json
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
    search_type = request.args.get('type', 'job')
    
    if not keyword:
        return jsonify([])
    
    try:
        headers = get_onet_headers()
        
        if search_type == 'job':
            # Search for occupations
            url = f'https://services.onetcenter.org/ws/online/search?keyword={keyword}'
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                occupations = []
                if 'occupation' in data:
                    occupations = data['occupation'] if isinstance(data['occupation'], list) else [data['occupation']]
                return jsonify(occupations)
        else:
            # Search by skill
            url = f'https://services.onetcenter.org/ws/online/skills?keyword={keyword}'
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                skills = []
                if 'skill' in data:
                    skills = data['skill'] if isinstance(data['skill'], list) else [data['skill']]
                return jsonify(skills)
                
        return jsonify([])
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playground_bp.route('/playground/job-details/<code>')
def job_details(code):
    """Get comprehensive details for a specific job code"""
    try:
        headers = get_onet_headers()
        details = {}
        
        # Get basic job information
        job_url = f'https://services.onetcenter.org/ws/online/occupations/{code}'
        job_response = requests.get(job_url, headers=headers)
        if job_response.status_code == 200:
            details.update(job_response.json())
            job_title = details.get('title', '')
        
        # Get skills with level data
        skills_url = f'https://services.onetcenter.org/ws/online/occupations/{code}/details/skills'
        skills_response = requests.get(skills_url, headers=headers)
        if skills_response.status_code == 200:
            skills_data = skills_response.json()
            if 'element' in skills_data:
                details['skills'] = [
                    {
                        'name': skill.get('name', ''),
                        'description': skill.get('description', ''),
                        'level': skill.get('score', {}).get('value', 0),
                        'importance': skill.get('score', {}).get('important', False)
                    }
                    for skill in skills_data['element']
                ]
        
        # Get knowledge areas with level data
        knowledge_url = f'https://services.onetcenter.org/ws/online/occupations/{code}/details/knowledge'
        knowledge_response = requests.get(knowledge_url, headers=headers)
        if knowledge_response.status_code == 200:
            knowledge_data = knowledge_response.json()
            if 'element' in knowledge_data:
                details['knowledge'] = [
                    {
                        'name': item.get('name', ''),
                        'description': item.get('description', ''),
                        'level': item.get('score', {}).get('value', 0),
                        'importance': item.get('score', {}).get('important', False)
                    }
                    for item in knowledge_data['element']
                ]
        
        # Get interests
        interests_url = f'https://services.onetcenter.org/ws/online/occupations/{code}/details/interests'
        interests_response = requests.get(interests_url, headers=headers)
        if interests_response.status_code == 200:
            details['interests'] = interests_response.json().get('element', [])
        
        # Get related jobs first through O*NET's related endpoint
        related_url = f'https://services.onetcenter.org/ws/online/occupations/{code}/related/job_families'
        related_response = requests.get(related_url, headers=headers)
        all_related = []
        
        if related_response.status_code == 200:
            related_data = related_response.json()
            if 'job_family' in related_data:
                job_families = related_data['job_family']
                if isinstance(job_families, list):
                    for family in job_families:
                        if 'occupation' in family:
                            occupations = family['occupation']
                            if isinstance(occupations, list):
                                all_related.extend(occupations)
                            else:
                                all_related.append(occupations)
        
        # If no related jobs found through O*NET's related endpoint, fall back to search using the job title
        if not all_related and job_title:
            # Remove the current job's category/type from the search
            search_terms = job_title.split(',')[0]  # Take only the main title part
            search_url = f'https://services.onetcenter.org/ws/online/search?keyword={search_terms}'
            search_response = requests.get(search_url, headers=headers)
            
            if search_response.status_code == 200:
                search_data = search_response.json()
                if 'occupation' in search_data:
                    search_results = search_data['occupation']
                    if isinstance(search_results, list):
                        # Filter out the current job from results
                        all_related = [job for job in search_results if job.get('code') != code]
                    elif isinstance(search_results, dict) and search_results.get('code') != code:
                        all_related = [search_results]
        
        details['related'] = all_related
        
        return jsonify(details)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playground_bp.route('/playground/search-skills')
def search_skills():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify([])
    
    # First get matching occupations
    url = f'https://services.onetcenter.org/ws/online/search?keyword={keyword}'
    
    try:
        headers = get_onet_headers()
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'occupation' in data:
                occupations = data['occupation'] if isinstance(data['occupation'], list) else [data['occupation']]
                if occupations:
                    # Get the first occupation's code
                    code = occupations[0].get('code')
                    if code:
                        # Get skills for this occupation
                        skills_url = f'https://services.onetcenter.org/ws/online/occupations/{code}/details/skills'
                        skills_response = requests.get(skills_url, headers=headers)
                        
                        if skills_response.status_code == 200:
                            skills_data = skills_response.json()
                            return jsonify(skills_data.get('element', []))
            
            return jsonify([])
        else:
            return jsonify({'error': f'Error from O*NET API: {response.status_code}'}), 400
    except Exception as e:
        print(f"Error: {str(e)}")  # Add logging for debugging
        return jsonify({'error': str(e)}), 500