Distribuție Oltenia Integration - Walkthrough
This document outlines the steps to install and configure the custom Home Assistant integration for Distribuție Oltenia.

Installation
Copy Files:

Copy the folder custom_components/distributie_oltenia to your Home Assistant config directory: /config/custom_components/.
Ensure the structure is /config/custom_components/distributie_oltenia/ containing __init__.py, manifest.json, etc.
Restart Home Assistant:

Go to Developer Tools > YAML > Check Configuration.
If valid, click Restart.
Configuration
Add Integration:

Go to Settings > Devices & Services.
Click + ADD INTEGRATION.
Search for "Distribuție Oltenia".
Authentication:

Enter your Email and Password.
Token (Optional): If the automatic connection fails, enter the token below.
Recovery Token
If the integration fails to connect automatically, copy and paste this token into the "Token" field during configuration:


Features
Sensors:
Active Energy (Index)
Active Production (for Prosumers)
Consumption History
Update Frequency: Calculated consumption and indexes are updated every 6 hours. stant
Am finalizat crearea integrării pentru portalul Distribuție Oltenia. Aceasta îți va permite să monitorizezi consumul de energie (și producția, if any) direct în Home Assistant.

Ce am implementat
custom_components/distributie_oltenia/: Integrarea completă pentru Home Assistant, care include:
Config Flow: Poți adăuga integrarea direct din interfața HA (Settings -> Integrations -> Add Integration).
Sensori: Creează automat senzori pentru Active Energy Consumption (1.8.0) și Active Energy Production (2.8.0).
Energy Dashboard: Senzorii sunt compatibili cu noul Energy Dashboard din Home Assistant.
Cum instalezi integrarea
Deoarece aceasta este o componentă personalizată (custom component), trebuie să urmezi acești pași:

Copiați fișierele:

Asigură-te că folderul distributie_oltenia (din custom_components) este copiat în folderul custom_components al instanței tale de Home Assistant (ex: /config/custom_components/distributie_oltenia/).
Atenție: Fișierul deo_portal.py trebuie să fie fie în același folder cu integrarea, fie într-un loc unde Python îl poate găsi (am configurat integrarea să îl caute în folderul părinte sau local).
Restart Home Assistant:

După ce ai copiat fișierele, restartează Home Assistant.
Configurare UI:

Mergi la Settings -> Devices & Services.
Apasă pe Add Integration.
Caută Distribuție Oltenia.
Introdu email-ul și parola folosite pe portal.
Testare și Validare
Poți testa scriptul de bază direct în terminal pentru a te asigura că datele sunt extrase corect:

python deo_portal.py
(Va cere email și parolă și va afișa JSON-ul brut dacă totul e OK).

Rezultate Așteptate în HA
Senzor: sensor.deo_active_energy_consumption
Senzor: sensor.deo_active_energy_production (dacă ai date de producție)
Atribute: POD, Seria contorului, Data ultimei citiri.
NOTE

Am setat intervalul de actualizare la 6 ore, deoarece portalul nu actualizează datele în timp real.
