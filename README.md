# 🔌 Distribuție Oltenia - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg)

Integrare custom pentru Home Assistant care permite monitorizarea consumului de energie electrică prin portalul [Distribuție Oltenia](https://portal.distributieoltenia.ro).

---

## ✨ Funcționalități

- 📊 **Index Energie Activă** - Vizualizare index curent (kWh)
- ☀️ **Producție Activă** - Pentru prosumatori cu panouri solare
- 📈 **Istoric Consum** - Date istorice de consum
- 🔄 **Actualizare Automată** - Refresh la fiecare 6 ore

---

## 📋 Cerințe

- Home Assistant 2024.1 sau mai nou
- Cont activ pe [portal.distributieoltenia.ro](https://portal.distributieoltenia.ro)
- Python 3.11+

---

## 🚀 Instalare

### Metoda 1: Manual

1. Descarcă ultima versiune din [Releases](../../releases)
2. Copiază folderul `custom_components/distributie_oltenia` în:

   ```bash
   /config/custom_components/distributie_oltenia/
   ```

3. Restartează Home Assistant

### Metoda 2: HACS (Custom Repository)

1. Deschide HACS → Integrations
2. Click pe cele 3 puncte (⋮) → Custom repositories
3. Adaugă URL-ul acestui repository
4. Caută "Distribuție Oltenia" și instalează

---

## 🔑 Obținere Token

> ⚠️ **Important**: Token-ul este necesar pentru funcționarea integrării!

### Pași

1. **Accesează portalul** în browser:

   ```bash
   https://portal.distributieoltenia.ro
   ```

2. **Autentifică-te** cu credențialele tale

3. **Navighează** la pagina "Istoric indecsi si consum":
   - Click pe locația ta de consum
   - Click pe butonul verde **"Istoric indecsi si consum"**

4. **Copiază token-ul** din bara de adrese:

   ```bash
   https://portal.distributieoltenia.ro/pages/istoricIndecsi?token=eyJfX21ldGFk...
   ```

   Copiază totul după `token=` (textul care începe cu `eyJ`)

### Metodă Alternativă (View Source)

1. Pe pagina "Istoric indecsi", apasă `Ctrl+U`
2. Caută `token=eyJ` folosind `Ctrl+F`
3. Copiază token-ul găsit

---

## ⚙️ Configurare

1. **Settings** → **Devices & Services** → **+ Add Integration**
2. Caută **"Distribuție Oltenia"**
3. Completează:

| Câmp | Descriere | Obligatoriu |
| :--- | :--- | :---: |
| Email | Email-ul de pe portal | ✅ |
| Password | Parola de pe portal | ✅ |
| POD | Codul POD (23 cifre) | ❌ |
| Token | Token-ul copiat (vezi mai sus) | ✅ |

---

## 📊 Senzori

După configurare, vor fi disponibili următorii senzori:

| Entitate | Descriere | Unitate |
| :--- | :--- | :--- |
| `sensor.deo_energie_activa_XXXXX` | Index curent energie consumată | kWh |
| `sensor.deo_productie_activa_XXXXX` | Energie produsă (prosumatori) | kWh |

> **Notă**: `XXXXX` = numărul de serie al contorului tău

### Atribute senzori

- `reading_date` - Data ultimei citiri
- `consumption` - Consumul în perioada curentă (kWh)
- `meter_serial` - Seria contorului
- `reading_type` - Tipul citirii

## 🔧 Depanare

### "Token discovery failed"

✅ Soluție: Introdu token-ul manual în configurare (vezi [Obținere Token](#-obținere-token))

### "500 Server Error"

✅ Soluție: Token-ul poate fi invalid. Obține unul nou din browser.

### Senzori fără date

✅ Soluție: Așteaptă 6 ore pentru prima actualizare sau forțează refresh din Developer Tools.

---

## ❓ FAQ

### Token-ul expiră?

**Nu în mod normal.** Token-ul conține datele tale de cont (POD, adresă) și rămâne valid atâta timp cât nu îți schimbi informațiile de cont.

### Cât de des se actualizează datele?

**La fiecare 6 ore.** Poți modifica intervalul în `__init__.py` (variabila `update_interval`).

### Funcționează pentru prosumatori?

**Da!** Dacă ai panouri solare, vei vedea și senzorul de producție.

---

## 📄 Licență

Acest proiect este licențiat sub [MIT License](LICENSE).

---

## 🤝 Contribuții

Contribuțiile sunt binevenite! Deschide un [Issue](../../issues) sau trimite un [Pull Request](../../pulls).

---

Made with ❤️ for the Home Assistant community
