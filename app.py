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
    st.subheader("제조사를 선택하세요")
    
    with st.form(key="manufacturer_form"):
        cols = st.columns(4)
        for i, manufacturer in enumerate(st.session_state.manufacturers):
            with cols[i % 4]:
                # 각 체크박스에 고유한 key를 할당합니다. Streamlit이 이 key를 사용해 상태를 관리합니다.
                st.checkbox(manufacturer['name'], key=f"mfr_{i}")
        
        # 버튼들을 나란히 배치
        col1, col2, col3 = st.columns(3)
        with col1:
            product_search_button = st.form_submit_button("선택한 제조사로 제품 검색")
        with col2:
            if st.form_submit_button("모든 제조사 선택"):
                # 모든 체크박스를 True로 설정
                for i in range(len(st.session_state.manufacturers)):
                    st.session_state[f"mfr_{i}"] = True
                st.rerun()
        with col3:
            clear_all_button = st.form_submit_button("전체 해제")

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
    
    if clear_all_button:
        # 모든 체크박스를 False로 설정
        for i in range(len(st.session_state.manufacturers)):
            st.session_state[f"mfr_{i}"] = False
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
    
    # 다크모드와 라이트모드 모두 지원하는 테이블 스타일
    st.markdown("""
    <style>
    .adaptive-table {
        width: 100%;
        border-collapse: collapse;
        font-family: "Source Sans Pro", sans-serif;
        font-size: 14px;
        background-color: var(--background-color);
        color: var(--text-primary-color);
    }
    
    /* 라이트 모드 기본값 */
    .adaptive-table {
        --background-color: white;
        --text-primary-color: rgb(38, 39, 48);
        --header-bg-color: rgb(240, 242, 246);
        --border-color: rgb(230, 234, 241);
        --hover-bg-color: rgb(245, 245, 245);
        --link-color: rgb(255, 75, 75);
    }
    
    /* 다크 모드 감지 및 적용 */
    @media (prefers-color-scheme: dark) {
        .adaptive-table {
            --background-color: rgb(14, 17, 23);
            --text-primary-color: rgb(250, 250, 250);
            --header-bg-color: rgb(38, 39, 48);
            --border-color: rgb(68, 70, 84);
            --hover-bg-color: rgb(38, 39, 48);
            --link-color: rgb(255, 115, 115);
        }
    }
    
    /* 스트림릿 다크 테마 클래스 감지 */
    [data-theme="dark"] .adaptive-table {
        --background-color: rgb(14, 17, 23);
        --text-primary-color: rgb(250, 250, 250);
        --header-bg-color: rgb(38, 39, 48);
        --border-color: rgb(68, 70, 84);
        --hover-bg-color: rgb(38, 39, 48);
        --link-color: rgb(255, 115, 115);
    }
    
    .adaptive-table th {
        background-color: var(--header-bg-color);
        color: var(--text-primary-color);
        font-weight: 600;
        padding: 0.5rem 0.75rem;
        text-align: left;
        border-bottom: 1px solid var(--border-color);
    }
    
    .adaptive-table td {
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid var(--border-color);
        color: var(--text-primary-color);
        background-color: var(--background-color);
    }
    
    .adaptive-table tr:hover td {
        background-color: var(--hover-bg-color);
    }
    
    .adaptive-table a {
        color: var(--link-color);
        text-decoration: none;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 3px;
        border: 1px solid var(--link-color);
        background-color: transparent;
        transition: all 0.2s ease;
    }
    
    .adaptive-table a:hover {
        background-color: var(--link-color);
        color: var(--background-color);
    }
    </style>
    """, unsafe_allow_html=True)
    
    html_table = df_with_links.to_html(escape=False, index=False, classes='adaptive-table')
    st.markdown(html_table, unsafe_allow_html=True)

    # Reset button
    if st.button("새로 검색하기"):
        st.session_state.keyword = ""
        st.session_state.manufacturers = []
        st.session_state.selected_manufacturers = {}
        st.session_state.products = []
        st.rerun()
