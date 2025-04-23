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
logger.info(f"Database path set to: {DATABASE_PATH}")

def ensure_db_directory():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")

def init_db():
    """Initialize the SQLite database with necessary tables"""
    ensure_db_directory()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
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
    
    logger.info("Database initialized successfully")
    return True

def insert_or_update_photo(photo_data):
    """Insert or update a photo record in the database"""
    if not photo_data or 'photoId' not in photo_data or 'id' not in photo_data['photoId']:
        logger.warning("Invalid photo data: missing photoId")
        return False
    
    photo_id = photo_data['photoId']['id']
    
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
    
    try:
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
            # Delete existing connections for this photo
            cursor.execute("DELETE FROM connections WHERE source_photo_id = ?", (photo_id,))
            
            # Insert new connections
            for connection in photo_data['connections']:
                if 'target' in connection and 'id' in connection['target']:
                    target_id = connection['target']['id']
                    cursor.execute('''
                    INSERT OR IGNORE INTO connections (source_photo_id, target_photo_id)
                    VALUES (?, ?)
                    ''', (photo_id, target_id))
        
        conn.commit()
        return True
    
    except Exception as e:
        logger.error(f"Error inserting/updating photo {photo_id}: {str(e)}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

def get_photo_from_db(photo_id):
    """Retrieve a photo from the database by its ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()
    
    try:
        # Get photo data
        cursor.execute("SELECT * FROM photos WHERE photo_id = ?", (photo_id,))
        photo_row = cursor.fetchone()
        
        if not photo_row:
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
        
        return photo_data
    
    except Exception as e:
        logger.error(f"Error retrieving photo {photo_id}: {str(e)}")
        return None
    
    finally:
        conn.close()

def get_all_photos_from_db():
    """Retrieve all photos from the database"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get all photo IDs
        cursor.execute("SELECT photo_id FROM photos")
        photo_ids = [row['photo_id'] for row in cursor.fetchall()]
        
        # Retrieve complete photo data for each ID
        photos = []
        for photo_id in photo_ids:
            photo_data = get_photo_from_db(photo_id)
            if photo_data:
                photos.append(photo_data)
        
        return photos
    
    except Exception as e:
        logger.error(f"Error retrieving all photos: {str(e)}")
        return []
    
    finally:
        conn.close()

def import_photos_from_json(json_file):
    """Import photos from a JSON file into the database"""
    try:
        with open(json_file, 'r') as f:
            photos = json.load(f)
        
        if not isinstance(photos, list):
            logger.error(f"Invalid JSON format in {json_file}. Expected a list of photos.")
            return False
        
        success_count = 0
        total_count = len(photos)
        
        for photo in photos:
            if insert_or_update_photo(photo):
                success_count += 1
        
        logger.info(f"Imported {success_count}/{total_count} photos from {json_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error importing photos from {json_file}: {str(e)}")
        return False

def get_db_stats():
    """Get statistics about the database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
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
        logger.error(f"Error getting database stats: {str(e)}")
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
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # First, get all photo IDs currently in the database
        cursor.execute("SELECT photo_id FROM photos")
        db_photo_ids = set(row[0] for row in cursor.fetchall())
        
        # Find photo IDs that are in the database but not in the API response
        deleted_ids = db_photo_ids - set(existing_photo_ids)
        
        if not deleted_ids:
            logger.info("No deleted photos found to clean up")
            return 0
            
        # Log the IDs to be deleted
        logger.info(f"Found {len(deleted_ids)} photos to remove from database: {deleted_ids}")
        
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
        logger.info(f"Successfully removed {len(deleted_ids)} deleted photos from database")
        return len(deleted_ids)
        
    except Exception as e:
        logger.error(f"Error cleaning deleted photos: {str(e)}")
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
    if not photo_ids:
        return []
        
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        all_connections = []
        
        # For each photo ID, fetch its connections
        for photo_id in photo_ids:
            logger.debug(f"Fetching connections for photo_id {photo_id} from database")
            
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
            
            logger.debug(f"Found {len(connections)} database connections for photo_id {photo_id}")
            
        return all_connections
    
    except Exception as e:
        logger.error(f"Error fetching connections from database: {str(e)}")
        return []
        
    finally:
        if conn:
            conn.close()