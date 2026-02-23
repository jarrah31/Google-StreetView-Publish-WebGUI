"""
Tests for database.py operations:
  - init_db()
  - insert_or_update_photo()
  - get_photo_from_db()
  - get_all_photos_from_db()
  - get_connections_by_photo_ids()
  - clean_deleted_photos()
  - get_db_stats()
  - get_nearby_photos()
"""
import pytest
from unittest.mock import patch

import database as db_module
from tests.conftest import make_photo_data


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_creates_photos_table(self, tmp_db):
        import sqlite3
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='photos'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_places_table(self, tmp_db):
        import sqlite3
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='places'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_connections_table(self, tmp_db):
        import sqlite3
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='connections'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_indexes(self, tmp_db):
        import sqlite3
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert 'idx_photos_lat_lng' in index_names
        assert 'idx_photos_upload_time' in index_names
        assert 'idx_photos_maps_publish_status' in index_names
        assert 'idx_places_photo_id' in index_names
        assert 'idx_connections_source' in index_names
        assert 'idx_connections_target' in index_names

    def test_idempotent(self, tmp_db):
        """Calling init_db() twice must not raise"""
        result = db_module.init_db()
        assert result is True


# ---------------------------------------------------------------------------
# insert_or_update_photo
# ---------------------------------------------------------------------------

class TestInsertOrUpdatePhoto:
    def test_insert_valid_photo_returns_true(self, tmp_db):
        photo = make_photo_data()
        result = db_module.insert_or_update_photo(photo)
        assert result is True

    def test_inserted_photo_can_be_retrieved(self, tmp_db):
        photo = make_photo_data('photo-abc')
        db_module.insert_or_update_photo(photo)
        retrieved = db_module.get_photo_from_db('photo-abc')
        assert retrieved is not None
        assert retrieved['photo_id'] == 'photo-abc'

    def test_update_existing_photo(self, tmp_db):
        photo = make_photo_data('photo-001', viewCount=10)
        db_module.insert_or_update_photo(photo)

        updated = make_photo_data('photo-001', viewCount=99)
        db_module.insert_or_update_photo(updated)

        retrieved = db_module.get_photo_from_db('photo-001')
        assert retrieved['view_count'] == 99

    def test_stores_coordinates(self, tmp_db):
        photo = make_photo_data('photo-coords')
        db_module.insert_or_update_photo(photo)
        retrieved = db_module.get_photo_from_db('photo-coords')
        assert retrieved['latitude'] == pytest.approx(51.5074)
        assert retrieved['longitude'] == pytest.approx(-0.1278)

    def test_stores_heading(self, tmp_db):
        photo = make_photo_data('photo-heading')
        db_module.insert_or_update_photo(photo)
        retrieved = db_module.get_photo_from_db('photo-heading')
        assert retrieved['heading'] == pytest.approx(180.0)

    def test_stores_places(self, tmp_db):
        photo = make_photo_data('photo-places')
        db_module.insert_or_update_photo(photo)
        retrieved = db_module.get_photo_from_db('photo-places')
        assert 'places' in retrieved
        assert len(retrieved['places']) == 1
        assert retrieved['places'][0]['name'] == 'London'

    def test_stores_connections_when_target_exists(self, tmp_db):
        """Connection is only stored when target photo exists in the DB first."""
        # Insert the target photo first
        target = make_photo_data('target-001')
        db_module.insert_or_update_photo(target)

        # Now insert source photo with a connection to the target
        source = make_photo_data(
            'source-001',
            connections=[{'target': {'id': 'target-001'}}]
        )
        db_module.insert_or_update_photo(source)

        retrieved = db_module.get_photo_from_db('source-001')
        assert 'connections' in retrieved
        assert any(c['target']['id'] == 'target-001' for c in retrieved['connections'])

    def test_missing_photo_id_returns_false(self, tmp_db):
        result = db_module.insert_or_update_photo({})
        assert result is False

    def test_none_returns_false(self, tmp_db):
        result = db_module.insert_or_update_photo(None)
        assert result is False

    def test_nan_heading_stored_as_none(self, tmp_db):
        photo = make_photo_data('photo-nan-heading')
        photo['pose']['heading'] = 'NaN'
        db_module.insert_or_update_photo(photo)
        retrieved = db_module.get_photo_from_db('photo-nan-heading')
        assert retrieved['heading'] is None

    def test_places_replaced_on_update(self, tmp_db):
        """Re-inserting a photo should replace its places, not accumulate them."""
        photo = make_photo_data('photo-places-update')
        db_module.insert_or_update_photo(photo)

        # Update with different places
        updated = make_photo_data(
            'photo-places-update',
            places=[
                {'placeId': 'new-place-id', 'name': 'Paris', 'languageCode': 'fr'}
            ]
        )
        db_module.insert_or_update_photo(updated)

        retrieved = db_module.get_photo_from_db('photo-places-update')
        assert len(retrieved['places']) == 1
        assert retrieved['places'][0]['name'] == 'Paris'

    def test_string_view_count_with_commas(self, tmp_db):
        photo = make_photo_data('photo-views')
        photo['viewCount'] = '1,234'
        db_module.insert_or_update_photo(photo)
        retrieved = db_module.get_photo_from_db('photo-views')
        assert retrieved['view_count'] == 1234


