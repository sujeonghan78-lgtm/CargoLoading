import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import copy

# --- 1. 기본 클래스 정의 (Classes) ---

class Item:
    def __init__(self, id, name, length, width, height, weight, color=None, description="", stackable=True):
        self.id = id
        self.name = name
        self.length = float(length)
        self.width = float(width)
        self.height = float(height)
        self.weight = float(weight)
        self.volume = self.length * self.width * self.height
        self.position = None
        self.rotation_type = 0 # 0: 0도, 1: 90도
        self.color = color if color else f'rgb({np.random.randint(150, 250)}, {np.random.randint(150, 250)}, {np.random.randint(150, 250)})'
        self.description = description 
        self.stackable = stackable

    def get_dimension(self):
        if self.rotation_type == 0:
            return self.length, self.width, self.height
        else:
            return self.width, self.length, self.height

class Tower:
    """여러 아이템이 수직으로 쌓인 형태를 나타내는 클래스"""
    def __init__(self, base_item):
        self.items = [base_item]
        self.length = base_item.length
        self.width = base_item.width
        self.height = base_item.height
        self.weight = base_item.weight
        self.rotation_type = 0 # Tower 전체의 회전

    def add_item(self, item):
        self.items.append(item)
        self.height += item.height
        self.weight += item.weight
    
    def get_dimension(self):
        if self.rotation_type == 0:
            return self.length, self.width, self.height
        else:
            return self.width, self.length, self.height

class Vehicle:
    def __init__(self, name, length, width, height, max_weight):
        self.name = name
        self.length = float(length)
        self.width = float(width)
        self.height = float(height)
        self.max_weight = float(max_weight)
        self.items = [] # Packed items (with positions)

    def pack_items(self, items_to_pack, allow_rotation=True, allow_stacking=True, sort_by_weight=False):
        # 1. 정렬 (Sorting)
        # 무게 우선 옵션이 켜져 있으면 무게(내림차순) -> 부피(내림차순)
        if sort_by_weight:
            sorted_items = sorted(items_to_pack, key=lambda x: (x.weight, x.volume), reverse=True)
        else:
            sorted_items = sorted(items_to_pack, key=lambda x: x.volume, reverse=True)
        
        # 2. 타워 생성 (Grouping into Towers)
        towers = []
        used_indices = set()
        
        for i, item_i in enumerate(sorted_items):
            if i in used_indices:
                continue
            
            # 기본 타워 생성 (바닥에 놓일 아이템)
            current_tower = Tower(item_i)
            used_indices.add(i)
            
            if allow_stacking and item_i.stackable:
                # 이 위에 쌓을 수 있는 아이템 찾기 (Greedy)
                while True:
                    best_match_idx = -1
                    
                    for j in range(i + 1, len(sorted_items)):
                        if j in used_indices: continue
                        
                        item_j = sorted_items[j]
                        if not item_j.stackable: continue
                        
                        # 높이 체크
                        if current_tower.height + item_j.height > self.height:
                            continue
                        
                        # 무게 체크 (타워 전체 무게가 차량 허용 하중을 넘지 않는지 - 단순 체크)
                        if current_tower.weight + item_j.weight > self.max_weight:
                            continue

                        # 규격 체크 (L, W가 같아야 함)
                        # Case A: 둘 다 회전 안 함 (L=L, W=W)
                        if item_i.length == item_j.length and item_i.width == item_j.width:
                            item_j.rotation_type = 0 
                            best_match_idx = j
                            break
                        # Case B: 둘 다 회전 함 (L=W, W=L) - 여기서는 Base 기준 90도 회전 시 일치하는지 확인
                        elif item_i.length == item_j.width and item_i.width == item_j.length:
                             item_j.rotation_type = 1 
                             best_match_idx = j
                             break
                    
                    if best_match_idx != -1:
                        current_tower.add_item(sorted_items[best_match_idx])
                        used_indices.add(best_match_idx)
                    else:
                        break # 더 이상 쌓을 게 없음
            
            towers.append(current_tower)

        # 3. 타워 배치 (Packing Towers)
        unpacked_items = []
        current_weight = 0
        
        current_x = 0
        current_y = 0
        row_max_width = 0
        
        for tower in towers:
            if current_weight + tower.weight > self.max_weight:
                continue 
            
            placed = False
            rotations = [0]
            if allow_rotation:
                rotations.append(1)
            
            for rot in rotations:
                tower.rotation_type = rot
                l, w, h = tower.get_dimension()
                
                # Shelf 알고리즘
                if current_x + l <= self.length and current_y + w <= self.width:
                    pass
                elif current_y + w <= self.width:
                    current_x = 0
                    current_y += row_max_width
                    row_max_width = 0
                    if current_y + w > self.width:
                        continue
                else:
                    continue
                
                if current_x + l <= self.length and current_y + w <= self.width:
                    # 배치 성공
                    current_z_in_tower = 0
                    for item in tower.items:
                        # 아이템 회전 설정 (타워 회전 + 자체 회전 보정)
                        # 단순화를 위해 타워 회전값만 적용 (위에서 L=L, W=W만 묶었으므로)
                        # 만약 90도 돌려서 묶은 경우(Case B)는 추가 로직이 필요하지만, 
                        # 여기서는 간단히 타워 회전값을 따르게 함.
                        item.rotation_type = tower.rotation_type
                        if item.rotation_type == 1 and item.length != tower.width:
                             # 타워가 90도 돌았는데 아이템이 원래 L,W였다면... 
                             # 복잡한 케이스는 생략하고, 시각적으로는 타워 박스 안에 들어감.
                             pass

                        il, iw, ih = item.get_dimension()
                        
                        item.position = (current_x, current_y, current_z_in_tower)
                        self.items.append(item)
                        current_z_in_tower += ih
                    
                    current_weight += tower.weight
                    current_x += l
                    row_max_width = max(row_max_width, w)
                    placed = True
                    break
            
            if not placed:
                pass # 배치 실패
        
        # 적재 안 된 아이템 찾기
        packed_ids = set(item.id for item in self.items)
        unpacked_items = [item for item in items_to_pack if item.id not in packed_ids]
        
        return unpacked_items

