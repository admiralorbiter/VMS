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
    """Search O*NET database for occupations or skills"""
    try:
        keyword = request.args.get('keyword', '')
        search_type = request.args.get('type', 'occupation')
        headers = get_onet_headers()
        
        if search_type == 'skills':
            # Search for skills using O*NET API
            skills_url = 'https://services.onetcenter.org/ws/online/occupations/list/skills'
            response = requests.get(skills_url, headers=headers)
            
            if response.status_code == 200:
                skills_data = response.json()
                
                matching_skills = []
                
                if 'element' in skills_data:
                    all_skills = skills_data['element']
                    
                    matching_skills = [
                        {
                            'name': skill.get('name', ''),
                            'description': skill.get('description', ''),
                            'score': {
                                'value': 0,  # Default score since this is just a skill search
                                'important': False
                            }
                        }
                        for skill in all_skills
                        if keyword.lower() in skill.get('name', '').lower() or 
                           keyword.lower() in skill.get('description', '').lower()
                    ]
                return jsonify(matching_skills)
            else:
                return jsonify({'error': f'Error from O*NET API: {response.status_code}'}), 400
        else:
            # Existing occupation search logic
            search_url = f'https://services.onetcenter.org/ws/online/search?keyword={keyword}'
            response = requests.get(search_url, headers=headers)
            
            if response.status_code == 200:
                search_data = response.json()
                if 'occupation' in search_data:
                    occupations = search_data['occupation']
                    if isinstance(occupations, list):
                        return jsonify(occupations)
                    else:
                        return jsonify([occupations])
                return jsonify([])
            else:
                return jsonify({'error': f'Error from O*NET API: {response.status_code}'}), 400
                
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
                all_skills = skills_data['element']
                
                details['skills'] = [
                    {
                        'name': skill.get('name', ''),
                        'description': skill.get('description', ''),
                        'level': skill.get('score', {}).get('value', 0),
                        'importance': skill.get('score', {}).get('important', False)
                    }
                    for skill in all_skills
                ]
        
        # Get knowledge areas with level data
        knowledge_url = f'https://services.onetcenter.org/ws/online/occupations/{code}/details/knowledge'
        knowledge_response = requests.get(knowledge_url, headers=headers)
        
        if knowledge_response.status_code == 200:
            knowledge_data = knowledge_response.json()
            
            if 'element' in knowledge_data:
                all_knowledge = knowledge_data['element']
                
                details['knowledge'] = [
                    {
                        'name': item.get('name', ''),
                        'description': item.get('description', ''),
                        'level': item.get('score', {}).get('value', 0),
                        'importance': item.get('score', {}).get('important', False)
                    }
                    for item in all_knowledge
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

@playground_bp.route('/playground/search')
def search():
    """Search for jobs or skills based on query"""
    try:
        query = request.args.get('query', '')
        search_type = request.args.get('type', 'job')  # 'job' or 'skill'
        headers = get_onet_headers()
        
        if search_type == 'skill':
            # First, get a list of occupations that match the query
            search_url = f'https://services.onetcenter.org/ws/online/search?keyword={query}'
            response = requests.get(search_url, headers=headers)
            
            if response.status_code == 200:
                search_data = response.json()
                matching_skills = set()  # Use a set to avoid duplicates
                
                # Get skills for each matching occupation
                if 'occupation' in search_data:
                    occupations = search_data['occupation']
                    if not isinstance(occupations, list):
                        occupations = [occupations]
                    
                    for occupation in occupations[:3]:  # Limit to first 3 occupations to avoid too many requests
                        code = occupation.get('code')
                        if code:
                            skills_url = f'https://services.onetcenter.org/ws/online/occupations/{code}/details/skills'
                            skills_response = requests.get(skills_url, headers=headers)
                            
                            if skills_response.status_code == 200:
                                skills_data = skills_response.json()
                                if 'element' in skills_data:
                                    # Convert skills to list of dicts and add to set
                                    for skill in skills_data['element']:
                                        skill_dict = {
                                            'code': skill.get('id', ''),
                                            'title': skill.get('name', ''),
                                            'description': skill.get('description', '')
                                        }
                                        # Convert dict to tuple of items for set storage
                                        skill_tuple = tuple(sorted(skill_dict.items()))
                                        matching_skills.add(skill_tuple)
                
                # Convert back to list of dicts and filter by query
                final_skills = [dict(skill) for skill in matching_skills]
                filtered_skills = [
                    skill for skill in final_skills
                    if query.lower() in skill['title'].lower() or 
                       query.lower() in skill['description'].lower()
                ]
                
                return jsonify(filtered_skills)
            
            return jsonify([])
            
        else:
            # Existing job search logic
            search_url = f'https://services.onetcenter.org/ws/online/search?keyword={query}'
            response = requests.get(search_url, headers=headers)
            
            if response.status_code == 200:
                search_data = response.json()
                if 'occupation' in search_data:
                    occupations = search_data['occupation']
                    if isinstance(occupations, list):
                        return jsonify(occupations)
                    else:
                        return jsonify([occupations])
                return jsonify([])
            else:
                return jsonify({'error': f'Error from O*NET API: {response.status_code}'}), 400
                
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playground_bp.route('/playground/skill/<skill_id>')
def get_skill_details(skill_id):
    """Get detailed information about a specific skill"""
    try:
        headers = get_onet_headers()
        details = {'id': skill_id}
        
        # First, search for occupations to get a sample occupation that has this skill
        search_url = 'https://services.onetcenter.org/ws/online/search?keyword=manager'  # Use a common occupation
        response = requests.get(search_url, headers=headers)
        
        if response.status_code == 200:
            search_data = response.json()
            if 'occupation' in search_data:
                # Take the first occupation to get skill details
                occupation = search_data['occupation'][0] if isinstance(search_data['occupation'], list) else search_data['occupation']
                occ_code = occupation.get('code')
                
                # Get skills for this occupation to find our target skill
                skills_url = f'https://services.onetcenter.org/ws/online/occupations/{occ_code}/details/skills'
                skills_response = requests.get(skills_url, headers=headers)
                
                if skills_response.status_code == 200:
                    skills_data = skills_response.json()
                    if 'element' in skills_data:
                        # Find our target skill
                        target_skill = None
                        for skill in skills_data['element']:
                            if skill.get('id') == skill_id:
                                target_skill = skill
                                break
                        
                        if target_skill:
                            details.update({
                                'title': target_skill.get('name', ''),
                                'description': target_skill.get('description', ''),
                                'element_id': target_skill.get('id', '')
                            })
                            
                            # Now get occupations that use this skill
                            occupations_url = f'https://services.onetcenter.org/ws/online/search?keyword={details["title"]}'
                            occupations_response = requests.get(occupations_url, headers=headers)
                            
                            if occupations_response.status_code == 200:
                                occupations_data = occupations_response.json()
                                if 'occupation' in occupations_data:
                                    occupations = occupations_data['occupation']
                                    if not isinstance(occupations, list):
                                        occupations = [occupations]
                                        
                                    # Get detailed skill information for each occupation
                                    related_occupations = []
                                    for occ in occupations[:5]:  # Limit to 5 occupations
                                        occ_skills_url = f'https://services.onetcenter.org/ws/online/occupations/{occ["code"]}/details/skills'
                                        occ_skills_response = requests.get(occ_skills_url, headers=headers)
                                        
                                        if occ_skills_response.status_code == 200:
                                            occ_skills_data = occ_skills_response.json()
                                            if 'element' in occ_skills_data:
                                                for skill in occ_skills_data['element']:
                                                    if skill.get('id') == skill_id:
                                                        related_occupations.append({
                                                            'code': occ['code'],
                                                            'title': occ['title'],
                                                            'description': occ.get('description', ''),
                                                            'score': skill.get('score', {}).get('value', 0),
                                                            'importance': skill.get('score', {}).get('important', False)
                                                        })
                                                        break
                                    
                                    details['related_occupations'] = related_occupations
                            
                            # Get related skills by looking at the skills from related occupations
                            related_skills = {}
                            for occ in details.get('related_occupations', []):
                                skills_url = f'https://services.onetcenter.org/ws/online/occupations/{occ["code"]}/details/skills'
                                skills_response = requests.get(skills_url, headers=headers)
                                
                                if skills_response.status_code == 200:
                                    skills_data = skills_response.json()
                                    if 'element' in skills_data:
                                        for skill in skills_data['element']:
                                            if skill.get('id') != skill_id:  # Don't include the target skill
                                                skill_key = skill.get('id')
                                                if skill_key not in related_skills:
                                                    related_skills[skill_key] = {
                                                        'code': skill.get('id'),
                                                        'title': skill.get('name'),
                                                        'description': skill.get('description'),
                                                        'score': skill.get('score', {}).get('value', 0),
                                                        'count': 1
                                                    }
                                                else:
                                                    related_skills[skill_key]['count'] += 1
                                                    related_skills[skill_key]['score'] = max(
                                                        related_skills[skill_key]['score'],
                                                        skill.get('score', {}).get('value', 0)
                                                    )
                            
                            # Sort related skills by count and score
                            sorted_skills = sorted(
                                related_skills.values(),
                                key=lambda x: (x['count'], x['score']),
                                reverse=True
                            )
                            details['related_skills'] = sorted_skills[:10]  # Top 10 related skills
                            
                            return jsonify(details)
        
        return jsonify({'error': 'Skill not found'}), 404
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500