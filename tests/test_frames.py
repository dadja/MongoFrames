from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
import pytest
from time import sleep
from unittest.mock import Mock

from mongoframes import *


# Classes

class Dragon(Frame):
    """
    A dragon.
    """

    _fields = {
        'name',
        'breed'
        }
    _private_fields = {'breed'}


class Inventory(SubFrame):
    """
    An inventory of items kept within a lair.
    """

    _fields = {
        'gold',
        'skulls'
        }
    _private_fields = {'gold'}


class Lair(Frame):
    """
    A lair in which a dragon resides.
    """

    _fields = {
        'name',
        'inventory'
        }


class ComplexDragon(Dragon):

    _fields = Dragon._fields | {
        'dob',
        'lair',
        'traits',
        'misc'
        }

    _default_projection = {
        'lair': {
            '$ref': Lair,
            'inventory': {'$sub': Inventory}
            }
        }

class MonitoredDragon(Dragon):

    _fields = Dragon._fields | {
        'created',
        'modified'
        }


# Fixtures

@pytest.fixture(scope='function')
def mongo_client(request):
    """Connect to the test database"""

    # Connect to mongodb and create a test database
    Frame._client = MongoClient('mongodb://localhost:27017/mongoframes_test')

    def fin():
        # Remove the test database
        Frame._client.drop_database('mongoframes_test')

    request.addfinalizer(fin)

    return Frame._client

@pytest.fixture(scope='function')
def example_dataset_one(request):
    """Create an example set of data that can be used in testing"""
    inventory = Inventory(
        gold=1000,
        skulls=100
        )

    cave = Lair(
        name='Cave',
        inventory=inventory
        )
    cave.insert()

    burt = ComplexDragon(
        name='Burt',
        dob=datetime(1979, 6, 11),
        breed='Cold-drake',
        lair=cave,
        traits=['irritable', 'narcissistic']
        )
    burt.insert()

@pytest.fixture(scope='function')
def example_dataset_many(request):
    """Create an example set of data that can be used in testing"""

    # Burt
    cave = Lair(
        name='Cave',
        inventory=Inventory(
            gold=1000,
            skulls=100
            )
        )
    cave.insert()

    burt = ComplexDragon(
        name='Burt',
        dob=datetime(1979, 6, 11),
        breed='Cold-drake',
        lair=cave,
        traits=['irritable', 'narcissistic']
        )
    burt.insert()

    # Fred
    castle = Lair(
        name='Castle',
        inventory=Inventory(
            gold=2000,
            skulls=200
            )
        )
    castle.insert()

    fred = ComplexDragon(
        name='Fred',
        dob=datetime(1980, 7, 12),
        breed='Fire-drake',
        lair=castle,
        traits=['impulsive', 'loyal']
        )
    fred.insert()

    # Fred
    mountain = Lair(
        name='Mountain',
        inventory=Inventory(
            gold=3000,
            skulls=300
            )
        )
    mountain.insert()

    albert = ComplexDragon(
        name='Albert',
        dob=datetime(1981, 8, 13),
        breed='Stone dragon',
        lair=mountain,
        traits=['reclusive', 'cunning']
        )
    albert.insert()


# Tests

def test_frame():
    """Should create a new Dragon instance"""

    # Passing no inital values
    burt = Dragon()
    assert isinstance(burt, Dragon)

    # Passing initial values
    burt = Dragon(
        name='Burt',
        breed='Cold-drake'
        )
    assert burt.name == 'Burt'
    assert burt.breed == 'Cold-drake'

def test_dot_notation():
    """
    Should allow access to read and set document values using do notation.
    """

    # Simple set/get
    burt = Dragon(
        name='Burt',
        breed='Cold-drake'
        )

    assert burt.name == 'Burt'
    burt.name = 'Fred'
    assert burt.name == 'Fred'

    # SubFrame (embedded document get/set)
    inventory = Inventory(
        gold=1000,
        skulls=100
        )

    cave = Lair(
        name='Cave',
        inventory=inventory
        )

    assert cave.inventory.gold == 1000
    cave.inventory.gold += 100
    assert cave.inventory.gold == 1100

