# HeroAI Backup Folder

Ovaj folder čuva verziovane bekape ključnih fajlova vezanih za HeroAI behavior tree i follow logiku.

## Struktura

- `HeroAI_v1_follow_bt_foundation.py`
  - Kopija `Widgets/HeroAI.py` u trenutku kada je:
    - uveden behavior tree za follow (`HeroAI/bt.py`, `HeroAI/follow_bt.py`),
    - follow BT tikuje ~3 puta u sekundi preko `ThrottledTimer(333)`,
    - postoji deadzone za kretanje (oko 120 range) i `CanFollowNode` preuslov.
- `follow_bt_v1.py`
  - Kopija `HeroAI/follow_bt.py` odgovarajuća verziji `HeroAI_v1_follow_bt_foundation.py`.
- `bt_v1.py`
  - Kopija `HeroAI/bt.py` (BT framework sa `ConditionNode.check/execute`).

- `HeroAI_v2_follow_bt_antistuck.py`
  - Snapshot `Widgets/HeroAI.py` u trenutku kada je dodat anti-stuck u `FollowNode`.
- `follow_bt_v2.py`
  - Snapshot `HeroAI/follow_bt.py` sa anti-stuck logikom i poboljšanim `CanFollowNode`.
- `bt_v2.py`
  - Snapshot `HeroAI/bt.py` (isto kao v1 u ovom trenutku, dodato radi konzistentnosti verzija).

> Napomena: trenutna `HeroAI.py` iz `Widgets/` nije direktno učitana iz ovog foldera. Ovo su samo bekapi.

## Kako vratiti v1 verziju

Ako želimo da se vratimo na ovu stabilnu verziju (v1):

1. **Zameni glavnu HeroAI skriptu**
   - Prekopiraj `HeroAI_backup/HeroAI_v1_follow_bt_foundation.py` u:
     - `Widgets/HeroAI.py`

2. **Zameni follow BT modul**
   - Prekopiraj `HeroAI_backup/follow_bt_v1.py` u:
     - `HeroAI/follow_bt.py`

3. **Zameni BT framework**
   - Prekopiraj `HeroAI_backup/bt_v1.py` u:
     - `HeroAI/bt.py`

## Kako vratiti v2 verziju (follow BT + anti-stuck)

Ako želimo da se vratimo na v2 (follow BT sa anti-stuck logikom):

1. **Zameni glavnu HeroAI skriptu**
   - Prekopiraj `HeroAI_backup/HeroAI_v2_follow_bt_antistuck.py` u:
     - `Widgets/HeroAI.py`

2. **Zameni follow BT modul**
   - Prekopiraj `HeroAI_backup/follow_bt_v2.py` u:
     - `HeroAI/follow_bt.py`

3. **Zameni BT framework (opciono)**
   - Prekopiraj `HeroAI_backup/bt_v2.py` u:
     - `HeroAI/bt.py`

4. **Reload u Py4GW**
   - Restartuj Py4GW ili reloaduj widgete, pa proveri da se `HeroAI` normalno učitava.

- `HeroAI_v3_formations_deadzone.py`
  - Snapshot `Widgets/HeroAI.py` kada su dodane precizne formacije i finalni deadzone fix.
- `follow_bt_v3.py`
  - Snapshot `HeroAI/follow_bt.py` sa:
    - direktnim mapiranjem party_number → formation slot (bez hero_count/hench_count),
    - formacijama po tipu lidera (melee/ranged/spear) i tipu heroja,
    - povećanim radiusom za ranged lider + ranged followere (1.6x),
    - finalnom deadzone proverom na dist_to_target (formacijska pozicija).
- `globals_v3.py`
  - Snapshot `HeroAI/globals.py` sa preciznim formacijskim listama po svakom tipu lidera i heroja (7 slotova svaka lista).

## Kako vratiti v3 verziju (precizne formacije + deadzone fix)

Ako želimo da se vratimo na v3 (formacije po tipu lidera sa deadzone fiks):

