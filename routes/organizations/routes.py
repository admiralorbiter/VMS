from flask import Blueprint, request, render_template, jsonify, flash, redirect, url_for
from flask_login import login_required
from models import Volunteer, db
from models.event import Event
from models.organization import Organization, VolunteerOrganization
from models.volunteer import EventParticipation
from routes.utils import parse_date
import csv
import os
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from config import Config

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
    # Get pagination and sorting parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    sort_by = request.args.get('sort', 'name')  # Default sort by name
    sort_dir = request.args.get('direction', 'asc')  # Default ascending

    # Create current_filters dictionary
    current_filters = {
        'search_name': request.args.get('search_name', '').strip(),
        'type': request.args.get('type', ''),
        'per_page': per_page,
        'sort': sort_by,
        'direction': sort_dir
    }

    # Build query
    query = Organization.query

    # Apply filters
    if current_filters.get('search_name'):
        search_term = f"%{current_filters['search_name']}%"
        query = query.filter(Organization.name.ilike(search_term))

    if current_filters.get('type'):
        query = query.filter(Organization.type == current_filters['type'])

    # Apply sorting
    sort_column = getattr(Organization, sort_by, Organization.name)
    if sort_dir == 'desc':
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Get unique types for filter dropdown
    organization_types = db.session.query(Organization.type)\
        .filter(Organization.type.isnot(None))\
        .distinct()\
        .order_by(Organization.type)\
        .all()
    organization_types = [t[0] for t in organization_types if t[0]]

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

@organizations_bp.route('/organizations/add', methods=['GET', 'POST'])
@login_required
def add_organization():
    if request.method == 'POST':
        try:
            # Create new organization
            organization = Organization(
                name=request.form['name'],
                type=request.form['type'],
                description=request.form['description'],
                billing_street=request.form['billing_street'],
                billing_city=request.form['billing_city'],
                billing_state=request.form['billing_state'],
                billing_postal_code=request.form['billing_postal_code'],
                billing_country=request.form['billing_country']
            )
            
            db.session.add(organization)
            db.session.commit()
            
            flash('Organization created successfully!', 'success')
            return redirect(url_for('organizations.organizations'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating organization: {str(e)}', 'error')
            return redirect(url_for('organizations.add_organization'))
    
    # Get unique organization types for the dropdown
    organization_types = db.session.query(Organization.type)\
        .filter(Organization.type.isnot(None))\
        .distinct()\
        .order_by(Organization.type)\
        .all()
    organization_types = [t[0] for t in organization_types if t[0]]
    
    return render_template('organizations/add_organization.html',
                         organization_types=organization_types)

@organizations_bp.route('/organizations/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_organization(id):
    try:
        organization = Organization.query.get_or_404(id)
        
        # Delete associated volunteer organizations first
        VolunteerOrganization.query.filter_by(organization_id=id).delete()
        
        # Delete the organization
        db.session.delete(organization)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@organizations_bp.route('/organizations/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_organization(id):
    organization = Organization.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update organization fields
            organization.name = request.form['name']
            organization.type = request.form['type']
            organization.description = request.form['description']
            organization.billing_street = request.form['billing_street']
            organization.billing_city = request.form['billing_city']
            organization.billing_state = request.form['billing_state']
            organization.billing_postal_code = request.form['billing_postal_code']
            organization.billing_country = request.form['billing_country']
            
            db.session.commit()
            flash('Organization updated successfully!', 'success')
            return redirect(url_for('organizations.organizations'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating organization: {str(e)}', 'error')
            return redirect(url_for('organizations.edit_organization', id=id))
    
    # Get unique organization types for the dropdown
    organization_types = db.session.query(Organization.type)\
        .filter(Organization.type.isnot(None))\
        .distinct()\
        .order_by(Organization.type)\
        .all()
    organization_types = [t[0] for t in organization_types if t[0]]
    
    return render_template('organizations/edit_organization.html',
                         organization=organization,
                         organization_types=organization_types)

@organizations_bp.route('/organizations/purge', methods=['POST'])
@login_required
def purge_organizations():
    try:
        # First delete all volunteer organization affiliations
        VolunteerOrganization.query.delete()
        
        # Then delete all organizations
        Organization.query.delete()
        
        # Commit the changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All organizations and their affiliations have been purged'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@organizations_bp.route('/organizations/import-from-salesforce', methods=['POST'])
@login_required
def import_organizations_from_salesforce():
    try:
        print("Fetching organizations from Salesforce...")
        success_count = 0
        error_count = 0
        affiliation_success = 0
        affiliation_error = 0
        errors = []

        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )

        # First query: Get organizations
        org_query = """
        SELECT Id, Name, Type, Description, ParentId, 
               BillingStreet, BillingCity, BillingState, 
               BillingPostalCode, BillingCountry, LastActivityDate
        FROM Account
        WHERE Type NOT IN ('Household', 'School District', 'School')
        ORDER BY Name ASC
        """

        # Execute organizations query
        result = sf.query_all(org_query)
        sf_rows = result.get('records', [])

        # Process organizations
        for row in sf_rows:
            try:
                # Check if organization exists
                org = Organization.query.filter_by(salesforce_id=row['Id']).first()
                if not org:
                    org = Organization()
                    db.session.add(org)
                
                # Update organization fields
                org.salesforce_id = row['Id']
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
                errors.append(f"Error processing organization {row.get('Name', 'Unknown')}: {str(e)}")
                continue

        # Second query: Get affiliations
        affiliation_query = """
        SELECT Id, Name, npe5__Organization__c, npe5__Contact__c, 
               npe5__Role__c, npe5__Primary__c, npe5__Status__c, 
               npe5__StartDate__c, npe5__EndDate__c
        FROM npe5__Affiliation__c
        """

        # Execute affiliations query
        affiliation_result = sf.query_all(affiliation_query)
        affiliation_rows = affiliation_result.get('records', [])

        # Process affiliations
        for row in affiliation_rows:
            try:
                # Get the organization and volunteer by their Salesforce IDs
                org = Organization.query.filter_by(
                    salesforce_id=row.get('npe5__Organization__c')
                ).first()
                
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
                    vol_org.is_primary = row.get('npe5__Primary__c') == 'true'
                    vol_org.status = row.get('npe5__Status__c')
                    
                    if row.get('npe5__StartDate__c'):
                        vol_org.start_date = parse_date(row['npe5__StartDate__c'])
                    if row.get('npe5__EndDate__c'):
                        vol_org.end_date = parse_date(row['npe5__EndDate__c'])
                    
                    affiliation_success += 1
                else:
                    affiliation_error += 1
                    if not org:
                        errors.append(f"Organization with Salesforce ID {row.get('npe5__Organization__c')} not found")
                    if not volunteer:
                        errors.append(f"Volunteer with Salesforce ID {row.get('npe5__Contact__c')} not found")

            except Exception as e:
                affiliation_error += 1
                errors.append(f"Error processing affiliation: {str(e)}")
                continue

        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': (f'Successfully processed {success_count} organizations and '
                       f'{affiliation_success} affiliations with '
                       f'{error_count + affiliation_error} total errors'),
            'errors': errors
        })

    except SalesforceAuthenticationFailed:
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        db.session.rollback()
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
