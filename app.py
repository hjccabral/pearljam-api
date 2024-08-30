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
            database=os.getenv('DB_NAME', 'pearl_jam_db')
        )
        app.logger.info("Database connection successful")
        return conn
    except mysql.connector.Error as err:
        app.logger.error(f"Database connection failed: {err}")
        raise

@app.route('/api/pearl-jam/integrants', methods=['GET'])
def get_pearl_jam_integrants():
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT name, instrument, start_year, end_year
            FROM integrants
            ORDER BY start_year, name
        """)
        results = cursor.fetchall()

        integrants = []
        for row in results:
            integrant = {
                'name': row['name'],
                'instrument': row['instrument'],
                'start_year': row['start_year'],
                'end_year': row['end_year'] if row['end_year'] else 'Present'
            }
            integrants.append(integrant)

        result = {
            "band": "Pearl Jam",
            "integrants": integrants
        }

        return jsonify(result)


@app.route('/api/pearl-jam/album', methods=['GET'])
def get_all_pearl_jam_data():
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT a.id as album_id, a.name as album_name, a.year,
                   s.name as song_name, s.track_number
            FROM albums a
            LEFT JOIN songs s ON a.id = s.album_id
            ORDER BY a.year, a.id, s.track_number
        """)
        results = cursor.fetchall()

        album_data = defaultdict(lambda: {'songs': []})
        for row in results:
            album_id = row['album_id']
            album_data[album_id]['name'] = row['album_name']
            album_data[album_id]['year'] = row['year']
            if row['song_name']:
                album_data[album_id]['songs'].append({
                    'name': row['song_name'],
                    'track_number': row['track_number']
                })

        result = {
            "band": "Pearl Jam",
            "albums": list(album_data.values())
        }

        return jsonify(result)
    
@app.route('/api/pearl-jam/album/<string:album_name>', methods=['GET'])
def get_album_info(album_name):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.name as album_name, a.year, s.name as song_name, s.track_number
        FROM albums a
        LEFT JOIN songs s ON a.id = s.album_id
        WHERE a.name = %s
        ORDER BY s.track_number
    """, (album_name,))
    results = cursor.fetchall()
    
    if results:
        album_info = {
            'name': results[0]['album_name'],
            'year': results[0]['year'],
            'songs': [{'name': row['song_name'], 'track_number': row['track_number']} 
                      for row in results if row['song_name']]
        }
        conn.close()
        return jsonify({
            "band": "Pearl Jam",
            "album": album_info
        })
    else:
        conn.close()
        return jsonify({
            "band": "Pearl Jam",
            "error": f"Album '{album_name}' not found"
        }), 404

@app.route('/api/pearl-jam/music/year/<int:year>', methods=['GET'])
def get_music_by_year(year):
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT s.name FROM songs s JOIN albums a ON s.album_id = a.id WHERE a.year = %s", (year,))
        music = cursor.fetchall()

        if music:
            return jsonify({
                "band": "Pearl Jam",
                "year": year,
                "music": [song['name'] for song in music]
            })
        else:
            return jsonify({
                "band": "Pearl Jam",
                "error": f"No music found for the year {year}"
            }), 404

@app.route('/api/pearl-jam/music/<string:music_name>', methods=['GET'])
def get_music_info(music_name):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT s.name AS music_name, s.track_number,
                       a.name AS album_name, a.year
                FROM songs s
                JOIN albums a ON s.album_id = a.id
                WHERE s.name = %s
            """
            cursor.execute(query, (music_name,))
            music_info = cursor.fetchone()

            if music_info:
                response = jsonify({
                    "band": "Pearl Jam",
                    "music": {
                        "name": music_info['music_name'],
                        "track_number": music_info['track_number'],
                        "album": {
                            "name": music_info['album_name'],
                            "year": music_info['year']
                        }
                    }
                })
                response.headers['Content-Type'] = 'application/json'
                return response
            else:
                return jsonify({
                    "band": "Pearl Jam",
                    "error": f"Music '{music_name}' not found"
                }), 404
    except Exception as e:
        app.logger.error(f"Error in get_music_info: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Test successful"}), 200

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({"error": "An unexpected error occurred"}), 500

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers['Content-Type'] = 'application/json'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)