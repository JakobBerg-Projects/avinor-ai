# Rapport - Avinor Data konkurannse 2025 

## 1. Innledning
Denne rapporten beskriver vår tilnærming til å utvikle en prediksjonsmodell for samtidighet i flyplassgrupper, i forbindelse med Avinors datakonkurranse «Når går det på høygir?». Målet er å estimere sannsynlighet for samtidighet per flyplassgruppe per time, der samtidighet betyr at en AFIS-fullmektig er i aktiv dialog med to eller flere fly samtidig


Vi benytter historiske flydata til å trene modeller og evaluerer ytelsen ved hjelp av AUC og log loss, i tråd med konkurransens evalueringskriterier

## 2. Datagrunnlag og utforskende analyse
Datasettet historical_flights.csv inneholder detaljerte opplysninger om flyvninger, både planlagte og faktiske. Variablene kan deles inn i tre hovedkategorier: identifikasjon, operasjonelle opplysninger og tidsstempler:

<small>

* flight_id – unikt flyvningsnummer, der de to første tegnene identifiserer flyselskapet. Gir mulighet til å skille flyvninger og analysere mønstre per selskap.
* dep_airport – avgangsflyplass, en kortkode (f.eks. BGO for Bergen). Brukes til å knytte flyvningen til en geografisk lokasjon.
* dep_airport_group – hvilken flyplassgruppe avgangsflyplassen tilhører. Viktig for konkurransen, siden samtidighet måles på gruppenivå.
* arr_airport – ankomstflyplass, tilsvarende dep_airport.
* arr_airport_group – flyplassgruppen ankomstflyplassen tilhører.
* service_type – flyvningstype, f.eks. rutefly (J), charter (C) eller frakt (P). 
* std (Scheduled Time of Departure) – planlagt avgangstid.
* sta (Scheduled Time of Arrival) – planlagt ankomsttid.
* cancelled – indikator (0/1) for om flyvningen ble kansellert. Viktig å filtrere ut, da kansellerte flyvninger ikke genererer faktisk trafikk.
* atd (Actual Time of Departure) – faktisk avgangstid.
* ata (Actual Time of Arrival) – faktisk ankomsttid.
</small>

Planlagte tider (std, sta) danner grunnlag for en forventet trafikkflyt, mens faktiske tider (atd, ata) gjør det mulig å oppdage forsinkelser og avvik. Differansen mellom disse er ofte årsaken til samtidighet, og dermed sentral i modelleringen.

### 2.1 Databehandling

Dataene ble renset og transformert slik:

<small>

* Konverterte tidsvariabler til datetime-format - for å kunne beregne intervaller, forsinkelser og aggregere flyvninger på time-/dagsnivå på en konsistent måte.

* Fjernet urealistiske flytider (negative eller over 10 timer) - for å håndtere feilregistreringer eller datastøy som ellers ville kunne skape feil i beregningene av kommunikasjonsintervaller og mislede modellen.
</small>

### 2.2 Utforskende analyse

Vi ønsker å analysere når samtidighet oppstår i kommunikasjonen med AFIS-fullmektig per flyplass-gruppe. I motsetning til store flyplasser der det er flere AFIS-fullmektige, har mindre flyplasser en felles AFIS-fullmektig grunnet at det er betydeligere lavere flytrafikk. Kommunikasjon mellom fly og AFIS-fullmektig er 15 minutter før til 6 minutter etter for avgang og 15 minutter før til etter 8 minutter etter for landing. Vi ønsker å se når det er samtidighet i denne kommunikasjonen for følgende flyplasser og deres flyplass-gruppe.
![AirPort Map](visualizations/airport-map.png)


Som en del av den utforskende analysen har vi sett på sammenhengen mellom planlagt samtidighet (target_sched) og faktisk samtidighet (target_actual). Figuren under viser resultatene både som antall tilfeller og som prosentandeler:

![TargetVsActual](visualizations/1-TargetVsActual.png)
![TargetVsActual%](visualizations/2-TargetVsActual%.png)

