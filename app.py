import streamlit as st
import pandas as pd
from compuzone import CompuzoneParser, Product

st.set_page_config(page_title="컴퓨존 상품 검색", layout="wide")

st.title("🛒 컴퓨존 상품 검색기")

# Initialize session state
if 'parser' not in st.session_state:
    st.session_state.parser = CompuzoneParser()
if 'keyword' not in st.session_state:
    st.session_state.keyword = ""
if 'manufacturers' not in st.session_state:
    st.session_state.manufacturers = []
if 'selected_manufacturers' not in st.session_state:
    st.session_state.selected_manufacturers = {}
if 'products' not in st.session_state:
    st.session_state.products = []

# --- 1. Keyword Input using a Form ---
with st.form(key="search_form"):
    keyword_input = st.text_input(
        "검색어를 입력하세요:", 
        placeholder="예: 그래픽카드, SSD", 
        value=st.session_state.get("keyword", "")
    )
    search_button = st.form_submit_button(label="제조사 검색")

if search_button:
    st.session_state.keyword = keyword_input
    st.session_state.products = [] # 새로운 검색 시 이전 제품 결과 초기화
    if st.session_state.keyword:
        with st.spinner("제조사 정보를 가져오는 중..."):
            st.session_state.manufacturers = st.session_state.parser.get_search_options(st.session_state.keyword)
            st.session_state.selected_manufacturers = {m['name']: False for m in st.session_state.manufacturers}
            if not st.session_state.manufacturers:
                st.warning("해당 검색어에 대한 제조사 정보를 찾을 수 없습니다.")
    else:
        st.warning("검색어를 입력해주세요.")

# --- 2. Manufacturer Selection ---
if st.session_state.manufacturers:
    st.subheader("제조사를 선택하세요 (중복 가능)")
    with st.form(key="manufacturer_form"):
        cols = st.columns(4)
        for i, manufacturer in enumerate(st.session_state.manufacturers):
            with cols[i % 4]:
                # 각 체크박스에 고유한 key를 할당합니다. Streamlit이 이 key를 사용해 상태를 관리합니다.
                st.checkbox(manufacturer['name'], key=f"mfr_{i}")
        
        product_search_button = st.form_submit_button("선택한 제조사로 제품 검색")

    if product_search_button:
        # 폼 제출 후, st.session_state에서 직접 각 체크박스의 상태를 읽어옵니다.
        selected_codes = []
        for i, manufacturer in enumerate(st.session_state.manufacturers):
            if st.session_state[f"mfr_{i}"]:
                selected_codes.append(manufacturer['code'])
        
        if not selected_codes:
            st.warning("하나 이상의 제조사를 선택해주세요.")
        else:
            with st.spinner('제품 정보를 검색 중입니다...'):
                # 컴퓨존 검색만 실행
                compuzone_products = st.session_state.parser.get_unique_products(
                    st.session_state.keyword, selected_codes
                )
                
                st.session_state.products = compuzone_products
                
                if not st.session_state.products:
                    st.info("선택된 제조사의 제품을 찾을 수 없습니다.")
                # 검색이 완료되면 페이지를 새로고침하여 결과를 즉시 표시합니다.
                st.rerun()

# --- 3. Display Results ---
if st.session_state.products:
    st.subheader(f"'{st.session_state.keyword}'에 대한 검색 결과")

    # 가격순으로 정렬하기 위한 헬퍼 함수
    def extract_price(product):
        try:
            # "원"과 ","를 제거하고 숫자로 변환
            price_str = product.price.replace('원', '').replace(',', '')
            return int(price_str)
        except (ValueError, AttributeError):
            # "가격 문의" 등 변환 불가능한 경우, 맨 뒤로 보내기 위해 무한대 값 반환
            return float('inf')

    # 제품 목록을 가격 오름차순으로 정렬
    sorted_products = sorted(st.session_state.products, key=extract_price)
    
    # 데이터프레임 생성
    data = []
    for i, p in enumerate(sorted_products):
        data.append({
            "제품명": p.name,
            "가격": p.price,
            "주요 사양": p.specifications,
            "구매링크": p.product_link if p.product_link else ""
        })
    
    df = pd.DataFrame(data)
    
    # 클릭 가능한 링크로 데이터프레임 수정
    df_with_links = df.copy()
    for i, product in enumerate(sorted_products):
        if product.product_link:
            df_with_links.at[i, "구매링크"] = f'<a href="{product.product_link}" target="_blank">구매{i+1}</a>'
        else:
            df_with_links.at[i, "구매링크"] = "링크없음"
    
    # 스타일이 적용된 HTML 테이블로 표시
    st.markdown("""
    <style>
    table {
        border-collapse: collapse;
        margin: 25px 0;
        font-size: 0.9em;
        font-family: sans-serif;
        min-width: 400px;
        border-radius: 5px 5px 0 0;
        overflow: hidden;
        width: 100%;
    }
    table thead tr {
        background-color: #009879;
        color: #ffffff;
        text-align: left;
    }
    table th,
    table td {
        padding: 12px 15px;
        border: 1px solid #dddddd;
    }
    table tbody tr {
        border-bottom: 1px solid #dddddd;
    }
    table tbody tr:nth-of-type(even) {
        background-color: #f3f3f3;
    }
    table tbody tr:hover {
        background-color: #f5f5f5;
    }
    table a {
        color: #009879;
        text-decoration: none;
        font-weight: bold;
        padding: 5px 10px;
        border: 1px solid #009879;
        border-radius: 3px;
        transition: all 0.3s;
    }
    table a:hover {
        background-color: #009879;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    html_table = df_with_links.to_html(escape=False, index=False, classes='styled-table')
    st.markdown(html_table, unsafe_allow_html=True)

    # Reset button
    if st.button("새로 검색하기"):
        st.session_state.keyword = ""
        st.session_state.manufacturers = []
        st.session_state.selected_manufacturers = {}
        st.session_state.products = []
        st.rerun()
