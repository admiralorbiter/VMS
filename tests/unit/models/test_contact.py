import pytest
from datetime import date
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