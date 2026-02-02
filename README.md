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
Update Frequency: Calculated consumption and indexes are updated every 6 hours.
