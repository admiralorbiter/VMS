import pytest
from datetime import date, datetime
from models.contact import Contact, Phone, Email, Address, SalutationEnum, SuffixEnum, GenderEnum, ContactTypeEnum
from models import db

def test_new_contact(test_contact):
    """Test creating a new contact with basic information"""
    assert test_contact.first_name == 'John'
    assert test_contact.last_name == 'Doe'
    assert test_contact.salutation == SalutationEnum.mr
    assert test_contact.suffix == SuffixEnum.jr
    assert test_contact.gender == GenderEnum.male
    assert test_contact.birthdate == date(1990, 1, 1)
    assert test_contact.notes == 'Test contact notes'

def test_contact_relationships(test_contact):
    """Test contact relationships with Phone, Email, and Address"""
    # Test phone relationship
    assert test_contact.phones.count() == 1
    phone = test_contact.phones.first()
    assert phone.number == '123-456-7890'
    assert phone.type == ContactTypeEnum.personal
    assert phone.primary is True

    # Test email relationship
    assert test_contact.emails.count() == 1
    email = test_contact.emails.first()
    assert email.email == 'john.doe@example.com'
    assert email.type == ContactTypeEnum.personal
    assert email.primary is True

    # Test address relationship
    assert test_contact.addresses.count() == 1
    address = test_contact.addresses.first()
    assert address.address_line1 == '123 Main St'
    assert address.city == 'Kansas City'
    assert address.state == 'MO'
    assert address.zip_code == '64111'
    assert address.country == 'USA'
    assert address.type == ContactTypeEnum.personal
    assert address.primary is True

def test_salesforce_urls(test_contact):
    """Test Salesforce URL properties"""
    assert test_contact.salesforce_contact_url == 'https://prep-kc.lightning.force.com/lightning/r/Contact/003TESTID123456789/view'
    assert test_contact.salesforce_account_url is None  # No account ID set

    # Set account ID and test again
    test_contact.salesforce_account_id = '001TESTID123456789'
    assert test_contact.salesforce_account_url == 'https://prep-kc.lightning.force.com/lightning/r/Account/001TESTID123456789/view'

def test_contact_type_polymorphism():
    """Test contact type polymorphism"""
    contact = Contact(
        type='contact',
        first_name='Base',
        last_name='Contact'
    )
    assert contact.type == 'contact'
    assert isinstance(contact, Contact)

@pytest.mark.parametrize('invalid_data', [
    {'first_name': None, 'last_name': 'Doe'},  # Missing required first_name
    {'first_name': 'John', 'last_name': None},  # Missing required last_name
])
def test_contact_invalid_data(app, invalid_data):
    """Test contact creation with invalid data"""
    with app.app_context():
        contact = Contact(**invalid_data)
        with pytest.raises(Exception):  # SQLAlchemy will raise an error for nullable=False violations
            db.session.add(contact)
            db.session.commit()

def test_form_enum_choices():
    """Test FormEnum choices and choices_required methods"""
    # Test choices method
    assert SalutationEnum.choices() == [
        ('none', ''), ('mr', 'Mr.'), ('ms', 'Ms.'), 
        ('mrs', 'Mrs.'), ('dr', 'Dr.'), ('prof', 'Prof.'),
        ('mx', 'Mx.'), ('rev', 'Rev.'), ('hon', 'Hon.'),
        ('captain', 'Captain'), ('commissioner', 'Commissioner'),
        ('general', 'General'), ('judge', 'Judge'),
        ('officer', 'Officer'), ('staff_sergeant', 'Staff Sergeant')
    ]
    
    # Test choices_required method
    assert SalutationEnum.choices_required() == [
        ('none', ''), ('mr', 'Mr.'), ('ms', 'Ms.'), 
        ('mrs', 'Mrs.'), ('dr', 'Dr.'), ('prof', 'Prof.'),
        ('mx', 'Mx.'), ('rev', 'Rev.'), ('hon', 'Hon.'),
        ('captain', 'Captain'), ('commissioner', 'Commissioner'),
        ('general', 'General'), ('judge', 'Judge'),
        ('officer', 'Officer'), ('staff_sergeant', 'Staff Sergeant')
    ]

def test_email_to_dict(test_contact):
    """Test Email model's to_dict method"""
    email = test_contact.emails.first()
    email_dict = email.to_dict()
    
    assert email_dict == {
        'id': email.id,
        'email': 'john.doe@example.com',
        'type': 'personal',
        'primary': True
    }

    # Test with no type set
    email.type = None
    assert email.to_dict()['type'] == 'personal'  # Should default to personal

