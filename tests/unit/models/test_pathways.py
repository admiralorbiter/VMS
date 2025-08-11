from datetime import datetime

import pytest

from models import db
from models.contact import Contact
from models.event import Event
from models.pathways import Pathway


@pytest.fixture
def test_contact(app):
    with app.app_context():
        contact = Contact(type="contact", first_name="Test", last_name="Contact")
        db.session.add(contact)
        db.session.commit()
        yield contact
        db.session.delete(contact)
        db.session.commit()


@pytest.fixture
def test_event(app):
    with app.app_context():
        event = Event(
            title="Test Event",
            type="IN_PERSON",
            start_date=datetime.now(),
            status="IN_PERSON",
            volunteers_needed=1,
        )
        db.session.add(event)
        db.session.commit()
        yield event
        db.session.delete(event)
        db.session.commit()


def test_create_pathway(app):
    with app.app_context():
        pathway = Pathway(salesforce_id="a005f000003XNa7AAG", name="Test Pathway")
        db.session.add(pathway)
        db.session.commit()

        assert pathway.id is not None
        assert pathway.salesforce_id == "a005f000003XNa7AAG"
        assert pathway.name == "Test Pathway"
        assert pathway.created_at is not None
        assert pathway.updated_at is not None

        # Cleanup
        db.session.delete(pathway)
        db.session.commit()


def test_salesforce_id_uniqueness(app):
    with app.app_context():
        pathway1 = Pathway(salesforce_id="a005f000003XNa7AAG", name="Test Pathway 1")
        db.session.add(pathway1)
        db.session.commit()

        # Try to create another pathway with same salesforce_id
        pathway2 = Pathway(salesforce_id="a005f000003XNa7AAG", name="Test Pathway 2")
        db.session.add(pathway2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

        db.session.delete(pathway1)
        db.session.commit()


def test_pathway_contact_relationship(app):
    with app.app_context():
        contact = Contact(type="contact", first_name="Test", last_name="Contact")
        db.session.add(contact)
        db.session.commit()
        pathway = Pathway(
            salesforce_id="a005f000003XNa8AAG", name="Contact Test Pathway"
        )
        db.session.add(pathway)
        db.session.commit()
        # Add contact to pathway
        pathway.contacts.append(contact)
        db.session.commit()
        # Test relationship
        assert contact in pathway.contacts
        assert pathway in contact.pathways
        # Test query methods
        contacts = pathway.contacts.all()
        assert len(contacts) == 1
        assert contacts[0].id == contact.id
        # Remove contact
        pathway.contacts.remove(contact)
        db.session.commit()
        db.session.delete(pathway)
        db.session.delete(contact)
        db.session.commit()


def test_pathway_event_relationship(app):
    with app.app_context():
        event = Event(
            title="Test Event",
            type="IN_PERSON",
            start_date=datetime.now(),
            status="Confirmed",
            volunteers_needed=1,
        )
        db.session.add(event)
        db.session.commit()
        pathway = Pathway(salesforce_id="a005f000003XNa9AAG", name="Event Test Pathway")
        db.session.add(pathway)
        db.session.commit()
        # Add event to pathway
        pathway.events.append(event)
        db.session.commit()
        # Test relationship
        assert event in pathway.events
        assert pathway in event.pathways
        # Test query methods
        events = pathway.events.all()
        assert len(events) == 1
        assert events[0].id == event.id
        # Remove event
        pathway.events.remove(event)
        db.session.commit()
        db.session.delete(pathway)
        db.session.delete(event)
        db.session.commit()


def test_pathway_name_validation(app):
    with app.app_context():
        # Test with required name
        pathway = Pathway(salesforce_id="a005f000003XNa0AAG", name="Valid Pathway Name")
        db.session.add(pathway)
        db.session.commit()
        assert pathway.name == "Valid Pathway Name"

        # Test with None name (should fail)
        pathway2 = Pathway(salesforce_id="a005f000003XNa1AAG", name=None)
        db.session.add(pathway2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

        db.session.delete(pathway)
        db.session.commit()


def test_timestamp_behavior(app):
    with app.app_context():
        pathway = Pathway(
            salesforce_id="a005f000003XNa2AAG", name="Timestamp Test Pathway"
        )
        db.session.add(pathway)
        db.session.commit()

        initial_created = pathway.created_at
        initial_updated = pathway.updated_at

        # Update the pathway
        pathway.name = "Updated Pathway Name"
        db.session.commit()

        # created_at should not change, updated_at should change
        assert pathway.created_at == initial_created
        # Add a small delay to ensure timestamp difference
        import time

        time.sleep(0.001)
        assert pathway.updated_at >= initial_updated

        db.session.delete(pathway)
        db.session.commit()


def test_cascade_deletion_contacts(app):
    with app.app_context():
        contact = Contact(type="contact", first_name="Test", last_name="Contact")
        db.session.add(contact)
        db.session.commit()
        pathway = Pathway(
            salesforce_id="a005f000003XNa3AAG", name="Cascade Test Pathway"
        )
        db.session.add(pathway)
        pathway.contacts.append(contact)
        db.session.commit()
        # Delete pathway
        db.session.delete(pathway)
        db.session.commit()
        # Contact should still exist, but relationship should be gone
        contact_check = db.session.get(Contact, contact.id)
        assert contact_check is not None
        db.session.delete(contact)
        db.session.commit()


def test_cascade_deletion_events(app):
    with app.app_context():
        event = Event(
            title="Test Event",
            type="IN_PERSON",
            start_date=datetime.now(),
            status="Confirmed",
            volunteers_needed=1,
        )
        db.session.add(event)
        db.session.commit()
        pathway = Pathway(
            salesforce_id="a005f000003XNa4AAG", name="Cascade Event Pathway"
        )
        db.session.add(pathway)
        pathway.events.append(event)
        db.session.commit()
        # Delete pathway
        db.session.delete(pathway)
        db.session.commit()
        # Event should still exist, but relationship should be gone
        event_check = db.session.get(Event, event.id)
        assert event_check is not None
        db.session.delete(event)
        db.session.commit()


def test_multiple_relationships(app):
    with app.app_context():
        contact = Contact(type="contact", first_name="Test", last_name="Contact")
        db.session.add(contact)
        db.session.commit()
        event = Event(
            title="Test Event",
            type="IN_PERSON",
            start_date=datetime.now(),
            status="Confirmed",
            volunteers_needed=1,
        )
        db.session.add(event)
        db.session.commit()
        pathway = Pathway(salesforce_id="a005f000003XNa5AAG", name="Multi Test Pathway")
        db.session.add(pathway)
        db.session.commit()
        # Add both contact and event
        pathway.contacts.append(contact)
        pathway.events.append(event)
        db.session.commit()
        # Test both relationships
        assert contact in pathway.contacts
        assert event in pathway.events
        # Remove both
        pathway.contacts.remove(contact)
        pathway.events.remove(event)
        db.session.commit()
        db.session.delete(pathway)
        db.session.delete(contact)
        db.session.delete(event)
        db.session.commit()