def test_equal(mongo_client):
    """Should compare the equality of two Frame instances by Id"""

    # Create some dragons
    burt = Dragon(
        name='Burt',
        breed='Cold-drake'
        )
    burt.insert()

    fred = Dragon(
        name='Fred',
        breed='Fire-drake'
        )
    fred.insert()

    # Test equality
    assert burt != fred
    assert burt == burt

def test_python_sort(mongo_client):
    """Should sort a list of Frame instances by their Ids"""

    # Create some dragons
    burt = Dragon(
        name='Burt',
        breed='Cold-drake'
        )
    burt.insert()

    fred = Dragon(
        name='Fred',
        breed='Fire-drake'
        )
    fred.insert()

    albert = Dragon(
        name='Albert',
        breed='Stone dragon'
        )
    albert.insert()

    # Test sorting by Id
    assert sorted([albert, burt, fred]) == [burt, fred, albert]

def test_to_json_type(mongo_client, example_dataset_one):
    """
    Should return a dictionary for the document with all values converted to
    JSON safe types. All private fields should be excluded.
    """

    burt = ComplexDragon.one(Q.name == 'Burt')
    cave = burt.lair

    assert burt.to_json_type() == {
        '_id': str(burt._id),
        'name': 'Burt',
        'dob': '1979-06-11 00:00:00',
        'traits': ['irritable', 'narcissistic'],
        'lair': {
            '_id': str(cave._id),
            'name': 'Cave',
            'inventory': {
                'skulls': 100
                }
            }
        }

def test_insert(mongo_client):
    """Should insert a document into the database"""

    # Create some convoluted data to insert
    inventory = Inventory(
        gold=1000,
        skulls=100
        )

    cave = Lair(
        name='Cave',
        inventory=inventory
        )
    cave.insert()

    burt = ComplexDragon(
        name='Burt',
        dob=datetime(1979, 6, 11),
        breed='Cold-drake',
        lair=cave,
        traits=['irritable', 'narcissistic']
        )
    burt.insert()

    # Test the document now has an Id
    assert burt._id is not None

    # Get the document from the database and check it's values
    burt.reload()

    assert burt.name == 'Burt'
    assert burt.dob == datetime(1979, 6, 11)
    assert burt.breed == 'Cold-drake'
    assert burt.traits == ['irritable', 'narcissistic']
    assert burt.lair.name == 'Cave'
    assert burt.lair.inventory.gold == 1000
    assert burt.lair.inventory.skulls == 100

def test_update(mongo_client, example_dataset_one):
    """Should update a document on the database"""

    # Update all values
    burt = ComplexDragon.one(Q.name == 'Burt')

    burt.name = 'Jess'
    burt.breed = 'Fire-drake'
    burt.traits = ['gentle', 'kind']
    burt.update()

    burt.reload()

    assert burt.name == 'Jess'
    assert burt.breed == 'Fire-drake'
    assert burt.traits == ['gentle', 'kind']

    # Selective update
    burt.lair.name = 'Castle'
    burt.lair.inventory.gold += 100
    burt.lair.inventory.skulls = 0
    burt.lair.update('name', 'inventory.skulls')

    burt.reload()

    assert burt.lair.name == 'Castle'
    assert burt.lair.inventory.gold == 1000
    assert burt.lair.inventory.skulls == 0

def test_upsert(mongo_client):
    """
    Should update or insert a document on the database depending on whether or
    not it already exists.
    """

    # Insert
    burt = Dragon(
        name='Burt',
        breed='Cold-drake'
        )
    burt.upsert()
    id = burt._id
    burt.reload()

    # Update
    burt.upsert()
    burt.reload()

    assert burt._id == id

