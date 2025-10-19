Data Sources & Tools
We rely on Astropy and Astroquery to fetch real astronomical spectra. In particular, we use the NASA MAST archive for UV/optical/IR space data and the NIST Atomic Spectra Database for reference lines. The Mikulski Archive (MAST) contains science data from 20+ missions covering optical through near-IR wavelengths[1]. In our app, remote searches call astroquery.mast.Observations.query_criteria by target name to find calibrated spectra (e.g. JWST, HST). The dialog rewrites a free‐text object (e.g. “WASP-96 b” or “HD 189733”) into target_name and automatically filters for dataproduct_type="spectrum", intentType="SCIENCE", and calib_level=[2,3][2]. This ensures we retrieve science-grade spectra (levels 2/3) suitable for composition analysis.
Retrieving JWST & Multi-wavelength Spectra
Once a target search runs, the service returns a list of matching products (identifiers and URIs). For each selected entry, our code uses either requests or Astroquery’s own download methods. HTTP URLs are fetched with requests.get, and mast: URIs (MAST products) are fetched via astroquery.mast.Observations.download_file to handle authentication[3]. The downloaded FITS (or other files) are saved into a local cache (with SHA256 checksum) along with metadata (provider, URI, timestamp). Finally the file is passed to the ingest pipeline so it appears immediately in the app. In practice this means that as soon as we click “Download & Import,” the JWST spectrum is fetched and plotted in real time. Behind the scenes we track the provenance: e.g. for NIST line queries we replay astroquery.nist.Nist.query(...) and write out a CSV of lines, and for MAST we download the FITS and record provider=MAST[4].
Exoplanet & Stellar Data Access
To get exoplanet or stellar parameters, we use Astroquery’s interfaces as well. For example, the NASA Exoplanet Archive can be queried via astroquery.ipac.nexsci.NasaExoplanetArchive. A call like:

from astroquery.ipac.nexsci import NasaExoplanetArchive
result = NasaExoplanetArchive.query_object("HD 189733 b")
returns host star and planet data (coordinates, magnitudes, etc.)[5]. We then feed those sky coordinates or names into a MAST query to fetch any archived spectra of that system. Similarly, one could use astroquery.simbad or astroquery.gaia for cross-matching object identifiers or spectral types. In short, we chain the archives: use one service (Exoplanet Archive, SIMBAD, Gaia) to resolve a star/planet, then query MAST (or HST, Spitzer, etc.) for the actual spectra.
Laboratory Reference Data
To compare against lab spectra (UV/vis/IR of compounds), we overlay reference line lists. For atomic lines, we call astroquery.nist. For instance:

from astroquery.nist import Nist
import astropy.units as u
lines = Nist.query(4000*u.AA, 7000*u.AA, linename="H I")
This returns a table of hydrogen transitions from NIST over 400–700 nm[6]. We do similar calls for elements of interest (O, C, etc.) and normalize intensities. Our app’s Reference tab then can overlay these NIST lines on any spectrum. For molecular IR bands we include a built-in JSON reference of functional-group ranges (e.g. C–H stretches), drawn from standard handbooks. This way, the ground-measured VOC spectra can be directly compared to astronomical spectra by aligning features.
Caching & Provenance
Every remote fetch is cached. The first time we download a file, we record its URI and checksum; subsequent requests for that URI simply reuse the local copy[7]. In practice, enabling the Persistent Cache option means once a JWST spectrum is fetched, it’s stored permanently and the app won’t hit the network again for that file[7]. If cache is disabled, files persist only for the session. But either way, the metadata (provider, fetch time) is logged in a local index. The Library view lets us re-open cached spectra later without re-downloading. This ensures “live” queries don’t pull the same data repeatedly and makes offline replay possible[7].
Integration with Analysis Workflow
In summary, to pull live star/exoplanet data we instruct CodeX to use Astroquery calls to MAST (for JWST, HST spectra) and to other archives like the NASA Exoplanet Archive (for target info). Example code and instructions should be documented in our docs/ (e.g. docs/user/remote_data.md and developer notes) so that the process is repeatable. For instance, we can show how to call:

from astroquery.mast import Observations
obs_table = Observations.query_criteria(target_name="WASP-96 b",
                                       dataproduct_type="spectrum",
                                       calib_level=[2,3])
product_list = Observations.get_product_list(obs_table)
Observations.download_products(product_list)
and then how to feed the downloaded files into our DataIngestService. Our docs and knowledge log should cite the Astroquery/MAST examples and note the dependencies (astroquery, pandas, etc.) as in the Quickstart[2][3]. In this way, the agent always knows to use official APIs and archives (all real, cited data sources) and to update the code comments/docs whenever a new data source or target is added.
Sources: Official Astroquery documentation and our Spectra-App code/docs describe exactly this workflow[2][3][7][6][5]. These show how MAST and NIST queries are formulated and how caching is handled, ensuring the app fetches real-time spectra from NASA archives and lab references.
________________________________________
[1] MAST Queries (astroquery.mast) — astroquery v0.4.12.dev206
https://astroquery.readthedocs.io/en/latest/mast/mast.html
[2] [3] [4] [7] remote_data.md
https://github.com/brettadin/spectra-app-beta/blob/5a93fb63f6b62f7845e78a56723cab6d6f74db94/docs/user/remote_data.md
[5] NASA Exoplanet Archive (astroquery.ipac.nexsci.nasa_exoplanet_archive) — astroquery v0.4.12.dev206
https://astroquery.readthedocs.io/en/latest/ipac/nexsci/nasa_exoplanet_archive.html
[6] NIST Queries (astroquery.nist) — astroquery v0.4.12.dev206
https://astroquery.readthedocs.io/en/latest/nist/nist.html
