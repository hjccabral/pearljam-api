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

@app.route('/api/pearl-jam', methods=['GET'])
def get_all_pearl_jam_data():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.id as album_id, a.name as album_name, a.year, 
               s.name as song_name, s.track_number
        FROM albums a
        LEFT JOIN songs s ON a.id = s.album_id
        ORDER BY a.year, a.id, s.track_number
    """)
    results = cursor.fetchall()
    
    album_data = {}
    for row in results:
        album_id = row['album_id']
        if album_id not in album_data:
            album_data[album_id] = {
                'name': row['album_name'],
                'year': row['year'],
                'songs': []
            }
        if row['song_name']:
            album_data[album_id]['songs'].append({
                'name': row['song_name'],
                'track_number': row['track_number']
            })
    
    result = {
        "band": "Pearl Jam",
        "album": list(album_data.values())
    }
    
    conn.close()
    return jsonify(result)

@app.route('/api/pearl-jam/music/year/<int:year>', methods=['GET'])
def get_music_by_year(year):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT name FROM songs WHERE year = %s", (year,))
    music = cursor.fetchall()
    
    conn.close()
    
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

@app.route('/api/pearl-jam/music/<string:music_name>', methods=['GET'])
def get_music_info(music_name):
    app.logger.debug(f"Received request for music: {music_name}")
    app.logger.debug(f"Request headers: {request.headers}")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT s.name AS music_name, s.track_number, 
               a.name AS album_name, a.year
        FROM songs s
        JOIN albums a ON s.album_id = a.id
        WHERE s.name = %s
    """
    app.logger.info(f"Executing query: {query}")
    cursor.execute(query, (music_name,))
    music_info = cursor.fetchone()
    
    app.logger.info(f"Query result: {music_info}")
    conn.close()
    
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
        app.logger.debug(f"Sending response: {response.get_data(as_text=True)}")
        return response
    else:
        error_response = jsonify({
            "band": "Pearl Jam",
            "error": f"Music '{music_name}' not found"
        }), 404
        error_response[0].headers['Content-Type'] = 'application/json'
        app.logger.debug(f"Sending error response: {error_response[0].get_data(as_text=True)}")
        return error_response

@app.route('/test', methods=['GET'])
def test():
    app.logger.debug("Test route accessed")
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
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)