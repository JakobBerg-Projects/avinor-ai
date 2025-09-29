# Avinor Datakonkurranse 2025 – Prediksjon av samtidighet

Dette prosjektet er laget i forbindelse med Avinors datakonkurranse **«Når går det på høygir?»**.  
Målet er å utvikle en maskinlæringsmodell som kan predikere sannsynligheten for samtidighet i kommunikasjon mellom fly og AFIS-fullmektige.  

Prosjektet består av dataforberedelse, feature engineering, modelltrening, evaluering og en enkel Streamlit-app for visualisering av resultater.

For en fullstendig beskrivelse av metode, analyser og resultater:
[Se rapporten her](report/report.pdf)

## 📂 Prosjektstruktur

avinor-ai/
|
|-- data/
|   |-- raw_data/              # Originale data fra Avinor (+ airports.csv fra https://ourairports.com/data/)
|   |-- processed_data/        # Ferdig bearbeidede data (train/val/test/predict_oct2025)
|   |-- prediction_data/       # Modellens prediksjoner
|   \-- konkurranse_info/      # Informasjon om konkurransen
|
|-- notebooksExperimental/     # Utforskning, ikke del av endelig løsning
|   |-- 02-eda-jakob.ipynb     # Eksperimentell utforskning
|   |-- 02-eda-tobias.ipynb    # Eksperimentell utforskning
|   \-- 03-visualizations.ipynb# Endelige visualiseringer
|
|-- report/
|   |-- visualizations/        # Visualiseringer brukt i rapporten (png)
|   |-- report.md              # Rapport i markdown
|   \-- report.pdf             # Ferdig rapport i PDF
|
|-- src/
|   |-- preprocessing.ipynb    # Dataprosessering
|   |-- model.ipynb            # Modellering
|   \-- app.py                 # Streamlit-app for interaktiv visualisering
|
|-- requirements.txt           # Avhengigheter
\-- README.md                  # Denne filen

```mermaid
flowchart TD
    A[Raw data (historical_flights.csv)] -->|Cleaning| B[preprocessing.py]
    B --> C[Feature engineering]
    C --> D[Model training (Random Forest, XGBoost)]
    D --> E[Evaluation metrics: AUC, Log Loss]
    D --> F[Prediction files (CSV)]
    F --> G[Streamlit app (app.py)]
    G --> H[Interactive visualization of concurrency]
```

## ⚙️ Installasjon

1. Klon repoet:
   ```bash
   git clone <repo-url>
   cd avinor-ai
   ```

2. Opprett og aktiver miljø:
    ```bash
    conda create -n avinor-ml python=3.13
    conda activate avinor-ml
    ```

3. Installer avhengigheter:
    ```bash
    pip install -r requirements.txt
    ```

## Bruk
1. Preprocessing og modelltrening
    1. Kjør preprocessing.ipynb
    2. Kjøre model.ipynb

2. Valgfritt: Kjør Streamlit-app
    ```bash
    streamlit run src/app.py
    ```

## Metode
- **Features:** antall fly per time, planlagt samtidighet, forsinkelsesvariabler, tid/dato, flytypefordeling  
- **Modeller:** Random Forest, XGBoost  
- **Hyperparameter-tuning:** RandomizedSearchCV (HalvingGridSearchCV ble testet uten gevinst)  
- **Evalueringsmetrikker:** ROC AUC og Log Loss  
- **Beste modell:** XGBoost, valgt som endelig innsending  

## App
Vi har utviklet en interaktiv Streamlit-app som gjør det mulig å utforske prediksjonene på en intuitiv måte.
Appen visualiserer sannsynligheten for samtidighet per flyplassgruppe, og lar brukeren enkelt navigere i dataene gjennom ulike kontroller.
Hovedfunksjonalitet
Tidspunkt-valg:
* Brukeren kan velge dato via en sjekkboks eller dropdown.
* Brukeren kan velge time via en slider.
Visualisering:
* Et interaktivt stolpediagram (Plotly) viser predikert sannsynlighet for samtidighet (pred) for hver flyplassgruppe.
* Verdiene normaliseres til intervallet [0,1], slik at sannsynligheten er lett å tolke.
Kartvisning:
* Et statisk kartbilde av flyplassgruppene plasseres på venstre side av skjermen for å gi en geografisk kontekst.
* Diagrammet oppdateres til høyre basert på valgt tidspunkt.

![Streamlit-app](report/visualizations/Streamlit.png)


## Videreutvikling og skalering
* Legge til mer detaljerte værdata (vind, sikt, nedbør).
* Teste andre modeller som ElasticNet eller Neural Networks.
* Optimalisere XGBoost med større hyperparameter-søk.
* Integrere systemet direkte mot sanntidsdata fra Avinor API (hvis tilgjengelig).


## Bidragsytere
Prosjekt utviklet av:
Jakob Brekke Berg
Jonas Mathisen Sterud
Tobias Munch
Universitetet i Bergen, 2025.