# ---------------------------------------------------------------------------
# get_photo_from_db
# ---------------------------------------------------------------------------

class TestGetPhotoFromDb:
    def test_returns_none_for_missing_photo(self, tmp_db):
        result = db_module.get_photo_from_db('nonexistent-id')
        assert result is None

    def test_returns_dict_for_existing_photo(self, tmp_db):
        photo = make_photo_data('photo-get-test')
        db_module.insert_or_update_photo(photo)
        result = db_module.get_photo_from_db('photo-get-test')
        assert isinstance(result, dict)

    def test_photo_without_places_has_no_places_key(self, tmp_db):
        photo = make_photo_data('photo-no-places', places=[])
        db_module.insert_or_update_photo(photo)
        result = db_module.get_photo_from_db('photo-no-places')
        # places key absent or empty when no places
        assert result.get('places', []) == []

    def test_share_link_stored_correctly(self, tmp_db):
        photo = make_photo_data('photo-share')
        db_module.insert_or_update_photo(photo)
        result = db_module.get_photo_from_db('photo-share')
        assert 'photo-share' in result['share_link']

    def test_maps_publish_status_stored(self, tmp_db):
        photo = make_photo_data('photo-status')
        db_module.insert_or_update_photo(photo)
        result = db_module.get_photo_from_db('photo-status')
        assert result['maps_publish_status'] == 'PUBLISHED'


# ---------------------------------------------------------------------------
# get_all_photos_from_db
# ---------------------------------------------------------------------------

class TestGetAllPhotosFromDb:
    def test_empty_db_returns_empty_list(self, tmp_db):
        result = db_module.get_all_photos_from_db()
        assert result == []

    def test_returns_all_inserted_photos(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('p1'))
        db_module.insert_or_update_photo(make_photo_data('p2'))
        db_module.insert_or_update_photo(make_photo_data('p3'))
        result = db_module.get_all_photos_from_db()
        assert len(result) == 3

    def test_each_photo_has_photo_id(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('p-check'))
        result = db_module.get_all_photos_from_db()
        assert all('photo_id' in p for p in result)

    def test_places_included_in_bulk_result(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('p-places'))
        result = db_module.get_all_photos_from_db()
        photo = next(p for p in result if p['photo_id'] == 'p-places')
        assert 'places' in photo
        assert len(photo['places']) == 1

    def test_connections_included_in_bulk_result(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('target-bulk'))
        source = make_photo_data(
            'source-bulk',
            connections=[{'target': {'id': 'target-bulk'}}]
        )
        db_module.insert_or_update_photo(source)
        result = db_module.get_all_photos_from_db()
        photo = next(p for p in result if p['photo_id'] == 'source-bulk')
        assert 'connections' in photo

    def test_returns_list(self, tmp_db):
        assert isinstance(db_module.get_all_photos_from_db(), list)


