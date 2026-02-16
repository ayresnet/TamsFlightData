import requests
from bs4 import BeautifulSoup
import sys
import json
import datetime
import os

# Forzar salida UTF-8
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

URL = "http://www.tams.com.ar/organismos/vuelos.aspx"
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

def get_flights_data(movement_type='A', airport='AEP'):
    print(f"Consultando {movement_type} en {airport}...")
    try:
        # 1. GET inicial
        r = s.get(URL)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        
        viewstate_input = soup.find('input', {'id': '__VIEWSTATE'})
        eventvalidation_input = soup.find('input', {'id': '__EVENTVALIDATION'})
        viewstategenerator_input = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})

        if not viewstate_input or not eventvalidation_input:
            print("Error: No se encontraron los campos ocultos iniciales.")
            return []

        viewstate = viewstate_input.get('value')
        eventvalidation = eventvalidation_input.get('value')
        viewstategenerator = viewstategenerator_input.get('value')

        # 2. Payload
        payload = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            'ddlMovTp': movement_type,       
            'ddlAeropuerto': airport,          
            'ddlSector': '-1',               
            'ddlAerolinea': '0',            # 0 = TODAS las aerolíneas
            'ddlAterrizados': 'TODOS',
            'ddlVentanaH': '6',              
            'btnBuscar': 'Buscar'            
        }

        # 3. POST
        r_post = s.post(URL, data=payload)
        r_post.raise_for_status()

        # 4. Parsear
        soup_post = BeautifulSoup(r_post.content, 'html.parser')
        table_id = 'dgGrillaA' if movement_type == 'A' else 'dgGrillaD'
        table = soup_post.find('table', {'id': table_id})

        flights_list = []

        if not table:
            print(f"No table found for {movement_type} at {airport}")
            return []

        rows = table.find_all('tr')
        # Arribos: Cia(0), Vuelo(1), STA(2), Matricula(3), Pos(4), ETA(5), ATA(6), Term(7), Sec(8), Cinta(9), LF(10), Orig(11), Via(12), Remark(13), San(14), Pax(15)
        # Partidas: Cia(0), Vuelo(1), STD(2), Matricula(3), Pos(4), ETD(5), ATD(6), Term(7), Sec(8), Check(9), Pte(10), Dest(11), Via(12), Remark(13), San(14), Org(15)

        for row in rows[1:]: # Saltar header
            cols = row.find_all('td')
            if not cols: continue
            
            # Limpiar textos
            data_row = [c.get_text(strip=True) for c in cols]
            
            # Validar longitud mínima para evitar errores
            if len(data_row) < 5: continue

            flight_obj = {
                'airline': data_row[0] if len(data_row) > 0 else '',
                'flight': data_row[1] if len(data_row) > 1 else '',
                'registration': data_row[3] if len(data_row) > 3 else '',
                'position': data_row[4] if len(data_row) > 4 else '',
                'terminal': data_row[7] if len(data_row) > 7 else '',
                'sector': data_row[8] if len(data_row) > 8 else '',
                'remark': data_row[13] if len(data_row) > 13 else '',
                'type': movement_type,
                'airport': airport
            }

            if movement_type == 'A':
                flight_obj.update({
                    'sta': data_row[2] if len(data_row) > 2 else '',
                    'eta': data_row[5] if len(data_row) > 5 else '',
                    'ata': data_row[6] if len(data_row) > 6 else '',
                    'origin': data_row[11] if len(data_row) > 11 else '',
                })
            else:
                 flight_obj.update({
                    'std': data_row[2] if len(data_row) > 2 else '',
                    'etd': data_row[5] if len(data_row) > 5 else '',
                    'atd': data_row[6] if len(data_row) > 6 else '',
                    'destination': data_row[11] if len(data_row) > 11 else '',
                    'gate': data_row[10] if len(data_row) > 10 else ''
                 })

            flights_list.append(flight_obj)
            
        return flights_list

    except Exception as e:
        print(f"Error extracting {movement_type} {airport}: {e}")
        return []

if __name__ == "__main__":
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Recopilar todos los datos
    all_flights = []
    
    # AEP
    all_flights.extend(get_flights_data('A', 'AEP'))
    all_flights.extend(get_flights_data('D', 'AEP'))
    
    # EZE
    all_flights.extend(get_flights_data('A', 'EZE'))
    all_flights.extend(get_flights_data('D', 'EZE'))

    print(f"Total flights found: {len(all_flights)}")

    output = {
        "success": True,
        "last_updated": current_time,
        "count": len(all_flights),
        "data": all_flights
    }

    # Guardar JSON
    try:
        with open('flights.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print("Success: flights.json created.")
    except Exception as e:
        print(f"Error writing json: {e}")
