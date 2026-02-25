import sqlite3
from typing import List, Tuple, Optional
from collections import Counter

def create_database(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                phone TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                iso_code TEXT NOT NULL)''')
        
        conn.commit()
        print(f"База данных и таблица успешно созданы по пути: {db_path}")
    except sqlite3.Error as e:
        print(f"Ошибка при создании базы данных: {e}")
    finally:
        conn.close()

def get_records(db_path: str, phone: Optional[str] = None, iso_code: Optional[str] = None) -> List[Tuple[str, str, str]]:
    """
    

    db_path (str)
    phone (Optional[str]): Номер телефона
    iso_code (Optional[str]): ISO-код страны 
    
    Returns:
        List[Tuple[str, str, str]]: Список кортежей с данными (phone, token, iso_code)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if phone:
            cursor.execute('SELECT phone, token, iso_code FROM sessions WHERE phone = ?', (phone,))
        elif iso_code:
            cursor.execute('SELECT phone, token, iso_code FROM sessions WHERE iso_code = ?', (iso_code,))
        else:
            cursor.execute('SELECT phone, token, iso_code FROM sessions')
        
        records = cursor.fetchall()
        return records
    except sqlite3.Error as e:
        print(f"Ошибка при получении записей: {e}")
        return []
    finally:
        conn.close()

def delete_record(db_path: str, phone: str) -> bool:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM sessions WHERE phone = ?', (phone,))
        if not cursor.fetchone():
            print(f"Запись с номером {phone} не найдена")
            return False
        cursor.execute('DELETE FROM sessions WHERE phone = ?', (phone,))
        conn.commit()
        
        print(f"Запись с номером {phone} успешно удалена")
        return True
    except sqlite3.Error as e:
        print(f"Ошибка при удалении записи: {e}")
        return False
    finally:
        conn.close()

def count_iso_codes(db_path: str) -> str:
    """Подсчитывает количество каждого ISO-кода в базе данных и возвращает результат в формате "US:2 RU:0 UK:1"."""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
       
        cursor.execute('SELECT iso_code FROM sessions')
        rows = cursor.fetchall()
        iso_codes = [row[0] for row in rows if row[0]]
        iso_counts = Counter(iso_codes)
        
        #формируем результат в формат us: 1 и тд
        result = [f"{code}:{count}" for code, count in sorted(iso_counts.items())]
        return ' '.join(result)
    except sqlite3.Error as e:
        print(f"Ошибка при подсчёте ISO-кодов: {e}")
        return ""
    finally:
        conn.close()

def insert_record(db_path: str, phone: str, token: str, iso_code: str) -> bool:
    """   

    db_path (str)
    phone (str): Номер телефона (PRIMARY KEY)
    token (str): токен
    iso_code (str): ISO-код страны
   
    Returns:
        bool: True, если запись добавлена и False в случае ошибки
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
       
        cursor.execute('''
            INSERT INTO sessions (phone, token, iso_code)
            VALUES (?, ?, ?)
        ''', (phone, token, iso_code))
       
        conn.commit()
        print(f"Запись с номером {phone} успешно добавлена")
        return True
    except sqlite3.IntegrityError as e:
        print(f"Ошибка: Запись с номером {phone} уже существует ({e})")
        return False
    except sqlite3.Error as e:
        print(f"Ошибка при добавлении записи: {e}")
        return False
    finally:
        conn.close()