# --- 2. Streamlit UI 설정 ---

st.set_page_config(page_title="화물 적재 시뮬레이터", layout="wide")
st.title("🚛 화물 적재 최적화 및 차량/컨테이너 추천 시뮬레이터")

# 세션 상태 초기화
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None
if 'best_sol' not in st.session_state:
    st.session_state.best_sol = None
if 'sim_mode' not in st.session_state:
    st.session_state.sim_mode = "화물차" 

# 사이드바
st.sidebar.header("⚙️ 시뮬레이션 설정")
mode = st.sidebar.radio("적재 모드 선택", ["화물차 (Truck)", "컨테이너 (Container)"], index=0 if st.session_state.sim_mode == "화물차" else 1)
st.session_state.sim_mode = "화물차" if "화물차" in mode else "컨테이너"

tab1, tab2 = st.tabs(["📦 화물 입력 및 시뮬레이션", "🚛 차량/컨테이너 제원 설정"])

# --- Tab 2: 제원 설정 ---
with tab2:
    st.subheader(f"{st.session_state.sim_mode} 제원 설정")
    st.info(f"표준 {st.session_state.sim_mode} 규격이 입력되어 있습니다. 필요시 수정하세요.")
    
    if st.session_state.sim_mode == "화물차":
        default_vehicles = pd.DataFrame([
            {"Type": "1톤 카고", "Length": 2800, "Width": 1600, "Height": 1700, "MaxWeight": 1000},
            {"Type": "1.4톤 카고", "Length": 3100, "Width": 1700, "Height": 1800, "MaxWeight": 1400},
            {"Type": "2.5톤 카고", "Length": 4300, "Width": 1800, "Height": 2100, "MaxWeight": 2500},
            {"Type": "5톤 카고", "Length": 6200, "Width": 2300, "Height": 2350, "MaxWeight": 5000},
            {"Type": "5톤 축차", "Length": 7400, "Width": 2300, "Height": 2350, "MaxWeight": 8000},
            {"Type": "11톤 카고", "Length": 9100, "Width": 2350, "Height": 2500, "MaxWeight": 11000},
            {"Type": "11톤 윙바디", "Length": 10200, "Width": 2400, "Height": 2500, "MaxWeight": 11000},
            {"Type": "추레라 (평판)", "Length": 12000, "Width": 2400, "Height": 2500, "MaxWeight": 25000},
        ])
    else: # 컨테이너
        default_vehicles = pd.DataFrame([
            {"Type": "20ft Dry", "Length": 5898, "Width": 2350, "Height": 2390, "MaxWeight": 21700},
            {"Type": "40ft Dry", "Length": 12032, "Width": 2350, "Height": 2390, "MaxWeight": 26700},
            {"Type": "40ft HC", "Length": 12032, "Width": 2350, "Height": 2698, "MaxWeight": 26400},
            {"Type": "20ft Flat Rack", "Length": 5600, "Width": 2200, "Height": 2200, "MaxWeight": 30000}, 
            {"Type": "40ft Flat Rack", "Length": 11600, "Width": 2200, "Height": 2000, "MaxWeight": 40000},
            {"Type": "20ft Open Top", "Length": 5890, "Width": 2340, "Height": 2340, "MaxWeight": 28000},
            {"Type": "40ft Open Top", "Length": 12020, "Width": 2340, "Height": 2340, "MaxWeight": 26000},
        ])
    
    edited_vehicles = st.data_editor(
        default_vehicles, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Length": st.column_config.NumberColumn(format="%d"),
            "Width": st.column_config.NumberColumn(format="%d"),
            "Height": st.column_config.NumberColumn(format="%d"),
            "MaxWeight": st.column_config.NumberColumn(format="%d"),
        },
        key=f"editor_{st.session_state.sim_mode}" 
    )

