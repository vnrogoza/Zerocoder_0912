"""
Тестовый скрипт для проверки работы GigaChat API и получения access token.
"""
import requests
import urllib3

# Отключаем предупреждения о небезопасных SSL сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

payload = {
    'scope': 'GIGACHAT_API_PERS'
}

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
    'RqUID': 'client_id',
    'Authorization': 'Basic client_secret'
}

print("Отправка запроса...\n")

try:
    # Добавляем verify=False для обхода SSL ошибки
    response = requests.post(
        url, 
        headers=headers, 
        data=payload,
        verify=False,  # Отключаем проверку SSL сертификата
        timeout=30
    )
    
    print(f"Статус код: {response.status_code}")
    print(f"Заголовки ответа: {dict(response.headers)}\n")
    
    if response.status_code == 200:
        try:
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_at = token_data.get("expires_at")
            
            if access_token:
                print("=" * 60)
                print("✅ УСПЕХ! Access token получен")
                print("=" * 60)
                print(f"Access Token: {access_token}")
                if expires_at:
                    print(f"Истекает: {expires_at}")
                print("=" * 60)                
            else:
                raise Exception("Токен не найден в ответе")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    else:
        raise Exception(f"Не удалось получить токен: {response.status_code}")
except Exception as e:
    print(f"❌ Ошибка: {e}")