def test_address_with_line2(app):
    """Test Address model with address_line2"""
    with app.app_context():
        contact = Contact(
            type='contact',
            first_name='Jane',
            last_name='Smith'
        )
        
        address = Address(
            address_line1='456 Main St',
            address_line2='Apt 789',  # Testing address_line2
            city='Kansas City',
            state='MO',
            zip_code='64111',
            country='USA',
            type=ContactTypeEnum.personal,
            primary=True
        )
        
        contact.addresses.append(address)
        db.session.add(contact)
        db.session.commit()
        
        # Verify address was saved with line2
        saved_address = contact.addresses.first()
        assert saved_address.address_line1 == '456 Main St'
        assert saved_address.address_line2 == 'Apt 789'
        
        db.session.delete(contact)
        db.session.commit()

def test_name_properties(test_contact):
    """Test full_name and formal_name properties"""
    # Test full name without middle name
    assert test_contact.full_name == 'John Doe'
    
    # Test full name with middle name
    test_contact.middle_name = 'Michael'
    assert test_contact.full_name == 'John Michael Doe'
    
    # Test formal name with all components
    assert test_contact.formal_name == 'Mr. John Michael Doe Jr.'
    
    # Test formal name without optional components
    test_contact.salutation = SalutationEnum.none
    test_contact.suffix = SuffixEnum.none
    assert test_contact.formal_name == 'John Michael Doe'

def test_age_calculation(test_contact):
    """Test age property calculation"""
    # Test with a known birthdate
    test_contact.birthdate = date(1990, 1, 1)
    expected_age = date.today().year - 1990
    
    # Adjust for birthdate not yet reached this year
    if date.today().month < 1 or (date.today().month == 1 and date.today().day < 1):
        expected_age -= 1
    
    assert test_contact.age == expected_age
    
    # Test with no birthdate
    test_contact.birthdate = None
    assert test_contact.age is None

def test_contact_status_properties(test_contact):
    """Test contact status properties"""
    # Test valid email conditions
    assert test_contact.has_valid_email is True
    test_contact.email_opt_out = True
    assert test_contact.has_valid_email is False
    test_contact.email_opt_out = False
    test_contact.email_bounced_date = datetime.now()
    assert test_contact.has_valid_email is False
    
    # Test valid phone conditions
    assert test_contact.has_valid_phone is True
    test_contact.do_not_call = True
    assert test_contact.has_valid_phone is False
    
    # Test overall contactable status
    test_contact.do_not_call = False
    test_contact.email_bounced_date = None
    assert test_contact.is_contactable is True
    test_contact.do_not_contact = True
    assert test_contact.is_contactable is False

def test_address_formatting(test_contact):
    """Test address formatting properties"""
    # Test primary address retrieval
    primary_addr = test_contact.primary_address
    assert primary_addr is not None
    assert primary_addr.primary is True
    
    # Test US address formatting
    expected_us_format = "123 Main St\nKansas City, MO 64111"
    assert test_contact.formatted_primary_address == expected_us_format
    
    # Test international address formatting
    primary_addr.country = 'Canada'
    expected_intl_format = "123 Main St\nKansas City, MO 64111\nCanada"
    assert test_contact.formatted_primary_address == expected_intl_format
    
    # Test address with line2
    primary_addr.address_line2 = 'Suite 100'
    expected_with_line2 = "123 Main St\nSuite 100\nKansas City, MO 64111\nCanada"
    assert test_contact.formatted_primary_address == expected_with_line2
    
    # Test with no primary address
    test_contact.addresses = []
    assert test_contact.formatted_primary_address is None

def test_primary_validation(app):
    """Test validation of primary email and phone numbers"""
    with app.app_context():
        contact = Contact(
            type='contact',
            first_name='Test',
            last_name='Validation'
        )
        
        # First add the contact to the session
        db.session.add(contact)
        
        # Add multiple primary emails
        email1 = Email(email='test1@example.com', primary=True)
        email2 = Email(email='test2@example.com', primary=True)
        contact.emails.append(email1)
        contact.emails.append(email2)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Contact cannot have multiple primary emails"):
            contact.validate_email_primary_status()
        
        # Add multiple primary phones
        phone1 = Phone(number='123-456-7890', primary=True)
        phone2 = Phone(number='098-765-4321', primary=True)
        contact.phones.append(phone1)
        contact.phones.append(phone2)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Contact cannot have multiple primary phones"):
            contact.validate_phone_primary_status()
            
        # Clean up
        db.session.rollback() 