def test_delete(mongo_client, example_dataset_one):
    """Should delete a document from the database"""
    burt = ComplexDragon.one(Q.name == 'Burt')
    burt.delete()
    burt = burt.by_id(burt._id)

    assert burt is None

def test_insert_many(mongo_client):
    """Should insert multiple documents records into the database"""

    # Create some convoluted data to insert
    burt = Dragon(
        name='Burt',
        breed='Cold-drake'
        )

    fred = Dragon(
        name='Fred',
        breed='Fire-drake'
        )

    albert = Dragon(
        name='Albert',
        breed='Stone dragon'
        )

    burt.insert_many([burt, fred, albert])

    # Check 3 dragons have been created
    assert Dragon.count() == 3

    # Check the details for each dragon
    dragons = Dragon.many()
    assert dragons[0].name == 'Burt'
    assert dragons[0].breed == 'Cold-drake'
    assert dragons[1].name == 'Fred'
    assert dragons[1].breed == 'Fire-drake'
    assert dragons[2].name == 'Albert'
    assert dragons[2].breed == 'Stone dragon'

def test_update_many(mongo_client, example_dataset_many):
    """Should update mulitple documents on the database"""

    # Select all the dragons
    dragons = ComplexDragon.many()

    # Give each dragon a second name
    for dragon in dragons:
        dragon.name += ' ' + dragon.name + 'son'

    # Update all values for all the dragons in one go
    ComplexDragon.update_many(dragons)

    # Reload all the dragons
    dragons = ComplexDragon.many(sort=[('_id', ASC)])

    assert dragons[0].name == 'Burt Burtson'
    assert dragons[1].name == 'Fred Fredson'
    assert dragons[2].name == 'Albert Albertson'

    # Make various changes to the dragons only some of which we want to stick
    for dragon in dragons:
        dragon.name = dragon.name.split(' ')[0]
        dragon.breed = dragon.breed.replace('-', '_')
        dragon.breed = dragon.breed.replace(' ', '_')
        dragon.lair.inventory.gold += 100
        dragon.lair.inventory.skulls += 10

    # Update selected values for all the dragons in one go
    Lair.update_many([d.lair for d in dragons], 'inventory.gold')
    ComplexDragon.update_many(dragons, 'breed')

    # Reload all the dragons
    dragons = ComplexDragon.many()

    # Names should be the same
    assert dragons[0].name == 'Burt Burtson'
    assert dragons[1].name == 'Fred Fredson'
    assert dragons[2].name == 'Albert Albertson'

    # Breeds should have changed
    assert dragons[0].breed == 'Cold_drake'
    assert dragons[1].breed == 'Fire_drake'
    assert dragons[2].breed == 'Stone_dragon'

    # Gold should have changed
    assert dragons[0].lair.inventory.gold == 1100
    assert dragons[1].lair.inventory.gold == 2100
    assert dragons[2].lair.inventory.gold == 3100

    # Skulls should be the same
    assert dragons[0].lair.inventory.skulls == 100
    assert dragons[1].lair.inventory.skulls == 200
    assert dragons[2].lair.inventory.skulls == 300

def test_delete_many(mongo_client, example_dataset_many):
    """Should delete mulitple documents from the database"""

    # Select all the dragons
    dragons = ComplexDragon.many()

    # Delete all of them :(
    ComplexDragon.delete_many(dragons)

    # Check there are no remaining dragons
    assert ComplexDragon.count() == 0

def test_reload(mongo_client, example_dataset_one):
    """Should reload the current document's values from the database"""

    # Select Burt from the database
    burt = ComplexDragon.one(Q.name == 'Burt')

    # Change some values and reload
    burt.name = 'Fred'
    burt.lair.inventory = Inventory(gold=500, skulls=50)
    burt.reload()

    # Check Burt is himself again
    assert burt.name == 'Burt'
    assert burt.lair.inventory.gold == 1000
    assert burt.lair.inventory.skulls == 100

    # Reload with a different projection
    burt.reload(projection={'name': True})

    # Check Burt has values for the projection specified
    assert burt.name == 'Burt'
    assert burt.breed == None
    assert burt.lair == None

