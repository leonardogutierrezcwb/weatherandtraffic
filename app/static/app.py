from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Carrega variáveis de ambiente
load_dotenv()

# Cria a aplicação Flask
app = Flask(__name__)
CORS(app)  # Habilita CORS para todas as rotas

# Configurações padrão
DEFAULT_SETTINGS = {
    'home_address': '',
    'work_address': '',
    'dark_mode': False,
    'weather_api_key': os.getenv('WEATHER_API_KEY', ''),
    'traffic_api_key': os.getenv('TRAFFIC_API_KEY', '')
}

@app.route('/app/templates/index.html')
def index():
    return render_template('index.html', settings=DEFAULT_SETTINGS)

@app.route('/api/weather', methods=['GET'])
def get_weather():
    try:
        lat = request.args.get('lat', default=-23.5505, type=float)
        lon = request.args.get('lon', default=-46.6333, type=float)
        api_key = request.args.get('api_key', default=DEFAULT_SETTINGS['weather_api_key'], type=str)
        
        if not api_key:
            return jsonify({'error': 'Chave da API de tempo não configurada'}), 400
        
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        weather_data = {
            'city': data.get('name', 'Local desconhecido'),
            'temp': round(data['main']['temp']),
            'temp_min': round(data['main']['temp_min']),
            'temp_max': round(data['main']['temp_max']),
            'humidity': data['main']['humidity'],
            'wind_speed': round(data['wind']['speed'] * 3.6, 1),
            'description': data['weather'][0]['description'],
            'icon': data['weather'][0]['icon']
        }
        
        return jsonify(weather_data)
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/traffic', methods=['GET'])
def get_traffic():
    try:
        origin = request.args.get('origin', type=str)
        destination = request.args.get('destination', type=str)
        api_key = request.args.get('api_key', default=DEFAULT_SETTINGS['traffic_api_key'], type=str)
        
        if not api_key:
            return jsonify({'error': 'Chave da API de trânsito não configurada'}), 400
        
        if not origin or not destination:
            return jsonify({'error': 'Endereços de origem e destino são necessários'}), 400
        
        # Geocodificação dos endereços
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        print(f"Geocodificando origem: {origin}")  # Log para debug
        origin_response = requests.get(geocode_url, params={
            'address': origin,
            'key': api_key
        })
        origin_response.raise_for_status()
        origin_data = origin_response.json()
        
        print(f"Geocodificando destino: {destination}")  # Log para debug
        destination_response = requests.get(geocode_url, params={
            'address': destination,
            'key': api_key
        })
        destination_response.raise_for_status()
        destination_data = destination_response.json()
        
        if origin_data['status'] != 'OK':
            error_msg = origin_data.get('error_message', 'Erro ao geocodificar origem')
            print(f"Erro geocodificação origem: {error_msg}")
            return jsonify({'error': error_msg}), 400
            
        if destination_data['status'] != 'OK':
            error_msg = destination_data.get('error_message', 'Erro ao geocodificar destino')
            print(f"Erro geocodificação destino: {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        origin_location = origin_data['results'][0]['geometry']['location']
        destination_location = destination_data['results'][0]['geometry']['location']
        
        # Obter direções com informações de trânsito
        directions_url = "https://maps.googleapis.com/maps/api/directions/json"
        
        print("Obtendo informações de trânsito...")  # Log para debug
        directions_response = requests.get(directions_url, params={
            'origin': f"{origin_location['lat']},{origin_location['lng']}",
            'destination': f"{destination_location['lat']},{destination_location['lng']}",
            'departure_time': 'now',
            'traffic_model': 'best_guess',
            'key': api_key
        })
        directions_response.raise_for_status()
        directions_data = directions_response.json()
        
        print("Resposta da API Directions:", directions_data)  # Log para debug
        
        if directions_data['status'] != 'OK':
            error_msg = directions_data.get('error_message', 'Erro na API de direções')
            print(f"Erro Directions API: {error_msg}")
            return jsonify({'error': error_msg}), 400
            
        if not directions_data.get('routes'):
            error_msg = 'Nenhuma rota encontrada entre os endereços'
            print(error_msg)
            return jsonify({'error': error_msg}), 400
        
        route = directions_data['routes'][0]['legs'][0]
        duration = route.get('duration_in_traffic', route['duration'])
        normal_duration = route['duration']
        
        traffic_data = {
            'origin': origin,
            'destination': destination,
            'duration': duration['value'] // 60,  # em minutos
            'normal_duration': normal_duration['value'] // 60,
            'distance': route['distance']['text'],
            'summary': normal_duration['text']
        }
        
        return jsonify(traffic_data)
    
    except requests.exceptions.RequestException as e:
        error_msg = f'Erro na requisição: {str(e)}'
        print(error_msg)
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    app.run(debug=True)

    # Adicione no final do arquivo
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)