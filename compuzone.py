# -*- coding: utf-8 -*-
import requests
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict, Optional
import urllib.parse

@dataclass
class Product:
    name: str
    price: str
    specifications: str

class CompuzoneParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.base_url = "https://www.compuzone.co.kr/search/search.htm"
        self.search_api_url = "https://www.compuzone.co.kr/search/search_list.php"

    def _get_manufacturer_from_search_api(self, keyword: str) -> List[Dict[str, str]]:
        """search_list.php API 호출로 제조사 체크박스를 추출합니다."""
        try:
            # 메인 페이지 먼저 방문 (쿠키 설정용)
            encoded_keyword = urllib.parse.quote(keyword, encoding='utf-8')
            search_url = f"{self.base_url}?SearchProductKey={encoded_keyword}"
            self.session.get(search_url, timeout=10)
            
            # API 호출로 제조사 체크박스 포함된 HTML 가져오기
            params = {
                "actype": "list",
                "SearchType": "small",
                "SearchText": keyword,
                "PreOrder": "sale_order",
                "PageCount": "20",
                "StartNum": "0",
                "PageNum": "1",
                "ListType": "0",
                "BigDivNo": "",
                "MediumDivNo": "",
                "DivNo": "",
                "MinPrice": "0",
                "MaxPrice": "0",
                "ChkMakerNo": "",
                "sub_actype": "maker"  # 제조사 정보 요청
            }
            
            headers = {
                "Accept": "*/*",
                "Referer": search_url,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            
            resp = self.session.get(self.search_api_url, params=params, headers=headers, timeout=10)
            resp.encoding = 'euc-kr'
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 제조사 체크박스 추출
            checkbox_selectors = [
                'input[name_vals*="|"][vals]',
                'input[class*="chkMedium"][vals]',
                'input[onclick*="chk_maker"][vals]',
                'input[id^="chk"][vals]'
            ]
            
            manufacturers = []
            
            for selector in checkbox_selectors:
                manufacturer_checkboxes = soup.select(selector)
                if manufacturer_checkboxes:
                    print(f"API에서 제조사 체크박스 {len(manufacturer_checkboxes)}개 발견")
                    
                    for checkbox in manufacturer_checkboxes:
                        vals = checkbox.get('vals')  # 제조사 ID (숫자)
                        name_vals = checkbox.get('name_vals', '')
                        
                        if vals and vals.isdigit():  # 숫자 ID만 사용
                            brand_name = ''
                            
                            # name_vals에서 브랜드명 추출 (형식: "브랜드|ID")
                            if name_vals and '|' in name_vals:
                                brand_name = name_vals.split('|')[0]
                            
                            # label에서도 시도
                            if not brand_name:
                                checkbox_id = checkbox.get('id', '')
                                if checkbox_id:
                                    label = soup.find('label', {'for': checkbox_id})
                                    if label:
                                        label_text = label.get_text(strip=True)
                                        # 괄호와 숫자 제거
                                        brand_name = re.sub(r'\s*\(\d+\)\s*$', '', label_text)
                            
                            if brand_name:
                                manufacturers.append({'name': brand_name, 'code': vals})
                                print(f"  - {brand_name} (ID: {vals})")
                    
                    if manufacturers:
                        break
            
            return manufacturers[:20]
            
        except Exception as e:
            print(f"API에서 제조사 추출 실패: {e}")
            return []
    
    def _get_known_manufacturer_ids(self, keyword: str) -> List[Dict[str, str]]:
        """알려진 제조사 ID 매핑을 반환합니다."""
        # 제공받은 분석 자료에서 확인된 제조사 ID들
        known_manufacturers = {
            '삼성전자': '2',
            'HP': '99',
            '레노버': '4629',
            # 추가 제조사들 (추정)
            'LG전자': '3',
            'ASUS': '100',
            'MSI': '101',
            'GIGABYTE': '102',
            'Western Digital': '200',
            'Seagate': '201',
            'Kingston': '300',
            'Crucial': '301',
            'INTEL': '400',
            'AMD': '401',
        }
        
        manufacturers = []
        
        # 키워드에 따라 관련 제조사들만 반환
        keyword_lower = keyword.lower()
        
        if any(k in keyword_lower for k in ['ssd', 'nvme', 'storage', '저장']):
            # 저장장치 관련 제조사
            relevant_brands = ['삼성전자', 'Western Digital', 'Seagate', 'Kingston', 'Crucial']
        elif any(k in keyword_lower for k in ['cpu', 'processor', '프로세서']):
            # CPU 관련 제조사
            relevant_brands = ['INTEL', 'AMD']
        elif any(k in keyword_lower for k in ['gpu', 'graphic', '그래픽']):
            # GPU 관련 제조사
            relevant_brands = ['ASUS', 'MSI', 'GIGABYTE']
        elif any(k in keyword_lower for k in ['notebook', 'laptop', '노트북']):
            # 노트북 관련 제조사
            relevant_brands = ['삼성전자', 'LG전자', 'HP', '레노버', 'ASUS']
        else:
            # 일반적인 제조사들
            relevant_brands = list(known_manufacturers.keys())[:10]
        
        for brand in relevant_brands:
            if brand in known_manufacturers:
                manufacturers.append({'name': brand, 'code': known_manufacturers[brand]})
        
        return manufacturers

    def _get_manufacturers_from_actual_products(self, keyword: str) -> List[Dict[str, str]]:
        """실제 검색된 제품들에서 제조사를 추출합니다."""
        try:
            # 제조사 필터링 없이 전체 제품 검색
            encoded_keyword = urllib.parse.quote(keyword, encoding='utf-8')
            search_url = f"{self.base_url}?SearchProductKey={encoded_keyword}"
            
            # 검색 페이지 접근
            resp = self.session.get(search_url, timeout=10)
            resp.encoding = 'utf-8'
            resp.raise_for_status()
            
            # API 호출로 실제 제품 목록 가져오기 (컴퓨터부품 카테고리로 제한)
            params = {
                "actype": "list",
                "SearchType": "small",
                "SearchText": keyword,
                "PreOrder": "sale_order",
                "PageCount": "100",  # 더 많은 제품을 가져와서 제조사 추출
                "StartNum": "0",
                "PageNum": "1",
                "ListType": "0",
                "BigDivNo": "4",  # 컴퓨터부품 카테고리
                "MediumDivNo": "",
                "DivNo": "",
                "MinPrice": "0",
                "MaxPrice": "0",
                "ChkMakerNo": ""
            }
            
            headers = {
                "Accept": "*/*",
                "Referer": search_url,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            
            resp = self.session.get(self.search_api_url, params=params, headers=headers, timeout=10)
            resp.encoding = 'euc-kr'
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 제품 아이템에서 제조사 추출
            product_items = soup.select("li.li-obj")
            manufacturers_found = {}  # {브랜드명: ID} 형태로 저장
            
            print(f"실제 검색된 제품 수: {len(product_items)}개")
            
            for item in product_items:
                product_name_tag = item.select_one(".prd_info_name.prdTxt, .prd_info_name")
                if product_name_tag:
                    product_name = product_name_tag.get_text(strip=True)
                    
                    # [브랜드] 형식에서 브랜드 추출
                    bracket_brand_match = re.search(r'\[([^\]]+)\]', product_name)
                    if bracket_brand_match:
                        brand_name = bracket_brand_match.group(1)
                        
                        # 해당 브랜드의 제조사 ID 찾기 (API 호출을 통해)
                        if brand_name not in manufacturers_found:
                            brand_id = self._find_manufacturer_id_for_brand(brand_name, keyword)
                            if brand_id:
                                manufacturers_found[brand_name] = brand_id
                                print(f"  - {brand_name} (ID: {brand_id})")
            
            # 결과를 리스트로 변환
            result = []
            for brand_name, brand_id in manufacturers_found.items():
                result.append({'name': brand_name, 'code': brand_id})
            
            print(f"실제 제품이 있는 제조사: {len(result)}개")
            return result[:15]  # 최대 15개까지
            
        except Exception as e:
            print(f"실제 제품에서 제조사 추출 실패: {e}")
            return []

    def _find_manufacturer_id_for_brand(self, brand_name: str, keyword: str) -> Optional[str]:
        """특정 브랜드의 제조사 ID를 찾습니다."""
        try:
            # API에서 제조사 체크박스 추출하여 해당 브랜드 ID 찾기
            manufacturers_from_api = self._get_manufacturer_from_search_api(keyword)
            
            for mfr in manufacturers_from_api:
                if mfr['name'].lower() == brand_name.lower():
                    return mfr['code']
            
            # 알려진 제조사 매핑에서도 찾기
            known_mapping = {
                '삼성전자': '2', 'HP': '99', '레노버': '4629',
                'Western Digital': '24', 'SEAGATE': '25', 'ADATA': '3400',
                '동화': '439', 'SEBAP': '10219', 'HPE': '15947'
            }
            
            return known_mapping.get(brand_name)
            
        except Exception as e:
            print(f"브랜드 {brand_name}의 ID 찾기 실패: {e}")
            return None

    def _extract_brands_from_search_results(self, keyword: str) -> List[Dict[str, str]]:
        """실제 검색 결과에서 브랜드를 추출합니다 (간단한 방법)."""
        try:
            # 기본 제품 검색 (제조사 필터링 없이)
            products = self.search_products(keyword, "sale_order", [], limit=50)
            
            # 제품명에서 브랜드 추출
            brands_found = {}  # {브랜드명: 개수} 형태로 저장
            
            print(f"검색된 제품 수: {len(products)}개")
            
            for product in products:
                # [브랜드] 형식 추출
                bracket_match = re.search(r'\[([^\]]+)\]', product.name)
                if bracket_match:
                    brand_name = bracket_match.group(1).strip()
                    if len(brand_name) > 1:  # 너무 짧은 것 제외
                        brands_found[brand_name] = brands_found.get(brand_name, 0) + 1
                        if len(brands_found) <= 5:  # 처음 5개만 디버그 출력
                            print(f"  브랜드 발견: [{brand_name}] from {product.name[:40]}...")
            
            # 알려진 제조사 ID 매핑 (더 포괄적으로)
            known_ids = {
                'SEBAP': '10219', 'Western Digital': '24', '동화': '439', 
                'SEAGATE': '25', 'HPE': '15947', '삼성전자': '2', 
                'HP': '99', '레노버': '4629', 'ASUS': '9', 'MSI': '475',
                'GIGABYTE': '14', 'ADATA': '3400', 'Crucial': '6348',
                'Kingston': '18', 'Corsair': '763', 'G.SKILL': '1419',
                '지스킬': '1419', 'TeamGroup': '1419', 'TEAMGROUP': '1419',
                'CORSAIR': '763', 'Patriot': '1046', 'KINGMAX': '18'
            }
            
            # 제품 개수 기준으로 정렬 (실제로 많이 나오는 브랜드 우선)
            sorted_brands = sorted(brands_found.items(), key=lambda x: x[1], reverse=True)
            
            # 결과 생성
            result = []
            for brand_name, count in sorted_brands:
                # 알려진 ID가 있으면 사용, 없으면 브랜드명을 ID로 사용
                brand_id = known_ids.get(brand_name, brand_name)
                result.append({'name': brand_name, 'code': brand_id})
            
            print(f"실제 제품에서 추출한 브랜드: {len(result)}개")
            for brand in result[:10]:  # 처음 10개만 표시
                count = brands_found[brand['name']]
                print(f"  - {brand['name']} (ID: {brand['code']}) - {count}개 제품")
            
            return result[:15]  # 최대 15개까지
            
        except Exception as e:
            print(f"브랜드 추출 실패: {e}")
            return []

    def get_search_options(self, keyword: str) -> List[Dict[str, str]]:
        """컴퓨존에서 검색 결과를 통해 브랜드를 추출합니다."""
        try:
            # 간단한 방법: 실제 제품 검색 후 제품명에서 브랜드 추출
            return self._extract_brands_from_search_results(keyword)
            
            # 3단계: API에서 제품명을 통해 브랜드 추출 (fallback)
            # URL 인코딩된 검색어로 요청
            encoded_keyword = urllib.parse.quote(keyword, encoding='utf-8')
            search_url = f"{self.base_url}?SearchProductKey={encoded_keyword}"
            
            # 먼저 검색 페이지에 접근
            resp = self.session.get(search_url, timeout=10)
            resp.encoding = 'euc-kr'  # 컴퓨존은 EUC-KR 인코딩 사용
            resp.raise_for_status()
            
            # 검색 결과 목록 가져오기
            params = {
                "actype": "list",
                "SearchType": "small", 
                "SearchText": keyword,
                "PreOrder": "sale_order",
                "PageCount": "50",
                "StartNum": "0",
                "PageNum": "1",
                "ListType": "0",
                "BigDivNo": "",
                "MediumDivNo": "",
                "DivNo": "",
                "MinPrice": "0",
                "MaxPrice": "0"
            }
            
            headers = {
                "Accept": "*/*",
                "Referer": search_url,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            
            resp = self.session.get(self.search_api_url, params=params, headers=headers, timeout=10)
            resp.encoding = 'euc-kr'  # 컴퓨존은 EUC-KR 인코딩 사용
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 제품명에서 브랜드 추출
            product_items = soup.select("li.li-obj")
            brands = set()
            
            # 확장된 PC 부품 브랜드 리스트 (더 포괄적)
            common_brands = [
                # 그래픽카드 브랜드
                'ASUS', 'MSI', 'GIGABYTE', 'EVGA', 'ZOTAC', 'PALIT', 'GALAX', 'INNO3D', 'SAPPHIRE',
                'XFX', 'POWERCOLOR', 'HIS', 'GAINWARD', 'PNY', 'LEADTEK', 'MANLI', 'AFOX',
                # 메모리/저장장치 브랜드
                'SAMSUNG', '삼성전자', 'SK하이닉스', 'CRUCIAL', 'KINGSTON', 'WD', 'Seagate', 'TOSHIBA',
                'G.SKILL', 'TEAMGROUP', 'ADATA', 'PATRIOT', 'HYPERX', 'GEIL', 'MUSHKIN', 'CORSAIR',
                # 파워/케이스 브랜드  
                '마이크로닉스', 'SEASONIC', 'COOLER MASTER', 'THERMALTAKE', 'ANTEC', 'FSP', 'SILVERSTONE',
                # CPU/칩셋 브랜드
                'INTEL', 'AMD', 'NVIDIA', 
                # 주변기기/모니터 브랜드
                'LG전자', 'HP', 'DELL', 'LENOVO', 'ACER', 'BENQ', 'VIEWSONIC', 'AOC',
                # 기타 PC 브랜드
                'RAZER', 'LOGITECH', 'STEELSERIES', 'ROCCAT', 'REDRAGON', 'ABKO', '레오폴드'
            ]
            
            for item in product_items:
                product_name_tag = item.select_one(".prd_info_name.prdTxt")
                if product_name_tag:
                    product_name = product_name_tag.get_text(strip=True)
                    
                    # 컴퓨존의 [브랜드] 형식 추출
                    bracket_brand_match = re.search(r'\[([^\]]+)\]', product_name)
                    if bracket_brand_match:
                        bracket_brand = bracket_brand_match.group(1)
                        brands.add(bracket_brand)
                    
                    # 기존 브랜드 매칭도 계속 사용
                    product_name_upper = product_name.upper()
                    for brand in common_brands:
                        if brand.upper() in product_name_upper:
                            brands.add(brand)
            
            # 실제로 찾은 브랜드만 반환 (기본 브랜드 목록 제거)
            if not brands:
                return []  # 브랜드를 찾지 못하면 빈 목록 반환
            
            return [{'name': brand, 'code': brand} for brand in sorted(brands)]
            
        except Exception as e:
            print(f"브랜드 검색 중 오류 발생: {e}")
            # 오류 시에도 빈 목록 반환 (실제 데이터가 없으면 브랜드도 없어야 함)
            return []

    def search_products(self, keyword: str, sort_type: str, maker_codes: List[str], limit: int = 5) -> List[Product]:
        """컴퓨존에서 제품을 검색합니다."""
        try:
            # URL 인코딩된 검색어
            encoded_keyword = urllib.parse.quote(keyword, encoding='utf-8')
            search_url = f"{self.base_url}?SearchProductKey={encoded_keyword}"
            
            # 검색 페이지 접근
            resp = self.session.get(search_url, timeout=10)
            resp.encoding = 'utf-8'
            resp.raise_for_status()
            
            # API 파라미터 설정 (컴퓨터부품 카테고리로 제한, 제조사 필터링은 클라이언트에서 처리)
            params = {
                "actype": "list",
                "SearchType": "small",
                "SearchText": keyword,
                "PreOrder": sort_type if sort_type else "sale_order",
                "PageCount": "100",  # 충분한 결과를 가져와서 클라이언트에서 필터링
                "StartNum": "0",
                "PageNum": "1",
                "ListType": "0",
                "BigDivNo": "4",  # 컴퓨터부품 카테고리
                "MediumDivNo": "",
                "DivNo": "",
                "MinPrice": "0",
                "MaxPrice": "0",
                "ChkMakerNo": ""  # 서버 필터링 대신 클라이언트 필터링 사용
            }
            
            headers = {
                "Accept": "*/*",
                "Referer": search_url,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            
            resp = self.session.get(self.search_api_url, params=params, headers=headers, timeout=10)
            resp.encoding = 'euc-kr'  # 컴퓨존은 EUC-KR 인코딩 사용
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
            print(f"제품 검색 중 오류 발생: {e}")
            return []

    def _parse_product_item(self, item, maker_codes: List[str]) -> Optional[Product]:
        """제품 아이템을 파싱합니다."""
        try:
            # 제품명 추출
            product_name_tag = item.select_one(".prd_info_name.prdTxt, .prd_info_name")
            if not product_name_tag:
                return None
                
            product_name = product_name_tag.get_text(strip=True)
            if not product_name:
                return None
            
            # 브랜드 필터링 (컴퓨존 [브랜드] 형식 고려)
            if maker_codes:
                brand_found = False
                
                # [브랜드] 형식에서 브랜드 추출
                bracket_brand_match = re.search(r'\[([^\]]+)\]', product_name)
                if bracket_brand_match:
                    bracket_brand = bracket_brand_match.group(1).strip()
                    
                    # 제조사 코드와 매칭
                    for code in maker_codes:
                        # 숫자 ID인 경우 알려진 매핑으로 확인
                        if code.isdigit():
                            known_brand_names = {
                                '2': '삼성전자', '24': 'Western Digital', '25': 'SEAGATE',
                                '99': 'HP', '4629': '레노버', '10219': 'SEBAP', 
                                '439': '동화', '15947': 'HPE', '1419': 'G.SKILL',
                                '3400': 'ADATA', '6348': 'Crucial', '18': 'Kingston',
                                '763': 'Corsair', '1046': 'Patriot'
                            }
                            expected_brand = known_brand_names.get(code, '')
                            if expected_brand and bracket_brand.upper() == expected_brand.upper():
                                brand_found = True
                                break
                        # 브랜드명 직접 매칭
                        elif code.upper() == bracket_brand.upper():
                            brand_found = True
                            break
                        # 부분 매칭도 시도
                        elif bracket_brand.upper() in code.upper() or code.upper() in bracket_brand.upper():
                            brand_found = True
                            break
                
                if not brand_found:
                    return None
            
            # 가격 추출 - 여러 가능한 선택자 시도
            price_text = "가격 문의"
            price_selectors = [
                ".prd_price .number",
                ".prd_price .price", 
                ".price_sect .number",
                ".price .number",
                ".prd_price"
            ]
            
            for selector in price_selectors:
                price_tag = item.select_one(selector)
                if price_tag:
                    price_text = price_tag.get_text(strip=True)
                    break
            
            # 가격 정리
            price_clean = re.sub(r'[^0-9]', '', price_text)
            if price_clean and price_clean != '0':
                formatted_price = f"{int(price_clean):,}원"
            else:
                formatted_price = "가격 문의"
            
            # 사양 정보 추출 시도 (다양한 방법으로)
            specifications = []
            
            # 1. 제품명에서 주요 사양 추출
            name_specs = self._extract_specs_from_name(product_name)
            if name_specs:
                specifications.extend(name_specs)
            
            # 2. .prd_subTxt에서 상세 사양 정보 추출 (가장 정확한 방법)
            prd_subTxt = item.select_one(".prd_subTxt")
            if prd_subTxt:
                spec_text = prd_subTxt.get_text(strip=True)
                if spec_text and len(spec_text) > 10:
                    # 불필요한 텍스트 제거 후 사양 정보 추가
                    clean_spec = re.sub(r'\s+', ' ', spec_text)
                    specifications.append(clean_spec[:200])  # 너무 길면 자르기
            
            # 3. .prd_subTxt가 없으면 .prd_info에서 추출 (기존 방법)
            if not any('/' in spec for spec in specifications):
                prd_info = item.select_one(".prd_info")
                if prd_info:
                    info_text = prd_info.get_text(separator=' | ', strip=True)
                    parts = info_text.split(' | ')
                    
                    if len(parts) > 3:
                        spec_part = parts[3].strip()
                        if spec_part and len(spec_part) > 10 and not any(skip in spec_part for skip in ['토스', '확정발주', '입고지연']):
                            spec_items = [s.strip() for s in spec_part.split('/') if s.strip() and len(s.strip()) > 2]
                            if spec_items:
                                selected_specs = spec_items[:5]
                                specifications.append(' / '.join(selected_specs))
            
            # 4. 기본값 설정
            if not specifications:
                specifications.append("컴퓨존 상품")
            
            return Product(
                name=product_name, 
                price=formatted_price, 
                specifications=" / ".join(specifications)
            )
            
        except Exception as e:
            print(f"제품 파싱 중 오류: {e}")
            return None

    def _extract_specs_from_name(self, product_name: str) -> List[str]:
        """제품명에서 주요 사양 정보를 추출합니다."""
        specs = []
        name_upper = product_name.upper()
        
        # GPU 메모리 용량 추출 (그래픽카드)
        gpu_memory_patterns = [
            r'(\d+GB)\s*D?D?R?\d*',  # 8GB, 16GB DDR6 등
            r'(\d+G)\s*D?D?R?\d*',   # 8G DDR6 등
        ]
        for pattern in gpu_memory_patterns:
            matches = re.findall(pattern, name_upper)
            if matches:
                specs.extend([f"VRAM {match}" for match in matches])
        
        # 메모리/저장장치 용량 추출
        storage_patterns = [
            r'(\d+TB)',    # 1TB, 2TB 등
            r'(\d+GB)',    # 256GB, 512GB 등
        ]
        for pattern in storage_patterns:
            matches = re.findall(pattern, name_upper)
            if matches:
                specs.extend(matches)
        
        # 메모리 타입 추출
        memory_types = ['DDR4', 'DDR5', 'GDDR6', 'GDDR6X', 'HBM2', 'HBM3']
        for mem_type in memory_types:
            if mem_type in name_upper:
                specs.append(mem_type)
        
        # GPU 시리즈 추출
        gpu_series = ['RTX 4090', 'RTX 4080', 'RTX 4070', 'RTX 4060', 'RTX 3080', 'RTX 3070', 'RTX 3060', 
                     'RX 7900', 'RX 7800', 'RX 7700', 'RX 6800', 'RX 6700', 'RX 6600',
                     'GTX 1660', 'GTX 1650', 'ARC A770', 'ARC A750']
        for series in gpu_series:
            if series in name_upper:
                specs.append(series)
        
        # CPU 시리즈 추출  
        cpu_patterns = [
            r'I\d-\d+K?F?',     # i5-13400F, i7-13700K 등
            r'RYZEN \d+ \d+X?', # RYZEN 5 5600X 등
        ]
        for pattern in cpu_patterns:
            matches = re.findall(pattern, name_upper)
            if matches:
                specs.extend(matches)
                
        return specs[:3]  # 최대 3개만 반환

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