def test_by_id(mongo_client, example_dataset_many):
    """Should return a document by Id from the database"""

    # Get an Id for a dragon
    id = ComplexDragon.one(Q.name == 'Fred')._id

    # Load a dragon using the Id and make sure it's the same
    fred = ComplexDragon.by_id(id)

    assert fred.name == 'Fred'

def test_count(mongo_client, example_dataset_many):
    """Should return a count for documents matching the given query"""

    # Count all dragons
    count = ComplexDragon.count()
    assert count == 3

    # Count dragons that are cold or fire drakes
    count = ComplexDragon.count(In(Q.breed, ['Cold-drake', 'Fire-drake']))
    assert count == 2

    # Count dragons born after 1980
    count = ComplexDragon.count(Q.dob >= datetime(1981, 1, 1))
    assert count == 1

def test_ids(mongo_client, example_dataset_many):
    """Should return a list of ids for documents matching the given query"""

    # Ids for all dragons
    ids = ComplexDragon.ids()
    assert len(ids) == 3

    # Ids for dragons that are cold or fire drakes
    ids = ComplexDragon.ids(In(Q.breed, ['Cold-drake', 'Fire-drake']))
    assert len(ids) == 2

    # Ids for dragons born after 1980
    ids = ComplexDragon.ids(Q.dob >= datetime(1981, 1, 1))
    assert len(ids) == 1

def test_one(mongo_client, example_dataset_many):
    """Should return a the first document that matches the given query"""

    # Select the first matching dragon
    burt = ComplexDragon.one()
    assert burt.name == 'Burt'

    # Sort the results so we select the last matching dragon
    albert = ComplexDragon.one(sort=[('_id', DESC)])
    assert albert.name == 'Albert'

    # Select the first dragon who's a fire-drake
    fred = ComplexDragon.one(Q.breed == 'Fire-drake')
    assert fred.name == 'Fred'

    # Select a dragon with a different projection
    burt = ComplexDragon.one(projection={'name': True})
    assert burt.name == 'Burt'
    assert burt.breed == None

def test_many(mongo_client, example_dataset_many):
    """Should return all documents that match the given query"""

    # Select all dragons
    dragons = ComplexDragon.many()

    assert len(dragons) == 3
    assert dragons[0].name == 'Burt'
    assert dragons[1].name == 'Fred'
    assert dragons[2].name == 'Albert'

    # Select all dragons ordered by date of birth (youngest to oldest)
    dragons = ComplexDragon.many(sort=[('dob', DESC)])

    assert dragons[0].name == 'Albert'
    assert dragons[1].name == 'Fred'
    assert dragons[2].name == 'Burt'

    # Select only dragons born after 1980 ordered by date of birth (youngest to
    # oldest).
    dragons = ComplexDragon.many(
        Q.dob > datetime(1980, 1, 1),
        sort=[('dob', DESC)]
        )

    assert len(dragons) == 2
    assert dragons[0].name == 'Albert'
    assert dragons[1].name == 'Fred'

    # Select all dragons with a different projection
    dragons = ComplexDragon.many(projection={'name': True})

    assert dragons[0].name == 'Burt'
    assert dragons[0].breed == None
    assert dragons[1].name == 'Fred'
    assert dragons[1].breed == None
    assert dragons[2].name == 'Albert'
    assert dragons[2].breed == None

