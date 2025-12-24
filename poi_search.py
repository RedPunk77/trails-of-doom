import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class POI:
    id: int
    name: str
    latitude: float
    longitude: float
    poi_type: str
    tags: List[str]
    rating: float
    visit_time: int = 60

class RouteBuilder:
    def __init__(self):
        self.pois = self._create_sample_data()
        # Синонимы для улучшения поиска
        self.synonyms = {
            'церковь': ['церковь', 'храм', 'собор', 'часовня'],
            'монастырь': ['монастырь', 'обитель', 'лавра'],
            'старый': ['старый', 'древний', 'старинный', 'исторический'],
            'москва': ['москва', 'московский', 'в москве']
        }
    
    def _create_sample_data(self):
        return [
            POI(1, "Храм Василия Блаженного", 55.7525, 37.6231, "church", 
                ["храм", "собор", "старый", "православный", "москва"], 4.8, 90),
            POI(2, "Новодевичий монастырь", 55.7260, 37.5563, "monastery", 
                ["монастырь", "женский", "старый", "исторический", "москва"], 4.7, 120),
            POI(3, "Успенский собор Московского Кремля", 55.7510, 37.6171, "church", 
                ["собор", "кремль", "старый", "православный", "москва"], 4.9, 60),
            POI(4, "Церковь Вознесения в Коломенском", 55.6674, 37.6709, "church", 
                ["церковь", "древний", "памятник", "коломенское", "москва"], 4.5, 45),
            POI(5, "Саввино-Сторожевский монастырь", 55.7286, 36.8246, "monastery", 
                ["монастырь", "мужской", "звенигород", "подмосковье"], 4.6, 180),
            POI(6, "Храм Христа Спасителя", 55.7445, 37.6054, "church", 
                ["храм", "собор", "кафедральный", "москва"], 4.7, 75),
            POI(7, "Донской монастырь", 55.7146, 37.6027, "monastery", 
                ["монастырь", "некрополь", "старый", "москва"], 4.4, 90),
        ]
    
    def _expand_query_words(self, query_words: List[str]) -> List[str]:
        """Расширяем запрос синонимами"""
        expanded = []
        for word in query_words:
            expanded.append(word)
            # Добавляем синонимы если они есть
            for key, synonyms in self.synonyms.items():
                if word in synonyms:
                    expanded.extend([s for s in synonyms if s != word])
        return list(set(expanded))  # Убираем дубли
    
    def search(self, query: str, center: Tuple[float, float], radius_km: float = 100) -> List[POI]:
        """Улучшенный поиск POI"""
        results = []
        query_words = query.lower().split()
        expanded_words = self._expand_query_words(query_words)
        
        for poi in self.pois:
            # 1. Геофильтр
            dist = self._distance(center, (poi.latitude, poi.longitude))
            if dist > radius_km:
                continue
            
            # 2. Поиск по ключевым словам с синонимами
            score = 0
            poi_text = f"{poi.name.lower()} {' '.join(poi.tags).lower()}"
            
            # Проверяем каждое слово запроса (включая синонимы)
            for word in expanded_words:
                if word in poi_text:
                    # Слово из оригинального запроса дает больше очков
                    if word in query_words:
                        score += 2
                    else:  # Синоним
                        score += 1
            
            # Бонус за тип POI если он упоминается в запросе
            if any(t in query.lower() for t in ['церковь', 'храм', 'собор']) and poi.poi_type == 'church':
                score += 1
            if 'монастырь' in query.lower() and poi.poi_type == 'monastery':
                score += 1
            
            if score > 0:
                # Учитываем расстояние (ближе = лучше) и рейтинг
                distance_score = max(0, 1 - dist / radius_km) * 2
                rating_score = poi.rating / 5.0 * 2
                total_score = score + distance_score + rating_score
                results.append((poi, total_score, dist))
        
        # Сортировка по релевантности
        results.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in results]
    
    def create_route(self, pois: List[POI], max_points: int = 4) -> List[POI]:
        """Создание оптимального маршрута"""
        if not pois:
            return []
        
        # 1. Выбираем не больше max_points
        selected = pois[:max_points]
        
        # 2. Диверсификация по типам (чтобы были не только церкви)
        if len(selected) > 2:
            types = {}
            final_selected = []
            
            for poi in selected:
                if poi.poi_type not in types:
                    types[poi.poi_type] = 0
                
                if types[poi.poi_type] < max_points // 2:
                    final_selected.append(poi)
                    types[poi.poi_type] += 1
                elif len(final_selected) < max_points:
                    final_selected.append(poi)
            
            selected = final_selected[:max_points]
        
        # 3. Оптимизируем порядок
        if len(selected) > 1:
            return self._optimize_order(selected)
        
        return selected
    
    def _optimize_order(self, pois: List[POI]) -> List[POI]:
        """Жадная оптимизация порядка посещения"""
        if len(pois) <= 2:
            return pois
        
        # Начинаем с точки с наибольшим рейтингом
        start = max(pois, key=lambda p: p.rating)
        route = [start]
        unvisited = [p for p in pois if p.id != start.id]
        
        while unvisited:
            last = route[-1]
            # Находим ближайшую точку
            next_poi = min(unvisited, 
                          key=lambda p: self._distance(
                              (last.latitude, last.longitude),
                              (p.latitude, p.longitude)
                          ))
            route.append(next_poi)
            unvisited.remove(next_poi)
        
        return route
    
    def calculate_stats(self, route: List[POI]) -> Dict:
        """Расчет статистики маршрута"""
        if not route:
            return {}
        
        travel_time = 0
        visit_time = sum(p.visit_time for p in route)
        distance = 0
        
        for i in range(len(route)-1):
            p1 = route[i]
            p2 = route[i+1]
            dist = self._distance((p1.latitude, p1.longitude), 
                                 (p2.latitude, p2.longitude))
            distance += dist
            travel_time += dist / 40 * 60  # 40 км/ч
        
        total_time = travel_time + visit_time
        
        return {
            'points': len(route),
            'distance_km': round(distance, 1),
            'total_hours': round(total_time / 60, 1),
            'visit_hours': round(visit_time / 60, 1),
            'travel_hours': round(travel_time / 60, 1),
            'types': list(set(p.poi_type for p in route))
        }
    
    @staticmethod
    def _distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Простой расчет расстояния в км"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        return np.sqrt((lat1-lat2)**2 + (lon1-lon2)**2) * 111