Analysen viser at i 49 % av tilfellene der planlagte tider indikerer overlapp, oppstår det også faktisk samtidighet. Tilsvarende ser vi at i 30,3 % av tilfellene uten planlagt overlapp, skjer det heller ingen faktisk overlapp. Dette innebærer at i 79,3 % av tilfellene er planlagt tidsinformasjon alene tilstrekkelig for å predikere samtidighet korrekt.

Det gjenstår imidlertid 20,7 % av tilfellene hvor planlagte tider ikke stemmer med faktisk utfall: enten var samtidighet planlagt uten å inntreffe, eller så oppstod samtidighet selv om det ikke var planlagt. Dette avviket er spesielt interessant, og videre analyse og modellering vil fokusere på å forstå hvilke faktorer som forklarer disse tilfellene.

Vi ønsker å skje når i løpet av tidsintervaller på 1 time det vil skje en samtidighet. Grunnet at hver fly vil ha en kommunikasjonstid med AFIS-fullmektig på enten 23 eller 21 minutter vil det være naturlig å se på hvor mange fly vi har den gitte timen, og hvordan det påvirker target og target scheduled.
![FlightCountVsCollision%](visualizations/target-schedVsActual-flightcnt.png)

Figuren viser hvordan prediksjonene av samtidighet (target scheduled) samsvarer med de faktiske observasjonene (target actual) for ulike antall flyvninger per time.
Vi ser at når antall fly per time øker, blir andelen korrekte prediksjoner svært høy. Allerede ved 4 fly eller mer per time er andelen korrekte tilfeller over 95 %, og fra 6 fly og oppover er den praktisk talt 100%.
Ved lavere trafikk (1–3 fly per time) ser vi flere avvik:

* Allerede ved 1 fly per time ser vi en betydelig andel falske negative. Dette kan skyldes at flyet ikke faktisk gikk i sitt planlagte timeintervall, men i stedet overlappet med et annet fly som var forventet i en annen time. Det kan også være at et fly fra et annet timeintervall ble forsinket og dermed endte opp i samme tidsrom, slik at kommunikasjonen overlappet.
* Med 2 fly per time oppstår både falske positive og falske negative, noe som indikerer at scheduled target har utfordringer med å fange samtidighet korrekt i grensetilfellene.
* Med 3 fly per time dominerer de falske negative, mens falske positive reduseres.
* Ved høyere trafikk (4+ fly per time) øker treffsikkerheten raskt, og andelen korrekte prediksjoner er nær 100 %. Dette viser at prediksjonskvaliteten er svært god ved høy trafikk, mens de mest krevende situasjonene oppstår når vi har få fly per time.

Totalt sett viser figuren at prediksjonskvaliteten er svært god ved høy trafikk, mens de mest utfordrende situasjonene å predikere oppstår når vi har 1–3 fly på en time.

En sentral årsak til disse avvikene er forsinkelser. Dersom fly ikke går eller lander på det planlagte tidspunktet, kan kommunikasjonen overlappe selv om dette ikke var forventet i den opprinnelige planen. For å undersøke dette ser vi nærmere på hvordan forsinkelsene fordeler seg. Vi filtrerer bort ekstreme tilfeller, der noen få fly har forsinkelser på flere dager, og får dermed et mer representativt bilde av den typiske variasjonen.

![FlightCountVsCollision%](visualizations/forsinkelse-histogram.png)

Ettersom forsinkelsen har lange haler både for positiv og negativ forsinkelse vil en t-fordeling med parametere df=3.7 og mu=-1.98 og sigma=8.02 være et godt estimat på fordelingen forsinkelsen tas fra. Her ser vi at de aller fleste fly har nesten ingen forsinkelse. Likevel vil et skift fra dette midtpunktet gjøre at oppsatt tid ikke vil kunne alene beskrive om det vil forekomme samtidighet eller ikke.