# ---------------------------------------------------------------------------
# get_connections_by_photo_ids
# ---------------------------------------------------------------------------

class TestGetConnectionsByPhotoIds:
    def test_empty_list_returns_empty(self, tmp_db):
        result = db_module.get_connections_by_photo_ids([])
        assert result == []

    def test_no_connections_returns_empty(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('solo'))
        result = db_module.get_connections_by_photo_ids(['solo'])
        assert result == []

    def test_returns_connection_for_source(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('conn-target'))
        source = make_photo_data(
            'conn-source',
            connections=[{'target': {'id': 'conn-target'}}]
        )
        db_module.insert_or_update_photo(source)

        result = db_module.get_connections_by_photo_ids(['conn-source'])
        assert len(result) == 1
        assert result[0]['source'] == 'conn-source'
        assert result[0]['target'] == 'conn-target'

    def test_multiple_sources_bulk(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('tgt-a'))
        db_module.insert_or_update_photo(make_photo_data('tgt-b'))
        db_module.insert_or_update_photo(make_photo_data(
            'src-a', connections=[{'target': {'id': 'tgt-a'}}]
        ))
        db_module.insert_or_update_photo(make_photo_data(
            'src-b', connections=[{'target': {'id': 'tgt-b'}}]
        ))

        result = db_module.get_connections_by_photo_ids(['src-a', 'src-b'])
        assert len(result) == 2

    def test_result_has_source_and_target_keys(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('key-tgt'))
        db_module.insert_or_update_photo(make_photo_data(
            'key-src', connections=[{'target': {'id': 'key-tgt'}}]
        ))
        result = db_module.get_connections_by_photo_ids(['key-src'])
        assert 'source' in result[0]
        assert 'target' in result[0]


# ---------------------------------------------------------------------------
# clean_deleted_photos
# ---------------------------------------------------------------------------

class TestCleanDeletedPhotos:
    def test_no_photos_to_delete_returns_zero(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('keep-me'))
        result = db_module.clean_deleted_photos(['keep-me'])
        assert result == 0

    def test_removes_deleted_photo(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('gone'))
        db_module.insert_or_update_photo(make_photo_data('stays'))
        result = db_module.clean_deleted_photos(['stays'])
        assert result == 1
        assert db_module.get_photo_from_db('gone') is None

    def test_keeps_all_when_all_present(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('a'))
        db_module.insert_or_update_photo(make_photo_data('b'))
        result = db_module.clean_deleted_photos(['a', 'b'])
        assert result == 0

    def test_empty_existing_ids_removes_all(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('x'))
        db_module.insert_or_update_photo(make_photo_data('y'))
        result = db_module.clean_deleted_photos([])
        assert result == 2

    def test_cleans_associated_places(self, tmp_db):
        import sqlite3
        db_module.insert_or_update_photo(make_photo_data('with-place'))
        db_module.clean_deleted_photos([])

        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM places WHERE photo_id = ?", ('with-place',))
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0

    def test_cleans_associated_connections(self, tmp_db):
        import sqlite3
        db_module.insert_or_update_photo(make_photo_data('tgt-clean'))
        db_module.insert_or_update_photo(make_photo_data(
            'src-clean', connections=[{'target': {'id': 'tgt-clean'}}]
        ))
        db_module.clean_deleted_photos([])

        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM connections")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0


# ---------------------------------------------------------------------------
# get_db_stats
# ---------------------------------------------------------------------------

