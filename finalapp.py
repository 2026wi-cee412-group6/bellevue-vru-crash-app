# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 13:10:45 2026

@author: ekchen
"""

import streamlit as st
import pandas as pd
import pydeck as pdk

# 1. Page Config
st.set_page_config(page_title="Bellevue VRU Safety Dashboard", layout="wide")

st.title("🚲 City of Bellevue VRU Safety & Corridor Analysis")
st.markdown("Created by Ethan Chen🪰, Olivia Lee😺, Tin Vo🥫")
st.markdown("Comprehensive analysis of crashes involving vulnerable road users (pedestrians & cyclists) in the City of Bellevue (2022-2024)")

# 2. Unified Data Function (Fact & Dimension logic)
@st.cache_data
def get_vru_data():
    # Load raw data
    df = pd.read_csv('bellevue_crashes.csv', encoding='latin1', skiprows=5)
    df.columns = df.columns.str.strip()
    
    # Filter for VRU only
    df = df[(df['PedestrianCount'] > 0) | (df['PedalcyclistCount'] > 0)].copy()

    # Create Dimension: Locations
    loc_cols = ['PrimaryTrafficway', 'IntersectingTrafficway', 'Latitude', 'Longitude', 'CityName']
    locations = df[loc_cols].drop_duplicates().reset_index(drop=True)
    locations['LocationID'] = locations.index + 1

    # Create Fact: Crashes
    # We keep more attributes here for analysis
    df = df.merge(locations, on=loc_cols, how='left')
    crashes = df[[
        'ReportNumber', 'LocationID', 'PedestrianCount', 
        'PedalcyclistCount', 'MostSevereInjuryType'
    ]].rename(columns={'ReportNumber': 'CrashID'})

    # Merge for Map & Corridor Display
    full_data = crashes.merge(locations, on='LocationID')
    full_data = full_data.rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
    
    # Data Cleaning
    full_data['lat'] = pd.to_numeric(full_data['lat'], errors='coerce')
    full_data['lon'] = pd.to_numeric(full_data['lon'], errors='coerce')
    full_data['weight'] = 1 
    
    return full_data.dropna(subset=['lat', 'lon'])

try:
    data = get_vru_data()

    # --- SIDEBAR: Controls ---
    st.sidebar.header("Map & Chart Controls")
    map_type = st.sidebar.radio("Select Map View", ["Heatmap (Density)", "Point Map (Exact Locations)"])
    
    top_n = st.sidebar.slider("Number of Corridors to Show", 5, 20, 10)

    # --- TOP ROW: Key Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total VRU Crashes", len(data))
    m2.metric("Peds Involved", int(data['PedestrianCount'].sum()))
    m3.metric("Cyclists Involved", int(data['PedalcyclistCount'].sum()))
    
    # Calculate a "Danger Score" (e.g., total people involved)
    danger_score = int(data['PedestrianCount'].sum() + data['PedalcyclistCount'].sum())
    m4.metric("Total People Impacted", danger_score)

    # --- MIDDLE ROW: Maps & Charts ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader(f"VRU Incident {map_type}")
        
        view_state = pdk.ViewState(latitude=47.6101, longitude=-122.2015, zoom=12, pitch=0)

        if map_type == "Heatmap (Density)":
            layer = pdk.Layer(
                "HeatmapLayer",
                data=data,
                get_position='[lon, lat]',
                get_weight='weight',
                radius_pixels=35,
                opacity=0.8,
            )
        else:
            # Scatterplot (Point Map) Layer
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=data,
                get_position='[lon, lat]',
                get_color='[200, 30, 0, 160]', # Red points
                get_radius=80,
                pickable=True
            )

        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_provider="carto", 
            map_style="light",
            tooltip={"text": "Crash ID: {CrashID}\nCorridor: {PrimaryTrafficway}"}
        ))

    with col_right:
        st.subheader("Top Dangerous Corridors")
        st.markdown("Streets with the highest frequency of VRU crashes.")
        
        # Corridor Analysis Logic
        corridor_counts = data['PrimaryTrafficway'].value_counts().head(top_n).reset_index()
        corridor_counts.columns = ['Street Name', 'Number of Crashes']
        
        # Display as Bar Chart
        st.bar_chart(corridor_counts.set_index('Street Name'))

    # --- BOTTOM ROW: Data Exploration ---
    with st.expander("Detailed Analysis Table"):
        st.dataframe(data[['CrashID', 'PrimaryTrafficway', 'IntersectingTrafficway', 'MostSevereInjuryType', 'PedestrianCount', 'PedalcyclistCount']])

except Exception as e:
    st.error(f"Something went wrong: {e}")