# -*- coding: utf-8 -*-
import requests
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Product:
    name: str
    price: str
    specifications: str

class CompuzoneParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        })
        self.base_url = "https://www.compuzone.co.kr/search/search_list.php"

    def get_search_options(self, keyword: str) -> List[Dict[str, str]]:
        """컴퓨존에서는 브랜드 필터를 동적으로 가져오지 않고 원본 코드의 방식을 사용합니다."""
        try:
            # 원본 코드의 search_compuzone 함수 로직을 사용하여 브랜드 추출
            params = {
                "actype": "list", "SearchType": "small", "SearchText": keyword,
                "PreOrder": "sale_order", "PageCount": "100", "StartNum": "0",
                "PageNum": "1", "ListType": "0", "BigDivNo": "", "MediumDivNo": "",
                "DivNo": "", "MinPrice": "0", "MaxPrice": "0",
            }
            headers = {
                "Accept": "*/*",
                "Referer": f"https://www.compuzone.co.kr/search/search.htm?SearchProductKey={keyword}",
                "X-Requested-With": "XMLHttpRequest",
            }
            
            resp = self.session.get(self.base_url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 원본 코드처럼 제품명에서 브랜드 추출
            product_items = soup.select("li.li-obj")
            brands = set()
            
            # 일반적인 PC 부품 브랜드들
            common_brands = [
                'ASUS', 'MSI', 'GIGABYTE', 'EVGA', 'ZOTAC', 'PALIT', 'GALAX', 'INNO3D',
                'SAMSUNG', '삼성전자', 'SK하이닉스', 'CRUCIAL', 'KINGSTON', 'WD', 'Seagate',
                'CORSAIR', '마이크로닉스', 'SEASONIC', 'COOLER MASTER', 'THERMALTAKE',
                'INTEL', 'AMD', 'NVIDIA', 'LG전자', 'HP', 'DELL', 'LENOVO'
            ]
            
            for item in product_items:
                product_name_tag = item.select_one(".prd_info_name.prdTxt")
                if product_name_tag:
                    product_name = product_name_tag.get_text(strip=True).upper()
                    for brand in common_brands:
                        if brand.upper() in product_name:
                            brands.add(brand)
            
            return [{'name': brand, 'code': brand} for brand in sorted(brands)]
            
        except Exception as e:
            print(f"An error occurred while fetching search options: {e}")
            return []

    def search_products(self, keyword: str, sort_type: str, maker_codes: List[str], limit: int = 5) -> List[Product]:
        """원본 search_compuzone 함수의 로직을 그대로 사용"""
        params = {
            "actype": "list", "SearchType": "small", "SearchText": keyword,
            "PreOrder": "sale_order", "PageCount": "100", "StartNum": "0",
            "PageNum": "1", "ListType": "0", "BigDivNo": "", "MediumDivNo": "",
            "DivNo": "", "MinPrice": "0", "MaxPrice": "0",
        }
        headers = {
            "Accept": "*/*",
            "Referer": f"https://www.compuzone.co.kr/search/search.htm?SearchProductKey={keyword}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
        
        try:
            resp = self.session.get(self.base_url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            products = []
            product_items = soup.select("li.li-obj")
            
            for item in product_items:
                product = self._parse_product_item(item, maker_codes)
                if product:
                    products.append(product)
                    if len(products) >= limit:
                        break
            
            return products
            
        except Exception as e:
            print(f"An error occurred while searching for products: {e}")
            return []

    def _parse_product_item(self, item, maker_codes: List[str]) -> Optional[Product]:
        """원본 코드의 제품 파싱 로직을 그대로 사용"""
        try:
            product_name_tag = item.select_one(".prd_info_name.prdTxt")
            price_tag = item.select_one(".prd_price .number")
            
            if not product_name_tag or not price_tag:
                return None
            
            product_name = product_name_tag.get_text(strip=True)
            price_text = price_tag.get_text(strip=True)
            
            # 원본 코드의 브랜드 필터 로직
            if maker_codes:
                brand_found = False
                for brand in maker_codes:
                    if brand.upper() in product_name.upper():
                        brand_found = True
                        break
                if not brand_found:
                    return None
            
            # 원본 코드의 가격 처리 로직
            price_clean = re.sub(r'[^0-9]', '', price_text)
            if price_clean:
                formatted_price = f"{int(price_clean):,}원"
            else:
                formatted_price = "가격 문의"
            
            # 컴퓨존에서는 별도 사양 정보가 제한적이므로 간단히 처리
            specifications = "컴퓨존 상품"
            
            return Product(name=product_name, price=formatted_price, specifications=specifications)
            
        except Exception as e:
            print(f"Error parsing product item: {e}")
            return None

    def get_unique_products(self, keyword: str, maker_codes: List[str]) -> List[Product]:
        """danawa와 호환되도록 하지만 컴퓨존은 단일 검색만 수행"""
        products = self.search_products(keyword, "sale_order", maker_codes, limit=10)
        
        # 중복 제거
        unique_products = []
        seen_names = set()
        for product in products:
            if product.name not in seen_names:
                unique_products.append(product)
                seen_names.add(product.name)
        
        return unique_products


# 원본 코드의 독립 실행을 위한 함수들 (하위 호환성)
def search_compuzone(keyword, brand_filter=None):
    """원본 코드와의 하위 호환성을 위한 함수"""
    parser = CompuzoneParser()
    
    try:
        # 전체 제품 검색
        all_products = parser.search_products(keyword, "sale_order", [], limit=100)
        
        # 브랜드 필터 적용된 제품
        filtered_products = []
        if brand_filter:
            filtered_products = parser.search_products(keyword, "sale_order", [brand_filter], limit=100)
        
        # 원본 반환 형식 유지
        return {
            'keyword': keyword, 
            'brand_filter': brand_filter, 
            'total_count': len(all_products),
            'found_products': len(all_products), 
            'all_products': [{'name': p.name, 'price': int(p.price.replace('원', '').replace(',', ''))} for p in all_products if p.price != "가격 문의"],
            'filtered_count': len(filtered_products) if brand_filter else None,
            'filtered_products': [{'name': p.name, 'price': int(p.price.replace('원', '').replace(',', ''))} for p in filtered_products if p.price != "가격 문의"] if brand_filter else None
        }
        
    except Exception as e:
        print(f"❌ 검색 중 오류 발생: {e}")
        return None