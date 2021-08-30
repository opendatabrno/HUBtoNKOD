# HUBtoNKODNástroj slouží pro transfer metadat mezi dataportálem data.brno.cz, který je postavený nad technologií ArcGIS HUB a Národním katalogem otevřených dat. 
Data.brno.cz generuje JSON feed: https://data-brno-cz-mestobrno.hub.arcgis.com/data.json.
Skript pak z tohoto feedu transformuje metadata do feedu zde: https://kod.brno.cz/nkod/index.ttl
Z tohto feedu si pak 1x denne harvestuje metadata Národní katalog otevřených dat.
Skript pro transformaci z jednoho feedu do druhého se taky spouští také 1x denně.

Pro víc informací kontaktujte prosím data@brno.cz
