import os
import sqlite3
import json
import logging
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

# Get the base directory of the application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database constants
DATABASE_PATH = os.path.join(BASE_DIR, 'userdata', 'data', 'streetview_photos.db')
logger.info(f"Database - Database path set to: {DATABASE_PATH}")

def ensure_db_directory():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Database - Created database directory: {db_dir}")

def init_db():
    """Initialize the SQLite database with necessary tables"""
    ensure_db_directory()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Create photos table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS photos (
        photo_id TEXT PRIMARY KEY,
        latitude REAL,
        longitude REAL,
        heading REAL,
        altitude REAL,
        pitch REAL,
        roll REAL,
        capture_time TEXT,
        upload_time TEXT,
        view_count INTEGER,
        maps_publish_status TEXT,
        share_link TEXT,
        thumbnail_url TEXT,
        updated_at TEXT
    )
    ''')
    
    # Create places table (one photo can have multiple places)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        photo_id TEXT,
        place_id TEXT,
        name TEXT,
        language_code TEXT,
        FOREIGN KEY (photo_id) REFERENCES photos (photo_id),
        UNIQUE (photo_id, place_id)
    )
    ''')
    
    # Create connections table (many-to-many relationship)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_photo_id TEXT,
        target_photo_id TEXT,
        FOREIGN KEY (source_photo_id) REFERENCES photos (photo_id),
        FOREIGN KEY (target_photo_id) REFERENCES photos (photo_id),
        UNIQUE (source_photo_id, target_photo_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info("Database - Database initialized successfully")
    return True

def insert_or_update_photo(photo_data):
    """Insert or update a photo record in the database"""
    logger.debug(f"=== FUNCTION DB: insert_or_update_photo ===")
    if not photo_data or 'photoId' not in photo_data or 'id' not in photo_data['photoId']:
        logger.warning("Database - Invalid photo data: missing photoId")
        return False
    
    photo_id = photo_data['photoId']['id']
    
    # DEBUG: Enhanced logging for database insert/update
    logger.debug("=========================================================")
    logger.debug(f"=== DATABASE DEBUG: Processing photo {photo_id} ===")
    logger.debug(f"Input captureTime: {photo_data.get('captureTime', 'N/A')}")
    logger.debug(f"Input uploadTime: {photo_data.get('uploadTime', 'N/A')}")
    logger.debug(f"Input viewCount: {photo_data.get('viewCount', 'N/A')}")
    logger.debug(f"Complete input data: {photo_data}")
    
    # Extract pose data
    latitude = None
    longitude = None
    heading = None
    altitude = None
    pitch = None
    roll = None
    
    if 'pose' in photo_data:
        pose = photo_data['pose']
        if 'latLngPair' in pose:
            latitude = pose['latLngPair'].get('latitude')
            longitude = pose['latLngPair'].get('longitude')
        
        # Convert NaN string values to None
        heading_val = pose.get('heading')
        if isinstance(heading_val, str) and heading_val.lower() == 'nan':
            heading = None
        else:
            try:
                heading = float(heading_val) if heading_val is not None else None
            except (ValueError, TypeError):
                heading = None
        
        # Handle other pose attributes similarly
        for attr in ['altitude', 'pitch', 'roll']:
            val = pose.get(attr)
            if isinstance(val, str) and val.lower() == 'nan':
                pose[attr] = None
            else:
                try:
                    pose[attr] = float(val) if val is not None else None
                except (ValueError, TypeError):
                    pose[attr] = None
        
        altitude = pose.get('altitude')
        pitch = pose.get('pitch')
        roll = pose.get('roll')
    
    # Extract other data
    capture_time = photo_data.get('captureTime')
    upload_time = photo_data.get('uploadTime')
    view_count = photo_data.get('viewCount')
    if view_count and isinstance(view_count, str):
        view_count = view_count.replace(',', '')  # Remove commas from view count
        try:
            view_count = int(view_count)
        except ValueError:
            view_count = 0
    
    maps_publish_status = photo_data.get('mapsPublishStatus')
    share_link = photo_data.get('shareLink')
    thumbnail_url = photo_data.get('thumbnailUrl')
    updated_at = datetime.now().isoformat()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys = ON')
    
    try:
        # DEBUG: Log final values being written to database
        logger.debug("=========================================================")
        logger.debug(f"=== DATABASE DEBUG: Final values for photo {photo_id} ===")
        logger.debug(f"=Final capture_time: {capture_time}")
        logger.debug(f"=Final upload_time: {upload_time}")
        logger.debug(f"=Final view_count: {view_count}")
        logger.debug(f"=Final maps_publish_status: {maps_publish_status}")
        logger.debug(f"=Final share_link: {share_link}")
        logger.debug(f"=Final thumbnail_url: {thumbnail_url}")
        logger.debug(f"=Final updated_at: {updated_at}")
        logger.debug(f"=Final coordinates: lat={latitude}, lng={longitude}, heading={heading}")
        
        # Insert or update the photo record
        cursor.execute('''
        INSERT OR REPLACE INTO photos (
            photo_id, latitude, longitude, heading, altitude, pitch, roll,
            capture_time, upload_time, view_count, maps_publish_status,
            share_link, thumbnail_url, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            photo_id, latitude, longitude, heading, altitude, pitch, roll,
            capture_time, upload_time, view_count, maps_publish_status,
            share_link, thumbnail_url, updated_at
        ))
        
        # Handle places
        if 'places' in photo_data and photo_data['places']:
            # Delete existing places for this photo
            cursor.execute("DELETE FROM places WHERE photo_id = ?", (photo_id,))
            
            # Insert new places
            for place in photo_data['places']:
                cursor.execute('''
                INSERT INTO places (photo_id, place_id, name, language_code)
                VALUES (?, ?, ?, ?)
                ''', (
                    photo_id,
                    place.get('placeId'),
                    place.get('name'),
                    place.get('languageCode')
                ))
        
        # Handle connections
        if 'connections' in photo_data and photo_data['connections']:
            logger.debug(f"=== DATABASE DEBUG CONNECTIONS: Processing {len(photo_data['connections'])} connections for photo {photo_id} ===")
            # Delete existing connections for this photo
            cursor.execute("DELETE FROM connections WHERE source_photo_id = ?", (photo_id,))
            
            # Insert new connections with validation
            connections_added = 0
            connections_skipped = 0
            for connection in photo_data['connections']:
                if 'target' in connection and 'id' in connection['target']:
                    target_id = connection['target']['id']
                    logger.debug(f"=== DATABASE DEBUG CONNECTIONS: Adding connection {photo_id} -> {target_id} ===")
                    
                    # First check if target photo exists
                    cursor.execute("SELECT 1 FROM photos WHERE photo_id = ?", (target_id,))
                    target_exists = cursor.fetchone()
                    
                    if target_exists:
                        try:
                            cursor.execute('''
                            INSERT OR IGNORE INTO connections (source_photo_id, target_photo_id)
                            VALUES (?, ?)
                            ''', (photo_id, target_id))
                            connections_added += 1
                            logger.debug(f"=== DATABASE DEBUG CONNECTIONS: Successfully added connection {photo_id} -> {target_id} ===")
                        except sqlite3.IntegrityError as e:
                            logger.warning(f"=== DATABASE DEBUG CONNECTIONS: Failed to add connection {photo_id} -> {target_id}: {e} ===")
                            connections_skipped += 1
                    else:
                        logger.warning(f"=== DATABASE DEBUG CONNECTIONS: Skipping connection {photo_id} -> {target_id} - target photo not found in database ===")
                        connections_skipped += 1
            
            logger.debug(f"=== DATABASE DEBUG CONNECTIONS: Added {connections_added} connections, skipped {connections_skipped} for photo {photo_id} ===")
        else:
            logger.debug(f"=== DATABASE DEBUG CONNECTIONS: No connections to process for photo {photo_id} ===")
        
        conn.commit()
        return True
    
    except Exception as e:
        logger.error(f"Database - Error inserting/updating photo {photo_id}: {str(e)}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

def get_photo_from_db(photo_id):
    """Retrieve a photo from the database by its ID"""
    logger.debug(f"=== FUNCTION DB: get_photo_from_db ===")
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys = ON')
    
    try:
        # Get photo data
        cursor.execute("SELECT * FROM photos WHERE photo_id = ?", (photo_id,))
        photo_row = cursor.fetchone()
        
        if not photo_row:
            logger.debug(f"=== DATABASE DEBUG: Photo {photo_id} not found in database ===")
            return None
        
        photo_data = dict(photo_row)
        
        # Get places data
        cursor.execute("SELECT place_id, name, language_code FROM places WHERE photo_id = ?", (photo_id,))
        places_rows = cursor.fetchall()
        
        if places_rows:
            photo_data['places'] = [dict(row) for row in places_rows]
        
        # Get connections data
        cursor.execute("SELECT target_photo_id FROM connections WHERE source_photo_id = ?", (photo_id,))
        conn_rows = cursor.fetchall()
        
        if conn_rows:
            photo_data['connections'] = [{'target': {'id': row['target_photo_id']}} for row in conn_rows]
        
        # DEBUG: Log retrieved photo data from database
        logger.debug("==================================================================")
        logger.debug(f"=== DATABASE DEBUG: Final photo data being returned for {photo_id} ===")
        logger.debug(f"=Returned capture_time: {photo_data.get('capture_time', 'N/A')}")
        logger.debug(f"=Returned upload_time: {photo_data.get('upload_time', 'N/A')}")
        logger.debug(f"=Returned view_count: {photo_data.get('view_count', 'N/A')}")
        logger.debug(f"=Raw database maps_publish_status: {photo_data.get('maps_publish_status', 'N/A')}")
        logger.debug(f"=Raw database share_link: {photo_data.get('share_link', 'N/A')}")
        logger.debug(f"=Raw database thumbnail_url: {photo_data.get('thumbnail_url', 'N/A')}")
        logger.debug(f"=Raw database coordinates: lat={photo_data.get('latitude', 'N/A')}, lng={photo_data.get('longitude', 'N/A')}, heading={photo_data.get('heading', 'N/A')}")
        logger.debug(f"=Returned places count: {len(photo_data.get('places', []))}")
        logger.debug(f"=Returned connections count: {len(photo_data.get('connections', []))}")
        logger.debug(f"=Complete returned photo data: {photo_data}")
        
        return photo_data
    
    except Exception as e:
        logger.error(f"Database - Error retrieving photo {photo_id}: {str(e)}")
        return None
    
    finally:
        conn.close()

def get_all_photos_from_db():
    """Retrieve all photos from the database"""
    logger.debug(f"=== FUNCTION DB: get_all_photos_from_db ===")
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys = ON')
    
    try:
        # Get all photo IDs
        cursor.execute("SELECT photo_id FROM photos")
        photo_ids = [row['photo_id'] for row in cursor.fetchall()]
        
        # DEBUG: Log photo retrieval process
        logger.debug(f"=== DATABASE DEBUG: Retrieving all photos from database ===")
        logger.debug(f"Found {len(photo_ids)} photo IDs in database: {photo_ids}")
        
        # Retrieve complete photo data for each ID
        photos = []
        for photo_id in photo_ids:
            photo_data = get_photo_from_db(photo_id)
            if photo_data:
                photos.append(photo_data)
        
        # DEBUG: Log summary of retrieved photos
        logger.debug(f"=== DATABASE DEBUG: Retrieved {len(photos)} complete photo records ===")
        for i, photo in enumerate(photos):
            logger.debug(f"Photo {i+1}: ID={photo.get('photo_id', 'N/A')}, capture_time={photo.get('capture_time', 'N/A')}, upload_time={photo.get('upload_time', 'N/A')}")
        
        return photos
    
    except Exception as e:
        logger.error(f"Database - Error retrieving all photos: {str(e)}")
        return []
    
    finally:
        conn.close()

def import_photos_from_json(json_file):
    """Import photos from a JSON file into the database"""
    logger.debug(f"=== FUNCTION DB: import_photos_from_json ===")
    try:
        with open(json_file, 'r') as f:
            photos = json.load(f)
        
        if not isinstance(photos, list):
            logger.error(f"Database - Invalid JSON format in {json_file}. Expected a list of photos.")
            return False
        
        success_count = 0
        total_count = len(photos)
        
        for photo in photos:
            if insert_or_update_photo(photo):
                success_count += 1
        
        logger.info(f"Database - Imported {success_count}/{total_count} photos from {json_file}")
        return True
    
    except Exception as e:
        logger.error(f"Database - Error importing photos from {json_file}: {str(e)}")
        return False

def get_db_stats():
    """Get statistics about the database"""
    logger.debug(f"=== FUNCTION DB: get_db_stats ===")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys = ON')
    
    try:
        stats = {}
        
        # Count photos
        cursor.execute("SELECT COUNT(*) FROM photos")
        stats['photo_count'] = cursor.fetchone()[0]
        
        # Count places
        cursor.execute("SELECT COUNT(*) FROM places")
        stats['place_count'] = cursor.fetchone()[0]
        
        # Count connections
        cursor.execute("SELECT COUNT(*) FROM connections")
        stats['connection_count'] = cursor.fetchone()[0]
        
        # Sum total view count
        cursor.execute("SELECT SUM(view_count) FROM photos WHERE view_count IS NOT NULL")
        total_views = cursor.fetchone()[0]
        stats['total_views'] = total_views if total_views is not None else 0
        
        # Get last updated
        cursor.execute("SELECT MAX(updated_at) FROM photos")
        last_updated = cursor.fetchone()[0]
        
        # Format the timestamp in YYYY-MM-DD HH:MM format
        if last_updated:
            try:
                # Convert ISO format string to datetime object
                dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                # Format in YYYY-MM-DD HH:MM format
                stats['last_updated'] = dt.strftime('%Y-%m-%d %H:%M')
            except (ValueError, AttributeError):
                # In case of any error in parsing, use the raw value
                stats['last_updated'] = last_updated
        else:
            stats['last_updated'] = "N/A"
        
        return stats
    
    except Exception as e:
        logger.error(f"Database - Error getting database stats: {str(e)}")
        return {'error': str(e)}
    
    finally:
        conn.close()

def clean_deleted_photos(existing_photo_ids):
    """
    Remove photos from the database that are no longer in the API.
    
    Args:
        existing_photo_ids: A list of photo IDs that currently exist in the API
        
    Returns:
        Number of photos removed from the database
    """
    logger.debug(f"=== FUNCTION DB: clean_deleted_photos ===")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # First, get all photo IDs currently in the database
        cursor.execute("SELECT photo_id FROM photos")
        db_photo_ids = set(row[0] for row in cursor.fetchall())
        
        # Find photo IDs that are in the database but not in the API response
        deleted_ids = db_photo_ids - set(existing_photo_ids)
        
        if not deleted_ids:
            logger.info("Database - No deleted photos found to clean up")
            return 0
            
        # Log the IDs to be deleted
        logger.info(f"Database - Found {len(deleted_ids)} photos to remove from database: {deleted_ids}")
        
        # Delete all related records for the deleted photos
        for deleted_id in deleted_ids:
            # Delete from places table
            cursor.execute("DELETE FROM places WHERE photo_id = ?", (deleted_id,))
            
            # Delete from connections table (both source and target)
            cursor.execute("DELETE FROM connections WHERE source_photo_id = ? OR target_photo_id = ?", 
                           (deleted_id, deleted_id))
            
            # Delete from photos table
            cursor.execute("DELETE FROM photos WHERE photo_id = ?", (deleted_id,))
        
        conn.commit()
        logger.info(f"Database - Successfully removed {len(deleted_ids)} deleted photos from database")
        return len(deleted_ids)
        
    except Exception as e:
        logger.error(f"Database - Error cleaning deleted photos: {str(e)}")
        conn.rollback()
        return 0
        
    finally:
        conn.close()

def get_connections_by_photo_ids(photo_ids):
    """
    Fetch all connections for a list of photo IDs from the database
    
    Args:
        photo_ids: A list of photo IDs to fetch connections for
        
    Returns:
        A list of dictionaries with source and target photo IDs
    """
    logger.debug(f"=== FUNCTION DB: get_connections_by_photo_ids ===")
    if not photo_ids:
        return []
        
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute('PRAGMA foreign_keys = ON')
        
        all_connections = []
        
        # For each photo ID, fetch its connections
        for photo_id in photo_ids:
            logger.debug(f"Database - Fetching connections for photo_id {photo_id} from database")
            
            # Query the connections table
            cursor.execute(
                "SELECT source_photo_id, target_photo_id FROM connections WHERE source_photo_id = ?",
                (photo_id,)
            )
            
            # Process the results
            connections = cursor.fetchall()
            for conn_row in connections:
                all_connections.append({
                    'source': conn_row['source_photo_id'],
                    'target': conn_row['target_photo_id']
                })
            
            logger.debug(f"Database - Found {len(connections)} database connections for photo_id {photo_id}")
            
        return all_connections
    
    except Exception as e:
        logger.error(f"Database - Error fetching connections from database: {str(e)}")
        return []
        
    finally:
        if conn:
            conn.close()

def get_nearby_photos(lat, lng, min_lat, max_lat, min_lng, max_lng):
    """
    Get photos that are within a specified bounding box
    
    Args:
        lat: Center latitude
        lng: Center longitude
        min_lat: Minimum latitude of bounding box
        max_lat: Maximum latitude of bounding box
        min_lng: Minimum longitude of bounding box
        max_lng: Maximum longitude of bounding box
        
    Returns:
        List of photo objects within the bounding box
    """
    logger.debug(f"=== FUNCTION DB: get_nearby_photos ===")
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Query for photos within the bounding box
        cursor.execute("""
            SELECT * FROM photos 
            WHERE latitude >= ? AND latitude <= ? 
            AND longitude >= ? AND longitude <= ?
            AND photo_id IS NOT NULL
        """, (min_lat, max_lat, min_lng, max_lng))
        
        photos = []
        center_photo_id = None
        
        # Process results
        for row in cursor.fetchall():
            photo_data = dict(row)
            photo_id = photo_data['photo_id']
            
            # Skip if no coordinates
            if photo_data['latitude'] is None or photo_data['longitude'] is None:
                continue
                
            # Format data to match API response format
            formatted_photo = {
                'photoId': {'id': photo_id},
                'pose': {
                    'latLngPair': {
                        'latitude': photo_data['latitude'],
                        'longitude': photo_data['longitude']
                    },
                    'heading': photo_data['heading']
                },
                'captureTime': photo_data['capture_time'],
                'thumbnailUrl': photo_data['thumbnail_url'],
                'viewCount': photo_data['view_count'],
                'shareLink': photo_data['share_link'],
                'uploadTime': photo_data['upload_time']
            }
            
            # Get connections for this photo
            cursor.execute("""
                SELECT target_photo_id FROM connections 
                WHERE source_photo_id = ?
            """, (photo_id,))
            
            connections = []
            for conn_row in cursor.fetchall():
                connections.append({
                    'target': {'id': conn_row['target_photo_id']}
                })
            
            if connections:
                formatted_photo['connections'] = connections
            
            # Get places for this photo
            cursor.execute("""
                SELECT place_id, name, language_code FROM places
                WHERE photo_id = ?
            """, (photo_id,))
            
            places = []
            for place_row in cursor.fetchall():
                places.append({
                    'placeId': place_row['place_id'],
                    'name': place_row['name'],
                    'languageCode': place_row['language_code']
                })
            
            if places:
                formatted_photo['places'] = places
            
            # Check if this is the center photo
            if abs(photo_data['latitude'] - lat) < 0.0000001 and abs(photo_data['longitude'] - lng) < 0.0000001:
                center_photo_id = photo_id
            
            photos.append(formatted_photo)
        
        # Filter out the center photo from the results
        if center_photo_id:
            photos = [p for p in photos if p['photoId']['id'] != center_photo_id]
        
        return photos
        
    except Exception as e:
        logger.error(f"Database - Error getting nearby photos: {str(e)}")
        return []
        
    finally:
        if conn:
            conn.close()


def get_all_photos_with_gps():
    """
    Get all photos from the database that have GPS coordinates
    
    Returns:
        List of photo objects with GPS coordinates formatted for map display
    """
    logger.debug(f"=== FUNCTION DB: get_all_photos_with_gps ===")
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query for photos that have GPS coordinates
        cursor.execute("""
            SELECT p.*, GROUP_CONCAT(DISTINCT pl.name) as place_names
            FROM photos p
            LEFT JOIN places pl ON p.photo_id = pl.photo_id
            WHERE p.latitude IS NOT NULL 
            AND p.longitude IS NOT NULL
            GROUP BY p.photo_id
            ORDER BY p.upload_time DESC
        """)
        
        photos = []
        
        # Process results
        for row in cursor.fetchall():
            photo_data = dict(row)
            
            # Create simplified photo object for map display
            photo = {
                'photo_id': photo_data['photo_id'],
                'latitude': photo_data['latitude'],
                'longitude': photo_data['longitude'],
                'place_names': photo_data['place_names'] or 'Unknown Location',
                'maps_publish_status': photo_data['maps_publish_status'] or 'N/A',
                'view_count': photo_data['view_count'] or 0,
                'capture_time': photo_data['capture_time'],
                'share_link': photo_data['share_link'],
                'thumbnail_url': photo_data['thumbnail_url']
            }
            
            photos.append(photo)
        
        logger.info(f"Database - Retrieved {len(photos)} photos with GPS coordinates for map view")
        return photos
        
    except Exception as e:
        logger.error(f"Database - Error getting photos with GPS coordinates: {str(e)}")
        return []
        
    finally:
        if conn:
            conn.close()
