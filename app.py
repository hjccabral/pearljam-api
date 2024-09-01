from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import os
from collections import defaultdict
import logging

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes
logging.basicConfig(level=logging.DEBUG)

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'db'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'password'),
            database=os.getenv('DB_NAME', 'pearljam-db')
        )
        app.logger.info("Database connection successful")
        return conn
    except mysql.connector.Error as err:
        app.logger.error(f"Database connection failed: {err}")
        raise

@app.route('/api/pearljam/integrants', methods=['GET'])
def get_pearl_jam_integrants():
    with get_db_connection() as conn:
        db_mysql = conn.cursor(dictionary=True)

        db_mysql.execute("""
            SELECT name, instrument, start_year, end_year
            FROM integrants
            ORDER BY start_year, name
        """)
        results = db_mysql.fetchall()

        integrants = []
        for row in results:
            integrant = {
                'name': row['name'],
                'instrument': row['instrument'],
                'start_year': row['start_year'],
                'end_year': row['end_year'] if row['end_year'] else 'Present'
            }
            integrants.append(integrant)

        response = {
            "band": "Pearl Jam",
            "integrants": integrants
        }

        return jsonify(response)


@app.route('/api/pearljam/album', methods=['GET'])
def get_all_pearl_jam_data():
    with get_db_connection() as conn:
        db_mysql = conn.cursor(dictionary=True)

        db_mysql.execute("""
            SELECT a.id as album_id, a.name as album_name, a.year,
                s.name as song_name, s.track_number
            FROM albums a
            LEFT JOIN songs s ON a.id = s.album_id
            ORDER BY a.year, a.id, s.track_number
        """)
        results = db_mysql.fetchall()

        album_data = defaultdict(lambda: {'musics': []})
        for row in results:
            album_id = row['album_id']
            album_data[album_id]['name'] = row['album_name']
            album_data[album_id]['year'] = row['year']
            if row['song_name']:
                album_data[album_id]['musics'].append({
                    'name': row['song_name'],
                    'track_number': row['track_number']
                })

        response = {
            "band": "Pearl Jam",
            "albums": list(album_data.values())
        }

        return jsonify(response)
    
@app.route('/api/pearljam/album/<string:album_name>', methods=['GET'])
def get_album_info(album_name):
    with get_db_connection() as conn:
        db_mysql = conn.cursor(dictionary=True)
        
        db_mysql.execute("""
            SELECT a.name as album_name, a.year, s.name as song_name, s.track_number
            FROM albums a
            LEFT JOIN songs s ON a.id = s.album_id
            WHERE a.name = %s
            ORDER BY s.track_number
        """, (album_name,))
        results = db_mysql.fetchall()
        
        if results:
            album_info = {
                'name': results[0]['album_name'],
                'year': results[0]['year'],
                'musics': [{'name': row['song_name'], 'track_number': row['track_number']} 
                                           for row in results if row['song_name']]
            }
            response = {
                "band": "Pearl Jam",
                "album": album_info
            }
            return jsonify(response)
        else:
            response = {
                "band": "Pearl Jam",
                "error": f"Album '{album_name}' not found"
            }
            return jsonify(response), 404

@app.route('/api/pearljam/music/year/<int:year>', methods=['GET'])
def get_music_by_year(year):
    with get_db_connection() as conn:
        db_mysql = conn.cursor(dictionary=True)

        db_mysql.execute("SELECT s.name FROM songs s JOIN albums a ON s.album_id = a.id WHERE a.year = %s", (year,))
        music = db_mysql.fetchall()

        if music:
            response = {
                "band": "Pearl Jam",
                "year": year,
                "music": [song['name'] for song in music]
            }
            return jsonify(response)
        else:
            response = {
                "band": "Pearl Jam",
                "error": f"No music found for the year {year}"
            }
            return jsonify(response), 404