def main():
    builder = RouteBuilder()
    
    # Тестовые запросы
    queries = [
        ("старые церкви", (55.7522, 37.6156), 50),
        ("монастыри в Москве", (55.7522, 37.6156), 50),
        ("храмы", (55.7522, 37.6156), 100),
        ("соборы и монастыри", (55.7522, 37.6156), 100),
    ]
    
    for query, center, radius in queries:
        print(f"\n{'='*50}")
        print(f"🔍 Запрос: '{query}' (радиус: {radius} км)")
        print(f"📍 Центр: {center}")
        
        # 1. Поиск
        found = builder.search(query, center, radius_km=radius)
        print(f"   Найдено мест: {len(found)}")
        
        if found:
            print(f"   Топ-5 найденных:")
            for i, poi in enumerate(found[:5], 1):
                dist = builder._distance(center, (poi.latitude, poi.longitude))
                print(f"     {i}. {poi.name} ({poi.poi_type}) - ⭐{poi.rating} - {dist:.1f} км")
        
        # 2. Построение маршрута
        route = builder.create_route(found, max_points=4)
        
        if route:
            # 3. Расчет статистики
            stats = builder.calculate_stats(route)
            
            print(f"\n   📍 МАРШРУТ ({stats['points']} точек, типы: {', '.join(stats['types'])}):")
            for i, poi in enumerate(route, 1):
                dist_from_center = builder._distance(center, (poi.latitude, poi.longitude))
                print(f"      {i}. {poi.name}")
                print(f"          тип: {poi.poi_type}, ⭐{poi.rating}, ⏱️{poi.visit_time} мин, 📍{dist_from_center:.1f} км")
            
            print(f"\n   📊 СТАТИСТИКА:")
            print(f"      • Всего времени: {stats['total_hours']} ч")
            print(f"      • На посещение: {stats['visit_hours']} ч")
            print(f"      • В пути: {stats['travel_hours']} ч")
            print(f"      • Общее расстояние: {stats['distance_km']} км")
        else:
            print("   ❌ Не удалось построить маршрут")

if __name__ == "__main__":
    main()