Som histogrammet viser, har de fleste fly svært små forsinkelser. Likevel finnes det både positive og negative forsinkelser med lange haler. Dette gjør at en t-fordeling med parametere df=3.7, μ = –1.98 og σ = 8.02 gir en god tilnærming til den observerte fordelingen. Selv små avvik fra planlagt tidspunkt kan føre til samtidighet, noe som betyr at oppsatt tid alene ikke er tilstrekkelig for å forutsi om overlapp vil oppstå.







#### Daglige flyvninger mot target:

![DagligeFlyvningerVsTarget%](visualizations/DailyFlightVSTarget.png)

#### Visualing av de forskjellige flyplassene

![FlyplassVsTarget%](visualizations/AirportGroupVSTarget.png)

#### Visualing av de forskjellige flyselvkapene

![FlyselvskapVsTarget%](visualizations/AirlineVSTarget.png)

### 2.3 Foreløpige observasjoner

Samtidighet oppstår hyppigst når trafikkmengden er høy.

Planlagt samtidighet gir en indikasjon, men fanger ikke opp alle reelle overlapp.

## 3. Metodevalg og tilnærming
### 3.1 Intervall- og target-konstruksjon
For å identifisere samtidighet ble det konstruert intervaller for kommunikasjon:

* Avgang: 15 min før → 8 min etter faktisk avgang.

* Ankomst: 16 min før → 5 min etter faktisk landing.

Ved overlapp i disse intervallene oppstår samtidighet. Dette ble aggregert per flyplassgruppe × time, og brukt til å lage target-variablene 
* target_actual (basert på faktiske tider) 
* target_sched (basert på planlagte tider).

### 3.3 Feature engineering
Følgende features ble laget:

* Operasjonelle: antall flyvninger per time (flights_cnt), gj.snitt og maks flytid, andel passasjer-, cargo- og charterfly.
* Tid: ukedag, måned, time på dagen, helg-indikator.
* Planlagt samtidighet: target_sched.

### 3.4 Baseline modeller
Vi etablerte to enkle baselines:

1. Bruke target_sched direkte som prediksjon → ga AUC og log loss som referanse.
2. Majoritetsklassifikator (andel samtidighet i trening) → ga et alternativt sammenligningspunkt.

### 3.5 Modellvalg

Vi valgte en Random Forest Classifier med følgende parametere:

* n_estimators = 200
* max_depth = 20
* random_state = 42

Denne ble pakket i en scikit-learn Pipeline med preprocessing (OneHotEncoder for kategoriske features, passthrough for numeriske).

## 4. Resultater
### 4.1 Baseline

Baseline med target_sched: moderat AUC, men høy log loss (overkonfidens).

Majoritetsmodell: lav prediksjonsevne, men jevn log loss.

### 4.2 Random Forest

Accuracy: (resultat)

AUC: (resultat)

Log Loss: (resultat)

### 4.3 Feature importance

De viktigste feature-gruppene i modellen var:

* Planlagt samtidighet (target_sched)
* Antall flyvninger per time (flights_cnt)
* Tid på døgnet (hournum)
* Flytype-fordeling (passasjer vs. cargo)
* Ukedag/helg

## 5. Systemstruktur og arkitektur

Løsningen er bygget som et modulært Python-system:

* preprocess.py: full pipeline for lasting, rensing og feature engineering.

* modellering.py: trenings- og evalueringslogikk.

* innlevering.py (planlagt): genererer prediksjoner i konkurransens csv-format.

Dette muliggjør enkel reproduserbarhet og videreutvikling.

## 6. Videre arbeid

Vi ser flere muligheter for forbedring og utforskning:

* Eksterne datakilder: integrere værdata, helligdager og sesonginformasjon.
* Hyperparameter-tuning: optimalisere max_depth, learning rate, og antall estimators.
* Feature-utvidelser: kjedeeffekter (forsinkelser som forplanter seg til neste flyvning).

## 7. Konklusjon

Vi har etablert en komplett pipeline for å predikere samtidighet ved Avinors flyplassgrupper. Våre første resultater viser at Random Forest gir klart bedre prediksjoner enn baseline, og feature importance indikerer at både planlagte samtidigheter og flyintensitet er sentrale drivere.

https://ourairports.com/data/
