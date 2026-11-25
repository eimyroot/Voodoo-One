# CASEBOOK Tasks — nativní read-only integrace ve VOODOO One

Stav: **IZOLOVANÝ REVIEW KANDIDÁT; RUNTIME V HLAVNÍ APLIKACI DOSUD NENASAZEN**
Datum: 2026-11-23

## Skutečný produktový rozsah

Tento kandidát přidává jedinou obrazovku **CASEBOOK Tasks** do existujícího
`/console` a čtecí endpoint `GET /api/v1/casebook/tasks/{session_id}` do
existujícího VOODOO One `ProductComposition`. Nepřidává nový dashboard,
novou databázi aplikace, automatické oprávnění ani možnost spouštět příkazy.

**V běžném výchozím startu je připojení neaktivní**. Panel pro neaktivní
zdroj vrátí autentizovaný HTTP 503 („nenakonfigurováno“), nikoli falešný
výsledek. Server bez aktivního nastavení nijak neotvírá CASEBOOK zdroj.

## Konfigurace povoleného lokálního READ

Aktivace je záměrně povolená jen pokud `VOODOO_ENV=local` a
`VOODOO_ALLOW_PRODUCTION_EFFECTS` je vypnuté. Služba potřebuje všechny
následující **konkrétní skutečně schválené** hodnoty, které dodá operátor:

| Proměnná | Význam |
|---|---|
| `VOODOO_CASEBOOK_READ_SOURCE_ROOT` | Existující absolutní cesta ke schválenému kandidátu CASEBOOKu, jehož tři Python soubory odpovídají pinned SHA256. |
| `VOODOO_CASEBOOK_READ_DATA_ROOT` | Existující privátní evidence root; žádná cesta z HTTP klienta. Musí ležet pod `0_EVIDENCE` skutečného OS uživatele. |
| `VOODOO_CASEBOOK_READ_WORKSPACE_ID` | Přesné ID existujícího lokálního workspace ze stejné databáze VOODOO One. |
| `VOODOO_CASEBOOK_READ_SESSION_ID` | Přesné ID jedné schválené a existující CASEBOOK relace. |
| `VOODOO_CASEBOOK_READ_PROJECT` | Přesný název projektu z CASEBOOK session, kontrolovaný při čtení. |

Volitelný přepínač `VOODOO_CASEBOOK_READ_PASSPORT_CORRELATION=1` připojuje
read-only korelaci k téže nativní kompozici. Výchozí hodnota je `0`;
jiné hodnoty jsou odmítnuty. Zapnutí bez všech pěti přesných vazeb
selže při startu. Endpoint
`GET /api/v1/casebook/tasks/{session_id}/passport/{execution_id}`
kontroluje aktuální oprávnění, lokální CASEBOOK a přesnou návaznost
kanonického Passportu. Neautorizuje resume ani žádnou exekuci.
Pro vypnutí samotné korelace použít `0` nebo proměnnou odstranit.
Tato konfigurace je kandidát, nikoli důkaz aktivace používaného desktopu.

Konfiguraci aplikovat přes již existující bezpečný způsob nastavování
proměnných prostředí služby, neukládat neveřejné cesty, účty nebo hodnoty do
repozitáře. Obsahují-li hodnoty citlivé lokální cesty, chraňte i konfiguraci.

**V tomto kandidátu nejsou uvedené žádné skutečné owner-private hodnoty**.
Nepoužívat demo session ID pro skutečné operace. Identitu workspace a
vlastnictví CASEBOOK relace před aktivací nezávisle ověřit.

Nedodání všech položek končí chybou konfigurace; cizí workspace, neověřený
zdroj, poškozený journal, nepovolený privátní root nebo produkční režim
končí fail-closed při startu. Není vytvořen žádný automatický fallback,
lokální kopie journalu, token ani implicitní administrátorské právo.

## Bezpečnostní a provenance kontrola

- Autentizace a odvolání relací patří stávajícímu V-One identity provideru.
- Každý GET musí současně projít `evidence.read` a **aktuální**
  DB-backed workspace autorizací. Nestačí starý JWT nebo znalost session ID.
- CASEBOOK reader načítá jen tři pevně připnuté SHA256 zdrojové soubory,
  ověřuje jejich digests před importem i před/po každém čtení a používá
  CASEBOOK `CasebookStore.get_session()` s kontrolou SQLite hash-chain.
- Do JSON výstupu se nikdy nepřenáší raw metadata a `evidence_refs`.
- `execution_authorized_by_this_view` a `execution_verified_by_this_view`
  jsou **vždy `false`**. `independent_verifier=NOT_ATTESTED` nelze
  povýšit jen na základě zapsaného `RESULT`.
- Není přidána obecná execution capability, shell adapter, nový API grant,
  žádný G8 účinek ani poskytovatel WRITE.

## Akceptace a nástup do produkčního workflow

Před schválením feature merge je nutné:
1. Zkontrolovat souborově omezený diff proti přesnému GitHub `main`.
2. Provést nezávislé code/security review včetně volání třetí strany
   a ručního ověření, že klient nemůže změnit workspace ani data root.
3. Vyžádat CI/testy pro aktuální remote base; zkontrolovat možné
   konflikty s právě provozovanou desktopovou instancí a samostatně
   přijmout publikační, merge i deployment rozhodnutí.
4. Lokální aktivaci podrobit explicitnímu owner approval pro konkrétní
   CASEBOOK session ID, workspace a data root. Aktivovat pouze neprodukční
   profil a zopakovat čtení/login/logout/access revocation + browser QA.
5. Produkční zápisy zůstávají bez samostatného Runner/Verifier approval
   blokované. Tento read-only panel nic takového neobchází.

## Rollback

V nenasazeném stavu: žádný. Při budoucím povoleném lokálním nasazení
odstranit pět vazeb `VOODOO_CASEBOOK_READ_*` i volitelný přepínač korelace a restartovat **jen**
konkrétní schválenou V-One službu. Zcela nepřipojený CASEBOOK je
default; nebyla potřeba žádná schema migrace ani úprava skutečného CASEBOOK
journalu. Případný source rollback se provede řízeným Git revertem
přesně identifikovaného integračního commitu, nikoli destruktivním resetem
původních dirty checkoutů.

## Poznámka k přenositelnosti

Schválený lokální evidence shelf se odvozuje ze skutečného OS uživatele
(`pwd.getpwuid(os.getuid()).pw_dir/0_EVIDENCE`), nikoliv z dočasně
přepsaného `$HOME` v automatizovaném bridge prostředí. Jestliže hostitel
nepodporuje unixové `pwd`, pak je tato nyní lokálně macOS/Linux specifická
funkce neaktivovatelná, nikoli otevřená na libovolný adresář.