# --- Tab 1: 화물 입력 및 결과 ---
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("1. 화물 데이터 입력")
        st.caption("엑셀 패킹 리스트를 복사해서 붙여넣으세요.")
        
        default_cargo_data = pd.DataFrame([
            {
                "NO.": 1, "ITEM": "FILTER UNIT", "Loose": 1, "TAG.NO.": "PF250", "TYPE": "", 
                "WIDTH(mm)": 2400, "LENGTH(mm)": 1220, "HEIGHT(mm)": 1500, 
                "N.Weight": 717, "G.Weight": 850, "Stackable": True
            },
            {
                "NO.": 2, "ITEM": "UV UNIT", "Loose": 1, "TAG.NO.": "PL250(B)-Ex", "TYPE": "WOODEN BOX", 
                "WIDTH(mm)": 1600, "LENGTH(mm)": 800, "HEIGHT(mm)": 900, 
                "N.Weight": 290, "G.Weight": 330, "Stackable": True
            },
             {
                "NO.": None, "ITEM": None, "Loose": None, "TAG.NO.": None, "TYPE": None, 
                "WIDTH(mm)": None, "LENGTH(mm)": None, "HEIGHT(mm)": None, 
                "N.Weight": None, "G.Weight": None, "Stackable": True
            }
        ])
        
        edited_cargo_df = st.data_editor(
            default_cargo_data, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "NO.": st.column_config.NumberColumn(format="%d"),
                "ITEM": st.column_config.TextColumn(),
                "Loose": st.column_config.NumberColumn("Loose (수량)", format="%d"),
                "TAG.NO.": st.column_config.TextColumn(),
                "TYPE": st.column_config.TextColumn(),
                "WIDTH(mm)": st.column_config.NumberColumn(format="%d"),
                "LENGTH(mm)": st.column_config.NumberColumn(format="%d"),
                "HEIGHT(mm)": st.column_config.NumberColumn(format="%d"),
                "N.Weight": st.column_config.NumberColumn(format="%d"),
                "G.Weight": st.column_config.NumberColumn("G.Weight (총중량)", format="%d"),
                "Stackable": st.column_config.CheckboxColumn("적재 가능?", default=True),
            }
        )

    with col2:
        st.subheader("2. 옵션 및 실행")
        st.info(f"현재 모드: **{st.session_state.sim_mode}**")
        allow_rotation = st.checkbox("화물 회전 허용 (90도)", value=True)
        allow_stacking = st.checkbox("2단 적재 허용 (Stacking)", value=True, help="체크 시 동일한 규격(L, W)의 화물을 위로 쌓습니다.")
        sort_by_weight = st.checkbox("무거운 화물 우선 적재", value=True, help="체크 시 무거운 화물을 먼저(아래에) 배치합니다.")
        
        st.write("") 
        run_btn = st.button("🚀 시뮬레이션 시작", type="primary", use_container_width=True)

    st.divider()

    # --- 시뮬레이션 로직 ---
    if run_btn:
        all_items = []
        try:
            df_cleaned = edited_cargo_df.dropna(subset=['NO.'])
            df_cleaned = df_cleaned[df_cleaned['NO.'] != 0] 
            
            if df_cleaned.empty:
                st.warning("⚠️ 입력된 화물 데이터가 없습니다.")
                st.stop()

            df_processed = df_cleaned.replace(r'^\s*$', np.nan, regex=True).ffill()
            grouped = df_processed.groupby('NO.')
            
            for no_val, group in grouped:
                first_row = group.iloc[0]
                if pd.isna(first_row['WIDTH(mm)']) or pd.isna(first_row['LENGTH(mm)']) or pd.isna(first_row['HEIGHT(mm)']):
                    continue
                
                def clean_num(val):
                    if pd.isna(val) or val == "": return "0"
                    return str(val).replace(',', '')

                l = clean_num(first_row['LENGTH(mm)'])
                w = clean_num(first_row['WIDTH(mm)'])
                h = clean_num(first_row['HEIGHT(mm)'])
                weight = clean_num(first_row.get("G.Weight", 0))
                is_stackable = first_row.get("Stackable", True)
                
                item_names = group['ITEM'].dropna().astype(str).unique()
                full_desc = ", ".join(item_names)
                
                box_name = f"NO.{int(float(no_val))}"
                
                all_items.append(Item(
                    id=int(float(no_val)),
                    name=box_name,
                    length=l,
                    width=w,
                    height=h,
                    weight=weight,
                    description=full_desc,
                    stackable=is_stackable
                ))
            
            if not all_items:
                st.warning("⚠️ 유효한 화물 데이터가 없습니다.")
                st.stop()

            st.toast(f"✅ 총 {len(all_items)}개의 박스(NO.) 로딩 준비 완료")
            
        except Exception as e:
            st.error(f"데이터 처리 중 오류: {e}")
            st.stop()

        # 다중 차량 배차
        best_solution = None
        min_vehicles_needed = float('inf')
        simulation_results = []
        progress_bar = st.progress(0)
        total_v_types = len(edited_vehicles)
        
        # 규격 초과 검사
        max_v_l = edited_vehicles['Length'].max()
        max_v_w = edited_vehicles['Width'].max()
        max_v_h = edited_vehicles['Height'].max()
        max_v_weight = edited_vehicles['MaxWeight'].max()

        oversized_items = []
        for item in all_items:
            min_dim = min(item.length, item.width)
            if (min_dim > max_v_w and min_dim > max_v_l) or item.height > max_v_h or item.weight > max_v_weight:
                oversized_items.append(item)
        
        if oversized_items:
            st.error(f"❌ **적재 불가 화물 발견**: 다음 화물은 가장 큰 차량/컨테이너보다 큽니다.")
            for o_item in oversized_items:
                st.write(f"- {o_item.name}: {o_item.length}x{o_item.width}x{o_item.height}, {o_item.weight}kg")
            st.stop()

        for idx, v_row in edited_vehicles.iterrows():
            vehicle_type_name = v_row['Type']
            required_vehicles = []
            items_to_pack = copy.deepcopy(all_items)
            loop_limit = 50 
            
            while items_to_pack and len(required_vehicles) < loop_limit:
                try:
                    v = Vehicle(
                        f"{vehicle_type_name} #{len(required_vehicles)+1}", 
                        str(v_row['Length']).replace(',', ''), 
                        str(v_row['Width']).replace(',', ''), 
                        str(v_row['Height']).replace(',', ''), 
                        str(v_row['MaxWeight']).replace(',', '')
                    )
                except:
                    break
                
                unpacked = v.pack_items(items_to_pack, allow_rotation=allow_rotation, allow_stacking=allow_stacking, sort_by_weight=sort_by_weight)
                
                if len(v.items) > 0:
                    required_vehicles.append(v)
                    items_to_pack = unpacked 
                else:
                    break
            
            if len(items_to_pack) == 0: 
                simulation_results.append({
                    "차종": vehicle_type_name,
                    "필요대수": len(required_vehicles),
                    "차량목록": required_vehicles
                })
                
                if len(required_vehicles) < min_vehicles_needed:
                    min_vehicles_needed = len(required_vehicles)
                    best_solution = simulation_results[-1]
            
            progress_bar.progress((idx + 1) / total_v_types)
        
        st.session_state.simulation_results = simulation_results
        st.session_state.best_sol = best_solution

    # --- 결과 표시 ---
    if st.session_state.simulation_results is not None:
        results = st.session_state.simulation_results
        best_sol = st.session_state.best_sol
        
        st.subheader("3. 시뮬레이션 결과")
        
        if not results:
            st.error(f"❌ 어떤 {st.session_state.sim_mode}로도 모든 화물을 적재할 수 없습니다.")
        else:
            results.sort(key=lambda x: x['필요대수'])
            if not best_sol: best_sol = results[0]
            
            st.success(f"🏆 추천: **{best_sol['차종']}** (총 **{best_sol['필요대수']}**대 필요)")
            
            st.divider()
            st.subheader("📦 3D 적재 시뮬레이션")
            
            vehicle_options = [v.name for v in best_sol['차량목록']]
            selected_vehicle_names = st.multiselect("확인할 대상 선택", options=vehicle_options, default=vehicle_options)
            selected_vehicles = [v for v in best_sol['차량목록'] if v.name in selected_vehicle_names]
            
            for target_vehicle in selected_vehicles:
                st.markdown(f"#### 🚛 {target_vehicle.name}")
                fig = go.Figure()
                L, W, H = target_vehicle.length, target_vehicle.width, target_vehicle.height
                
                # 프레임
                vx = [0, L, L, 0, 0, 0, L, L, 0, 0, 0, 0, L, L, L, L]
                vy = [0, 0, W, W, 0, 0, 0, W, W, 0, 0, W, W, 0, 0, W]
                vz = [0, 0, 0, 0, 0, H, H, H, H, H, 0, 0, 0, 0, H, H]
                fig.add_trace(go.Scatter3d(x=vx, y=vy, z=vz, mode='lines', line=dict(color='black', width=4), hoverinfo='none'))
                
                for item in target_vehicle.items:
                    ix, iy, iz = item.position
                    il, iw, ih = item.get_dimension()
                    
                    # Mesh
                    x = [ix, ix+il, ix+il, ix, ix, ix+il, ix+il, ix]
                    y = [iy, iy, iy+iw, iy+iw, iy, iy, iy+iw, iy+iw]
                    z = [iz, iz, iz, iz, iz+ih, iz+ih, iz+ih, iz+ih]
                    fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6], color=item.color, opacity=0.9, flatshading=True, name=item.name, hovertext=f"{item.name}<br>{item.description}<br>{il}x{iw}x{ih}", showlegend=False))
                    
                    # Wireframe
                    bx = [ix, ix+il, ix+il, ix, ix, ix, ix+il, ix+il, ix, ix, ix, ix, ix+il, ix+il, ix+il, ix+il]
                    by = [iy, iy, iy+iw, iy+iw, iy, iy, iy, iy+iw, iy+iw, iy, iy, iy+iw, iy+iw, iy, iy, iy+iw]
                    bz = [iz, iz, iz, iz, iz, iz+ih, iz+ih, iz+ih, iz+ih, iz+ih, iz, iz, iz, iz+ih, iz+ih, iz+ih]
                    fig.add_trace(go.Scatter3d(x=bx, y=by, z=bz, mode='lines', line=dict(color='white', width=1), showlegend=False, hoverinfo='skip'))
                    
                    # 라벨
                    fig.add_trace(go.Scatter3d(x=[ix + il/2], y=[iy + iw/2], z=[iz + ih/2], mode='text', text=[str(item.id)], textposition="middle center", textfont=dict(size=30, color='black', family="Arial Black"), showlegend=False, hoverinfo='skip'))
                
                fig.update_layout(scene=dict(xaxis=dict(title='Length', range=[0, max(L, 1000)]), yaxis=dict(title='Width', range=[0, max(W, 1000)]), zaxis=dict(title='Height', range=[0, max(H, 1000)]), aspectmode='data'), height=600, margin=dict(l=0, r=0, b=0, t=0))
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            with st.expander("📊 상세 적재 결과 보기"):
                summary_data = [{"차종": sol['차종'], "필요대수": sol['필요대수'], "비고": "추천" if sol == best_sol else ""} for sol in results]
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
                st.divider()
                
                detail_options = [res['차종'] for res in results]
                selected_detail_type = st.selectbox("상세 결과를 볼 차종 선택", options=detail_options)
                target_detail_sol = next((res for res in results if res['차종'] == selected_detail_type), None)
                
                if target_detail_sol:
                    st.markdown(f"**{target_detail_sol['차종']} 상세 적재 목록**")
                    for v in target_detail_sol['차량목록']:
                        st.caption(f"🚛 {v.name}")
                        d_col1, d_col2 = st.columns([1, 1])
                        with d_col1:
                            packed_items_data = [{"No.": item.id, "품명": item.description[:15] + "...", "규격": f"{item.length}x{item.width}x{item.height}", "회전": "O" if item.rotation_type == 1 else "X"} for item in v.items]
                            st.dataframe(pd.DataFrame(packed_items_data), use_container_width=True, height=300)
                        with d_col2:
                            fig = go.Figure()
                            L, W, H = v.length, v.width, v.height
                            vx = [0, L, L, 0, 0, 0, L, L, 0, 0, 0, 0, L, L, L, L]
                            vy = [0, 0, W, W, 0, 0, 0, W, W, 0, 0, W, W, 0, 0, W]
                            vz = [0, 0, 0, 0, 0, H, H, H, H, H, 0, 0, 0, 0, H, H]
                            fig.add_trace(go.Scatter3d(x=vx, y=vy, z=vz, mode='lines', line=dict(color='black', width=2), hoverinfo='none'))
                            for item in v.items:
                                ix, iy, iz = item.position
                                il, iw, ih = item.get_dimension()
                                x = [ix, ix+il, ix+il, ix, ix, ix+il, ix+il, ix]
                                y = [iy, iy, iy+iw, iy+iw, iy, iy, iy+iw, iy+iw]
                                z = [iz, iz, iz, iz, iz+ih, iz+ih, iz+ih, iz+ih]
                                fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6], color=item.color, opacity=0.9, flatshading=True, hoverinfo='none'))
                                bx = [ix, ix+il, ix+il, ix, ix, ix, ix+il, ix+il, ix, ix, ix, ix, ix+il, ix+il, ix+il, ix+il]
                                by = [iy, iy, iy+iw, iy+iw, iy, iy, iy, iy+iw, iy+iw, iy, iy, iy+iw, iy+iw, iy, iy, iy+iw]
                                bz = [iz, iz, iz, iz, iz, iz+ih, iz+ih, iz+ih, iz+ih, iz+ih, iz, iz, iz, iz+ih, iz+ih, iz+ih]
                                fig.add_trace(go.Scatter3d(x=bx, y=by, z=bz, mode='lines', line=dict(color='white', width=1), hoverinfo='none'))
                            fig.update_layout(scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), aspectmode='data'), height=300, margin=dict(l=0, r=0, b=0, t=0), showlegend=False)
                            st.plotly_chart(fig, use_container_width=True)
                        st.divider()