def test_projection(mongo_client, example_dataset_one):
    """Should allow references and subframes to be projected"""

    # Select our complex dragon called burt
    burt = ComplexDragon.one(Q.name == 'Burt')
    inventory = Inventory(
        gold=1000,
        skulls=100
        )

    # Test list of references
    burt.misc = Lair.many()
    burt.update()
    burt = ComplexDragon.one(
        Q.name == 'Burt',
        projection={'misc': {'$ref': Lair}}
        )

    assert len(burt.misc) == 1
    assert burt.misc[0].name == 'Cave'

    # Test dictionary of references
    burt.misc = {'cave': Lair.one()}
    burt.update()
    burt = ComplexDragon.one(
        Q.name == 'Burt',
        projection={'misc': {'$ref': Lair}}
        )

    assert len(burt.misc.keys()) == 1
    assert burt.misc['cave'].name == 'Cave'

    # Test list of sub-frames
    burt.misc = [inventory]
    burt.update()
    burt = ComplexDragon.one(
        Q.name == 'Burt',
        projection={'misc': {'$sub': Inventory}}
        )

    assert len(burt.misc) == 1
    assert burt.misc[0].skulls == 100

    # Test dict of sub-frames
    burt.misc = {'spare': inventory}
    burt.update()
    burt = ComplexDragon.one(
        Q.name == 'Burt',
        projection={'misc': {'$sub.': Inventory}}
        )

    assert len(burt.misc.keys()) == 1
    assert burt.misc['spare'].skulls == 100


def test_timestamp_insert(mongo_client):
    """
    Should assign a timestamp to the `created` and `modified` field for a
    document.
    """

    # Assign a the timestamp helper to the insert event
    MonitoredDragon.listen('insert', MonitoredDragon.timestamp_insert)

    # Insert a monitored dragon in the database
    dragon = MonitoredDragon(name='Burt', breed='Cold-drake')
    now = datetime.now()
    now_tz = datetime.now(timezone.utc)
    dragon.insert()

    # Check the dragon has a created/modified timestamp set
    assert (dragon.created - now_tz) < timedelta(seconds=1)
    assert (dragon.modified - now_tz) < timedelta(seconds=1)

    # When the timestamps are reloaded whether they have associated timezones
    # will depend on the mongodb client settings, in the tests the client is not
    # timezone aware and so tests after the reload are against a naive datetime.
    dragon.reload()

    assert (dragon.created - now) < timedelta(seconds=1)
    assert (dragon.modified - now) < timedelta(seconds=1)

def test_timestamp_update(mongo_client):
    """@@ Should assign a timestamp to the `modified` field for a document"""

    # Assign a the timestamp helper to the insert event
    MonitoredDragon.listen('insert', MonitoredDragon.timestamp_insert)
    MonitoredDragon.listen('update', MonitoredDragon.timestamp_update)

    # Insert a monitored dragon in the database
    dragon = MonitoredDragon(name='Burt', breed='Cold-drake')
    now = datetime.now()
    now_tz = datetime.now(timezone.utc)
    dragon.insert()

    # Check the dragon has a modified timestamp set
    assert (dragon.modified - now_tz) < timedelta(seconds=1)

    # When the timestamps are reloaded whether they have associated timezones
    # will depend on the mongodb client settings, in the tests the client is not
    # timezone aware and so tests after the reload are against a naive datetime.
    dragon.reload()

    assert (dragon.modified - now) < timedelta(seconds=1)

    # Wait a couple of seconds and then update the dragon
    sleep(2)
    now = datetime.now()
    now_tz = datetime.now(timezone.utc)
    dragon.breed = 'Fire-drake'
    dragon.update('breed', 'modified')

    # Check a new modified date has been set
    assert (dragon.modified - now_tz) < timedelta(seconds=1)
    dragon.reload()
    assert (dragon.modified - now) < timedelta(seconds=1)

