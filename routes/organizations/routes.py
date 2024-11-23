from flask import Blueprint, request, render_template, jsonify, flash
from flask_login import login_required
from models import Volunteer, db
from models.event import Event
from models.organization import Organization, VolunteerOrganization
from models.volunteer import EventParticipation
from routes.utils import parse_date
import csv
import os

organizations_bp = Blueprint('organizations', __name__)

@organizations_bp.route('/organizations/import', methods=['GET', 'POST'])
@login_required
def import_organizations():
    if request.method == 'GET':
        return render_template('organizations/import.html')
    
    try:
        success_count = 0
        error_count = 0
        errors = []

        # Determine import type
        import_type = request.json.get('importType', 'organizations') if request.is_json else request.form.get('importType', 'organizations')
        
        if request.is_json and request.json.get('quickSync'):
            # Set file path based on import type
            file_path = os.path.join('data', 'Organizations.csv' if import_type == 'organizations' else 'npe5__Affiliation__c.csv')
            
            if not os.path.exists(file_path):
                return jsonify({'error': f'Default CSV file not found for {import_type}'}), 404
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                content = file.read().replace('\0', '')
                csv_data = csv.DictReader(content.splitlines())
                
                if import_type == 'organizations':
                    for row in csv_data:
                        try:
                            org = Organization.query.filter_by(salesforce_id=row.get('Id')).first()
                            if not org:
                                org = Organization()
                                db.session.add(org)
                            
                            # Update organization fields
                            org.salesforce_id = row.get('Id')
                            org.name = row.get('Name', '')
                            org.type = row.get('Type')
                            org.description = row.get('Description')
                            org.volunteer_parent_id = row.get('ParentId')
                            org.billing_street = row.get('BillingStreet')
                            org.billing_city = row.get('BillingCity')
                            org.billing_state = row.get('BillingState')
                            org.billing_postal_code = row.get('BillingPostalCode')
                            org.billing_country = row.get('BillingCountry')
                            
                            if row.get('LastActivityDate'):
                                org.last_activity_date = parse_date(row['LastActivityDate'])
                            
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Error processing organization: {str(e)}")
                            continue
                
                else:  # affiliations
                    for row in csv_data:
                        try:
                            # Get the organization and volunteer by their Salesforce IDs
                            org = Organization.query.filter_by(
                                salesforce_id=row.get('npe5__Organization__c')
                            ).first()
                            
                            # Use salesforce_individual_id instead of salesforce_id
                            volunteer = Volunteer.query.filter_by(
                                salesforce_individual_id=row.get('npe5__Contact__c')
                            ).first()

                            if org and volunteer:
                                # Check for existing relationship
                                vol_org = VolunteerOrganization.query.filter_by(
                                    volunteer_id=volunteer.id,
                                    organization_id=org.id
                                ).first()

                                if not vol_org:
                                    vol_org = VolunteerOrganization(
                                        volunteer_id=volunteer.id,
                                        organization_id=org.id
                                    )
                                    db.session.add(vol_org)

                                # Update relationship details
                                vol_org.salesforce_volunteer_id = row.get('npe5__Contact__c')
                                vol_org.salesforce_org_id = row.get('npe5__Organization__c')
                                vol_org.role = row.get('npe5__Role__c')
                                vol_org.is_primary = row.get('npe5__Primary__c') == '1'
                                vol_org.status = row.get('npe5__Status__c')
                                
                                if row.get('npe5__StartDate__c'):
                                    vol_org.start_date = parse_date(row['npe5__StartDate__c'])
                                if row.get('npe5__EndDate__c'):
                                    vol_org.end_date = parse_date(row['npe5__EndDate__c'])
                                
                                success_count += 1
                            else:
                                error_count += 1
                                if not org:
                                    errors.append(f"Organization with Salesforce ID {row.get('npe5__Organization__c')} not found")
                                if not volunteer:
                                    errors.append(f"Volunteer with Salesforce ID {row.get('npe5__Contact__c')} not found")
                                
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Error processing affiliation: {str(e)}")
                            continue

        # Commit all changes
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'successCount': success_count,
                'errorCount': error_count,
                'errors': errors
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
                
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
        
@organizations_bp.route('/organizations')
@login_required
def organizations():
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)

    # Create current_filters dictionary
    current_filters = {
        'search_name': request.args.get('search_name', '').strip(),
        'type': request.args.get('type', ''),
        'per_page': per_page
    }

    # Remove empty filters
    current_filters = {k: v for k, v in current_filters.items() if v}

    # Build query
    query = Organization.query

    # Apply filters
    if current_filters.get('search_name'):
        search_term = f"%{current_filters['search_name']}%"
        query = query.filter(Organization.name.ilike(search_term))

    if current_filters.get('type'):
        query = query.filter(Organization.type == current_filters['type'])

    # Get unique types for filter dropdown
    organization_types = db.session.query(Organization.type)\
        .filter(Organization.type.isnot(None))\
        .distinct()\
        .order_by(Organization.type)\
        .all()
    organization_types = [t[0] for t in organization_types if t[0]]

    # Default sort by name
    query = query.order_by(Organization.name)

    # Apply pagination
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template('organizations/organizations.html',
                         organizations=pagination.items,
                         pagination=pagination,
                         current_filters=current_filters,
                         organization_types=organization_types)

@organizations_bp.route('/organizations/view/<int:id>')
@login_required
def view_organization(id):
    organization = Organization.query.get_or_404(id)
    
    # Get all volunteers associated with this organization
    volunteers = organization.volunteers  # Using the relationship directly
    
    # Get recent events/activities
    recent_activities = []
    for volunteer in volunteers:
        participations = EventParticipation.query.filter_by(volunteer_id=volunteer.id)\
            .join(Event)\
            .order_by(Event.start_date.desc())\
            .limit(5)\
            .all()
        recent_activities.extend(participations)
    
    # Sort activities by event date
    recent_activities.sort(key=lambda x: x.event.start_date, reverse=True)
    
    return render_template(
        'organizations/view.html',
        organization=organization,
        volunteers=volunteers,
        recent_activities=recent_activities[:10]  # Limit to 10 most recent
    )