@app.route('/api/pearljam/music/<string:music_name>', methods=['GET'])
def get_music_info(music_name):
    try:
        with get_db_connection() as conn:
            db_mysql = conn.cursor(dictionary=True)

            query = """
                SELECT s.name AS music_name, s.track_number,
                    a.name AS album_name, a.year
                FROM songs s
                JOIN albums a ON s.album_id = a.id
                WHERE s.name = %s
            """
            db_mysql.execute(query, (music_name,))
            music_info = db_mysql.fetchone()

            if music_info:
                response = {
                    "band": "Pearl Jam",
                    "music": {
                        "name": music_info['music_name'],
                        "track_number": music_info['track_number'],
                        "album": {
                            "name": music_info['album_name'],
                            "year": music_info['year']
                        }
                    }
                }
                return jsonify(response)
            else:
                response = {
                    "band": "Pearl Jam",
                    "error": f"Music '{music_name}' not found"
                }
                return jsonify(response), 404
    except Exception as e:
        app.logger.error(f"Error in get_music_info: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/api/pearljam/music', methods=['GET'])
def get_all_music():
    try:
        with get_db_connection() as conn:
            db_mysql = conn.cursor(dictionary=True)

            query = """
                SELECT s.name AS music_name, s.track_number,
                    a.name AS album_name, a.year
                FROM songs s
                JOIN albums a ON s.album_id = a.id
                ORDER BY a.year, a.name, s.track_number
            """
            db_mysql.execute(query)
            music_info = db_mysql.fetchall()

            if music_info:
                albums = defaultdict(lambda: {"year": None, "musics": []})
                for row in music_info:
                    album_name = row['album_name']
                    albums[album_name]["year"] = row['year']
                    albums[album_name]["musics"].append({
                        "name": row['music_name'],
                        "track_number": row['track_number']
                    })

                album_list = [{
                    "name": album,
                    "year": info["year"],
                    "musics": info["musics"]
                } for album, info in albums.items()]

                response = {
                    "band": "Pearl Jam",
                    "albums": album_list
                }
                return jsonify(response)
            else:
                response = {
                    "band": "Pearl Jam",
                    "error": "No music found"
                }
                return jsonify(response), 404
    except Exception as e:
        app.logger.error(f"Error in get_all_music: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/api/pearljam/album/id/<int:album_id>', methods=['GET'])
def get_album_info_by_id(album_id):
    with get_db_connection() as conn:
        db_mysql = conn.cursor(dictionary=True)
        
        db_mysql.execute("""
            SELECT a.id as album_id, a.name as album_name, a.year, s.name as song_name, s.track_number
            FROM albums a
            LEFT JOIN songs s ON a.id = s.album_id
            WHERE a.id = %s
            ORDER BY s.track_number
        """, (album_id,))
        results = db_mysql.fetchall()
        
        if results:
            album_info = {
                'id': results[0]['album_id'],
                'name': results[0]['album_name'],
                'year': results[0]['year'],
                'musics': [{'name': row['song_name'], 'track_number': row['track_number']} 
                                           for row in results if row['song_name']]
            }
            response = {
                "band": "Pearl Jam",
                "album": album_info
            }
            return jsonify(response)
        else:
            response = {
                "band": "Pearl Jam",
                "error": f"Album with ID '{album_id}' not found"
            }
            return jsonify(response), 404

@app.route('/api/pearljam/album/year/<int:year>', methods=['GET'])
def get_albums_by_year(year):
    with get_db_connection() as conn:
        db_mysql = conn.cursor(dictionary=True)
        
        db_mysql.execute("""
            SELECT a.id as album_id, a.name as album_name, a.year, s.name as song_name, s.track_number
            FROM albums a
            LEFT JOIN songs s ON a.id = s.album_id
            WHERE a.year = %s
            ORDER BY s.track_number
        """, (year,))
        results = db_mysql.fetchall()
        
        if results:
            albums = defaultdict(lambda: {'musics': []})
            for row in results:
                album_id = row['album_id']
                albums[album_id]['id'] = album_id
                albums[album_id]['name'] = row['album_name']
                albums[album_id]['year'] = row['year']
                if row['song_name']:
                    albums[album_id]['musics'].append({
                        'name': row['song_name'],
                        'track_number': row['track_number']
                    })
            
            album_list = list(albums.values())
            response = {
                "band": "Pearl Jam",
                "albums": album_list
            }
            return jsonify(response)
        else:
            response = {
                "band": "Pearl Jam",
                "error": f"No albums found for the year {year}"
            }
            return jsonify(response), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)