def test_cascade(mongo_client, example_dataset_many):
    """Should apply a cascading delete"""

    # Listen for delete events against dragons and delete any associated lair at
    # the same time.
    def on_delete(sender, frames):
        ComplexDragon.cascade(Lair, 'lair', frames)

    ComplexDragon.listen('deleted', on_delete)

    # Delete a dragon and check the associated lair is also deleted
    burt = ComplexDragon.one(Q.name == 'Burt')
    burt.delete()
    lair = Lair.by_id(burt.lair._id)
    assert lair == None

def test_nullify(mongo_client, example_dataset_many):
    """Should nullify a reference field"""

    # Listen for delete events against lairs and nullify the lair field against
    # associated dragons
    def on_delete(sender, frames):
        Lair.nullify(ComplexDragon, 'lair', frames)

    ComplexDragon.listen('deleted', on_delete)

    # Delete a lair and check the associated field against the dragon has been
    # nullified.
    lair = Lair.one(Q.name == 'Cave')
    lair.delete()
    burt = ComplexDragon.one(Q.name == 'Burt')
    assert burt.lair == None

def test_pull(mongo_client, example_dataset_many):
    """Should pull references from a list field"""

    # Listen for delete events against lairs and pull any deleted lair from the
    # associated dragons. For the sake of the tests here we're storing multiple
    # lairs against the lair attribute instead of the intended one.
    def on_delete(sender, frames):
        Lair.pull(ComplexDragon, 'lair', frames)

    ComplexDragon.listen('deleted', on_delete)

    # List Burt stay in a few lairs
    castle = Lair.one(Q.name == 'Castle')
    burt = ComplexDragon.one(Q.name == 'Burt')
    burt.lair = [burt.lair, castle]
    burt.update()
    burt.reload()

    # Delete a lair and check the associated field against the dragon has been
    # nullified.
    lair = Lair.one(Q.name == 'Cave')
    lair.delete()
    burt.reload()
    assert burt.lair == [castle]

def test_listen(mongo_client):
    """Should add a callback for a signal against the class"""

    # Create a mocked functions for every event that can be triggered for a
    # frame.
    mock = Mock()

    def on_insert(sender, frames):
        mock.insert(sender, frames)

    def on_inserted(sender, frames):
        mock.inserted(sender, frames)

    def on_update(sender, frames):
        mock.update(sender, frames)

    def on_updated(sender, frames):
        mock.updated(sender, frames)

    def on_delete(sender, frames):
        mock.delete(sender, frames)

    def on_deleted(sender, frames):
        mock.deleted(sender, frames)

    # Listen for all events triggered by frames
    Dragon.listen('insert', on_insert)
    Dragon.listen('inserted', on_inserted)
    Dragon.listen('update', on_update)
    Dragon.listen('updated', on_updated)
    Dragon.listen('delete', on_delete)
    Dragon.listen('deleted', on_deleted)

    # Trigger all the events
    burt = Dragon(name='Burt', breed='Cold-drake')
    burt.insert()
    burt.breed = 'Fire-drake'
    burt.update()
    burt.delete()

    # Check each function was called
    assert mock.insert.called
    assert mock.inserted.called
    assert mock.update.called
    assert mock.updated.called
    assert mock.delete.called
    assert mock.deleted.called

def test_stop_listening(mongo_client):
    """Should remove a callback for a signal against the class"""

    # Add an listener for the insert event
    mock = Mock()

    def on_insert(sender, frames):
        mock.insert(sender, frames)

    Dragon.listen('on_insert', on_insert)

    # Remove the listener for the insert event
    Dragon.stop_listening('on_insert', on_insert)

    # Insert a dragon into the database and check that the insert event handler
    # isn't called.
    burt = Dragon(name='Burt', breed='Cold-drake')
    burt.insert()

    assert mock.insert.called == False

def test_get_collection(mongo_client):
    """Return a reference to the database collection for the class"""
    assert Dragon.get_collection() == mongo_client['mongoframes_test']['Dragon']

def test_get_db(mongo_client):
    """Return the database for the collection"""
    assert Dragon.get_db() == mongo_client['mongoframes_test']