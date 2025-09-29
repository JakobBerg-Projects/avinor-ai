import streamlit as st
import pandas as pd
import plotly.express as px

# Last inn prediksjonene
pred_out = pd.read_csv("../data/prediction_data/predict_oct2025_with_proba.csv")
st.set_page_config(layout="wide")
# Lag datetime for filtrering
pred_out["datetime"] = pd.to_datetime(pred_out["date"]) + pd.to_timedelta(pred_out["hour"], unit="h")

# --- Velg dato ---
dates = sorted(pred_out["date"].unique())
selected_date = st.selectbox("Velg dato", dates)

# --- Velg time ---
selected_hour = st.slider("Velg time", 0, 23, 12)

# Finn valgt tidspunkt
selected_time = pd.to_datetime(selected_date) + pd.to_timedelta(selected_hour, unit="h")

# Filtrer data
df_filtered = pred_out[pred_out["datetime"] == selected_time]

# --- Layout med to kolonner ---
col1, col2 = st.columns([2,3])  # venstre bredere nå

with col1:
    st.image("../report/visualizations/airport-map.png", caption="Flyplasskart", use_container_width=True)

with col2:
    fig = px.bar(df_filtered, x="airport_group", y="pred",
                 title=f"Predikert samtidighet {selected_time}",
                 labels={"pred": "Predikert sannsynlighet", "airport_group": "Flyplassgruppe"},
                 range_y=[0,1],
                 category_orders={"airport_group": ["A","B","C","D","E","F","G"]})
    
    st.plotly_chart(fig, use_container_width=True)