class TestGetDbStats:
    def test_empty_db_stats(self, tmp_db):
        stats = db_module.get_db_stats()
        assert stats['photo_count'] == 0
        assert stats['place_count'] == 0
        assert stats['connection_count'] == 0
        assert stats['total_views'] == 0
        assert stats['last_updated'] == 'N/A'

    def test_counts_photos(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('s1'))
        db_module.insert_or_update_photo(make_photo_data('s2'))
        stats = db_module.get_db_stats()
        assert stats['photo_count'] == 2

    def test_counts_places(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('sp1'))
        stats = db_module.get_db_stats()
        assert stats['place_count'] == 1

    def test_counts_connections(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('ct'))
        db_module.insert_or_update_photo(make_photo_data(
            'cs', connections=[{'target': {'id': 'ct'}}]
        ))
        stats = db_module.get_db_stats()
        assert stats['connection_count'] == 1

    def test_sums_view_count(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('v1', viewCount=10))
        db_module.insert_or_update_photo(make_photo_data('v2', viewCount=32))
        stats = db_module.get_db_stats()
        assert stats['total_views'] == 42

    def test_last_updated_not_na_when_photos_exist(self, tmp_db):
        db_module.insert_or_update_photo(make_photo_data('lu1'))
        stats = db_module.get_db_stats()
        assert stats['last_updated'] != 'N/A'

    def test_returns_dict(self, tmp_db):
        assert isinstance(db_module.get_db_stats(), dict)


# ---------------------------------------------------------------------------
# get_nearby_photos
# ---------------------------------------------------------------------------

class TestGetNearbyPhotos:
    def _insert_photo_at(self, photo_id, lat, lng, tmp_db):
        photo = make_photo_data(photo_id)
        photo['pose']['latLngPair'] = {'latitude': lat, 'longitude': lng}
        db_module.insert_or_update_photo(photo)

    def test_returns_photos_in_bounding_box(self, tmp_db):
        self._insert_photo_at('nearby-1', 51.5, -0.1, tmp_db)
        result = db_module.get_nearby_photos(
            51.5, -0.1,
            min_lat=51.4, max_lat=51.6,
            min_lng=-0.2, max_lng=0.0
        )
        assert len(result) == 1
        assert result[0]['photoId']['id'] == 'nearby-1'

    def test_excludes_photos_outside_bounding_box(self, tmp_db):
        self._insert_photo_at('far-away', 48.8, 2.3, tmp_db)
        result = db_module.get_nearby_photos(
            51.5, -0.1,
            min_lat=51.4, max_lat=51.6,
            min_lng=-0.2, max_lng=0.0
        )
        assert result == []

    def test_excludes_center_photo_when_specified(self, tmp_db):
        self._insert_photo_at('center', 51.5, -0.1, tmp_db)
        self._insert_photo_at('neighbor', 51.501, -0.101, tmp_db)
        result = db_module.get_nearby_photos(
            51.5, -0.1,
            min_lat=51.4, max_lat=51.6,
            min_lng=-0.2, max_lng=0.0,
            center_photo_id='center'
        )
        ids = [p['photoId']['id'] for p in result]
        assert 'center' not in ids
        assert 'neighbor' in ids

    def test_includes_center_photo_when_no_id_given(self, tmp_db):
        self._insert_photo_at('center-inc', 51.5, -0.1, tmp_db)
        result = db_module.get_nearby_photos(
            51.5, -0.1,
            min_lat=51.4, max_lat=51.6,
            min_lng=-0.2, max_lng=0.0
        )
        ids = [p['photoId']['id'] for p in result]
        assert 'center-inc' in ids

    def test_result_format(self, tmp_db):
        self._insert_photo_at('fmt-photo', 51.5, -0.1, tmp_db)
        result = db_module.get_nearby_photos(
            51.5, -0.1,
            min_lat=51.4, max_lat=51.6,
            min_lng=-0.2, max_lng=0.0
        )
        assert len(result) == 1
        photo = result[0]
        assert 'photoId' in photo
        assert 'pose' in photo
        assert 'latLngPair' in photo['pose']

    def test_empty_db_returns_empty_list(self, tmp_db):
        result = db_module.get_nearby_photos(
            51.5, -0.1,
            min_lat=51.4, max_lat=51.6,
            min_lng=-0.2, max_lng=0.0
        )
        assert result == []
