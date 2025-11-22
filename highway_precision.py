import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from geopy.distance import geodesic
import glob 
import os 

# 設定頁面
st.set_page_config(page_title="國道里程查詢 (自動載入/DMS)", page_icon="🛣️", layout="wide")

st.title("🛣️ 國道里程精準查詢 (進階版)")
st.markdown("程式已自動載入 `/data` 資料夾內所有國道 KML 資料。")

# ------------------------------------------------
# --- 輔助函式 (KML 解析與 DMS 轉換) ---
# ------------------------------------------------

@st.cache_data
def dms_to_dd(deg, minute, sec):
    """將度分秒 (DMS) 格式轉換為十進位 (DD) 格式"""
    return deg + (minute / 60) + (sec / 3600)

@st.cache_data(show_spinner="首次載入資料中... (自動載入所有 KML)")
def load_all_kml_data(data_folder="./data/"):
    """自動讀取指定資料夾內所有 KML 檔案並合併"""
    
    kml_files = glob.glob(os.path.join(data_folder, '*.kml'))
    
    if not kml_files:
        st.error(f"❌ 在 {data_folder} 資料夾中找不到 KML 檔案。請確認檔案已放置。")
        return None
        
    all_data = []
    
    def parse_kml_content(kml_content):
        soup = BeautifulSoup(kml_content, 'xml')
        placemarks = soup.find_all('Placemark')
        
        data_list = []
        for p in placemarks:
            try:
                name = p.find('name').text if p.find('name') else "未命名"
                coord_tag = p.find('coordinates')
                if coord_tag:
                    coords_text = coord_tag.text.strip()
                    coords_text = coords_text.split()[0] 
                    parts = coords_text.split(',')
                    if len(parts) >= 2:
                        lon = float(parts[0]) 
                        lat = float(parts[1]) 
                        data_list.append({'name': name, 'lat': lat, 'lon': lon})
            except Exception:
                continue 
        return pd.DataFrame(data_list)

    for filepath in kml_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            df_kml = parse_kml_content(content)
            if not df_kml.empty:
                df_kml['source'] = os.path.basename(filepath) 
                all_data.append(df_kml)
        except Exception as e:
            st.warning(f"⚠️ 無法讀取檔案 {os.path.basename(filepath)}: {e}")

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return None

def find_nearest_point(df, user_lat, user_lon):
    """尋找最近的點"""
    df['diff_lat'] = df['lat'] - user_lat
    df['diff_lon'] = df['lon'] - user_lon
    df['dist_sq'] = df['diff_lat']**2 + df['diff_lon']**2
    
    nearest_row = df.loc[df['dist_sq'].idxmin()]
    
    highway_pt = (nearest_row['lat'], nearest_row['lon'])
    user_pt = (user_lat, user_lon)
    real_distance_m = geodesic(user_pt, highway_pt).meters
    
    return nearest_row, real_distance_m

# ------------------------------------------------
# --- 介面啟動與邏輯 ---
# ------------------------------------------------

df_all = load_all_kml_data()

if df_all is not None:
    st.success(f"✅ 資料載入成功！共 {len(df_all)} 個里程點。")
    
    st.divider()
    st.subheader("2. 輸入座標與確認位置")

    input_type = st.radio(
        "選擇座標輸入格式",
        ('十進位 (DD: 25.1234)', '度分秒 (DMS: 25° 7\' 24")')
    )
    
    u_lat, u_lon = None, None 
    
    # --- DD 輸入調整：使用較小的欄位來控制寬度 ---
    if input_type == '十進位 (DD: 25.1234)':
        # 設置一個 3:1 的佈局，讓輸入框只佔 3/4 的寬度
        col_input_dd, _ = st.columns([3, 1]) 
        
        with col_input_dd:
            col1, col2 = st.columns(2) # 在這個 3/4 寬度的欄位內再分成兩欄
            with col1:
                u_lat = st.number_input("輸入緯度 (Latitude/N)", value=25.0480, format="%.6f", key="lat_dd")
            with col2:
                u_lon = st.number_input("輸入經度 (Longitude/E)", value=121.5170, format="%.6f", key="lon_dd")
            
    # --- DMS 輸入調整：使用一個主欄位來控制整體靠左 ---
    elif input_type == '度分秒 (DMS: 25° 7\' 24")':
        # 設置一個 4:6 的佈局，讓輸入框只佔 4/10 的寬度
        col_input_dms, _ = st.columns([4, 6]) 

        with col_input_dms:
            st.markdown("##### 緯度 (N)")
            col_n_deg, col_n_min, col_n_sec = st.columns(3)
            with col_n_deg:
                n_deg = st.number_input("度", min_value=0, max_value=90, value=25, key="n_deg")
            with col_n_min:
                n_min = st.number_input("分", min_value=0, max_value=59, value=2, key="n_min")
            with col_n_sec:
                n_sec = st.number_input("秒", min_value=0.0, max_value=59.999, value=53.0, format="%.2f", key="n_sec")
            
            u_lat = dms_to_dd(n_deg, n_min, n_sec)
            st.caption(f"轉換後緯度 (DD): {u_lat:.6f}")

            st.markdown("##### 經度 (E)")
            col_e_deg, col_e_min, col_e_sec = st.columns(3)
            with col_e_deg:
                e_deg = st.number_input("度", min_value=0, max_value=180, value=121, key="e_deg")
            with col_e_min:
                e_min = st.number_input("分", min_value=0, max_value=59, value=35, key="e_min")
            with col_e_sec:
                e_sec = st.number_input("秒", min_value=0.0, max_value=59.999, value=4.0, format="%.2f", key="e_sec")
                
            u_lon = dms_to_dd(e_deg, e_min, e_sec)
            st.caption(f"轉換後經度 (DD): {u_lon:.6f}")

    # 確保座標已定義
    if u_lat is not None and u_lon is not None:
        
        # Google Maps 按鈕放在一個較窄的欄位中
        col_button, _ = st.columns([4, 6])
        with col_button:
            google_maps_url = f"https://www.google.com/maps/search/?api=1&query={u_lat},{u_lon}"
            st.link_button("🌏 在 Google Maps 確認此座標", google_maps_url)
        
        st.divider()

        # 觸發計算
        if st.button("🔍 查詢最近里程", type="primary"):
            with st.spinner("計算中..."):
                result, dist_m = find_nearest_point(df_all, u_lat, u_lon)
                
                st.markdown("### 📍 查詢結果")
                
                c1, c2, c3 = st.columns(3)
                
                mileage_name = result['name']
                source_file = result['source'].replace('.kml', '')
                
                c1.metric("來源國道", source_file)
                c2.metric("里程樁號", mileage_name)
                c3.metric("與座標距離", f"{dist_m:.1f} 公尺")

                if dist_m > 200:
                    st.warning(f"⚠️ 距離過遠：您的座標距離「{mileage_name}」超過 {dist_m:.0f} 公尺。")
                else:
                    st.success(f"🎯 位置精準！最近的標記是 {mileage_name}")

                # 地圖視覺化
                st.write("#### 位置比對")
                map_data = pd.DataFrame({
                    'lat': [u_lat, result['lat']],
                    'lon': [u_lon, result['lon']],
                    'color': ['#ff0000', '#0000ff'], 
                    'size': [20, 20] 
                })
                # 將地圖也放在一個較窄的容器內
                col_map, _ = st.columns([5, 5])
                with col_map:
                    st.map(map_data, latitude='lat', longitude='lon', size='size', color='color', zoom=15)
    else:
        st.warning("請完成座標輸入。")

else:
    st.error("請確認您已在程式旁的 `/data` 資料夾中放入 KML 檔案。")