1. **Zameni follow BT modul**
   - Prekopiraj `HeroAI_backup/follow_bt_v3.py` u:
     - `HeroAI/follow_bt.py`

2. **Zameni globals**
   - Prekopiraj `HeroAI_backup/globals_v3.py` u:
     - `HeroAI/globals.py`

3. **Glavna HeroAI skripta je ista kao v2**
   - `Widgets/HeroAI.py` se nije promenio u v3, koristi se v2 ili trenutna verzija.

4. **Reload u Py4GW**
   - Restartuj Py4GW ili reloaduj widgete, pa proveri da se `HeroAI` normalno učitava i da formacije rade.

- `HeroAI_v4_follow_bt_dynamic_2025-11-15.py`
  - Snapshot `Widgets/HeroAI.py` u trenutku kada je:
    - uvedeno dinamičko dodeljivanje formacijskih slotova po broju aktivnih followera (relativni indeks umesto fiksnog `party_number`),
    - dodat brži ulazak u formaciju smanjenjem deadzone i agresivnijim skupljanjem radiusa.
- `follow_bt_v4_dynamic_2025-11-15.py`
  - Snapshot `HeroAI/follow_bt.py` sa:
    - dinamičkim mapiranjem formacijskih slotova u `FollowNode` po broju followera i tipu lidera/heroja,
    - manjom deadzone vrednošću (`FOLLOW_DEADZONE_DISTANCE = 60.0`),
    - povećanim baznim formacijskim radijusom (više razmaka između heroja),
    - agresivnijim spuštanjem radijusa pri prilasku lideru (brže “zakucavanje” u slotove).

## Kako vratiti v4 verziju (dinamički follow + tuning radius/deadzone)

Ako želimo da se vratimo na v4 (dinamičke formacije + podešena deadzona i radius):

1. **Zameni glavnu HeroAI skriptu (opciono)**
   - Ako želiš tačan v4 snapshot widgeta, prekopiraj `HeroAI_backup/HeroAI_v4_follow_bt_dynamic_2025-11-15.py` u:
     - `Widgets/HeroAI.py`

2. **Zameni follow BT modul**
   - Prekopiraj `HeroAI_backup/follow_bt_v4_dynamic_2025-11-15.py` u:
     - `HeroAI/follow_bt.py`

3. **Reload u Py4GW**
   - Restartuj Py4GW ili reloaduj widgete, pa proveri da se `HeroAI` normalno učitava i da se heroji raspoređuju po dinamičkim formacijama.

## Uputstvo za nove verzije (za GPT asistent)

Za svaku sledeću veću promenu u HeroAI behavior tree-u ili follow logici:

1. **Kreiraj novu verziju bekapa**
   - Kopiraj trenutnu `Widgets/HeroAI.py` u `HeroAI_backup/HeroAI_vN_opis_promene.py`.
   - Kopiraj trenutnu `HeroAI/follow_bt.py` u `HeroAI_backup/follow_bt_vN.py`.
   - Ako se menja i framework, kopiraj `HeroAI/bt.py` u `HeroAI_backup/bt_vN.py`.
   - Ako se menjaju formacije, kopiraj `HeroAI/globals.py` u `HeroAI_backup/globals_vN.py`.

2. **Ažuriraj ovaj README**
   - Dodaj sekciju:
     - opis šta je dodato/izmenjeno u vN (npr. "v2: dodan anti-stuck u FollowNode").
     - jasne korake kako da se vN verzija vrati (analogne koracima za v1/v2/v3).

3. **Ne menjaj postojeće vN fajlove**
   - Svaka verzija je snapshot. Kada se jednom kreira `*_vN*.py`, ne menja se, već se za nove izmene pravi `vN+1`.

Na ovaj način uvek postoji istorija promena za HeroAI, i lako možemo da se vratimo na bilo koju verziju kopi-pejstovanjem odgovarajućih fajlova iz `HeroAI_backup` u originalne lokacije.
